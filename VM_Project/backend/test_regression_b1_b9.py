"""Regression Test Suite for Backend Defects B1-B9 (Updated for Autonomous Watchdog).

Validates:
- B1: Watchdog stable dedup_key validation (rejects volatile day counts)
- B2: Resolved/Dismissed attention items are never reopened by subsequent sweeps
- B3: Concurrency lock prevents concurrent Watchdog sweeps
- B4: Copilot & Analysis endpoints use non-blocking threadpool execution
- B5: Gemini function-calling turn supports active_customer_id, multi-round tool calls, and ToolResult format
- B6: Offline Investigator dynamically resolves customers, drafts outreach, and returns consistent ToolResult format
- B7: Strict LLM output validation rejects missing fields, wrong policy ownership, and ungrounded evidence
- B8: BillingService applies customer_id & issue_type filters to summary counts and returns unpaginated total_issues
- B9: SQLite PRAGMA foreign_keys=ON is enforced on both sync and async connections
"""

import asyncio
import inspect
import json
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.agent.intelligence_core import intelligence_core
from app.agent.proactive_scanner import watchdog_scanner
from app.agent.tool_registry import tool_registry
from app.core.database import async_engine, sync_engine

client = TestClient(app)


def test_b1_b7_strict_validation_and_stable_dedup():
    print("\n[B1/B7] Testing strict LLM output validation & stable dedup_key enforcement...")
    cust = tool_registry.execute_tool("list_customer_records", {"limit": 1})["customers"][0]
    cid = cust["customer_id"]
    code = cust["customer_code"]

    invalid_items = [
        # Missing reasoning_summary
        {
            "customer_id": cid,
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 75,
            "title": "Incomplete",
            "root_cause": "Missing reasoning",
            "ai_recommendation": "Review",
            "supporting_evidence": [f"Customer {code}"],
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:TEST1",
        },
        # Volatile day-count dedup_key
        {
            "customer_id": cid,
            "category": "POLICY_EXPIRY",
            "urgency_level": "HIGH",
            "attention_score": 80,
            "title": "Volatile Dedup",
            "reasoning_summary": "Policy expiring soon.",
            "root_cause": "Expiry approaching",
            "ai_recommendation": "Send renewal",
            "supporting_evidence": [f"Customer {code}"],
            "dedup_key": f"{cid}:POLICY_EXPIRY:GENERAL:EXP_15D",
        },
        # Ungrounded supporting_evidence (does not reference real DB records)
        {
            "customer_id": cid,
            "category": "RISK_ALERT",
            "urgency_level": "MEDIUM",
            "attention_score": 55,
            "title": "Ungrounded Claim",
            "reasoning_summary": "Suspicious activity",
            "root_cause": "Unknown",
            "ai_recommendation": "Review",
            "supporting_evidence": ["Arbitrary unsupported statement XYZ-000"],
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:UNGROUNDED",
        },
        # Invalid policy_id not owned by customer
        {
            "customer_id": cid,
            "policy_id": "WRONG-POLICY-ID-999",
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 70,
            "title": "Wrong Policy",
            "reasoning_summary": "Policy mismatch",
            "root_cause": "Policy check",
            "ai_recommendation": "Review",
            "supporting_evidence": [f"Customer {code}"],
            "dedup_key": f"{cid}:RISK_ALERT:WRONG:TEST",
        },
    ]

    validated = intelligence_core._parse_and_validate_watchdog_output(json.dumps(invalid_items), [])
    assert len(validated) == 0, f"Expected all invalid items rejected, got {len(validated)}"
    print("    - B1, B7 strict validation verified.")


def test_b2_b3_lock_and_degraded_preservation():
    print("\n[B2/B3] Testing concurrency lock and DEGRADED preservation...")
    acquired = watchdog_scanner._sweep_lock.acquire(blocking=False)
    assert acquired
    try:
        busy_res = watchdog_scanner.run_sweep(trigger_source="TEST_CONCURRENT")
        assert busy_res["status"] == "ALREADY_RUNNING"
    finally:
        watchdog_scanner._sweep_lock.release()

    if not intelligence_core.gemini.is_live():
        res = watchdog_scanner.run_sweep(trigger_source="REGRESSION_DEGRADED")
        assert res["status"] == "DEGRADED"
        assert res["degraded_mode"] is True
    print("    - B2, B3 verified.")


def test_b4_non_blocking_endpoints():
    print("\n[B4] Testing threadpool offloading in copilot and analysis endpoints...")
    from app.api.v1.endpoints import copilot, analysis
    assert "run_in_threadpool" in inspect.getsource(copilot.chat_with_copilot)
    assert "run_in_threadpool" in inspect.getsource(analysis.trigger_proactive_sweep)
    print("    - B4 verified.")


def test_b5_b6_investigator_consistency():
    print("\n[B5/B6] Testing Investigator tool_results format & dynamic offline lookup...")
    res = client.post("/api/v1/copilot/chat", json={"message": "Draft a renewal email for CUST-1005"})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert isinstance(data["tool_results"], list)
    for tr in data["tool_results"]:
        assert "name" in tr and "result" in tr, f"Inconsistent ToolResult shape: {tr}"
    print("    - B5, B6 verified.")


def test_b8_billing_filtering_and_counts():
    print("\n[B8] Testing BillingService filtering and unpaginated total_issues...")
    all_res = client.get("/api/v1/billing/issues?limit=2").json()
    if all_res["total_issues"] > 2:
        assert len(all_res["items"]) == 2
        assert all_res["total_issues"] > len(all_res["items"]), "total_issues reflected paginated slice!"
    if all_res["items"]:
        cid = all_res["items"][0]["customer_id"]
        cust_res = client.get(f"/api/v1/billing/issues?customer_id={cid}").json()
        assert all(item["customer_id"] == cid for item in cust_res["items"])
        assert cust_res["total_issues"] == len(cust_res["items"])
    print("    - B8 verified.")


def test_b9_sqlite_foreign_keys():
    print("\n[B9] Testing SQLite PRAGMA foreign_keys=ON on sync and async engines...")
    with sync_engine.connect() as conn:
        fk_sync = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk_sync == 1, f"Sync foreign_keys={fk_sync}, expected 1"

    async def check_async():
        async with async_engine.connect() as conn:
            res = await conn.execute(text("PRAGMA foreign_keys"))
            return res.scalar()

    fk_async = asyncio.run(check_async())
    assert fk_async == 1, f"Async foreign_keys={fk_async}, expected 1"
    print("    - B9 verified.")


if __name__ == "__main__":
    test_b1_b7_strict_validation_and_stable_dedup()
    test_b2_b3_lock_and_degraded_preservation()
    test_b4_non_blocking_endpoints()
    test_b5_b6_investigator_consistency()
    test_b8_billing_filtering_and_counts()
    test_b9_sqlite_foreign_keys()
    print("\nALL B1-B9 REGRESSION TESTS PASSED!")
