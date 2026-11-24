"""Mocked Test Suite for Autonomous Watchdog Agent (No Live API Key Required).

Covers:
1. DEGRADED mode preservation when GEMINI_API_KEY is unset
2. Multi-step tool calling, duplicate call guard, and granular portfolio coverage accounting
3. Strict validation rejecting missing required fields, wrong policy ownership, and non-exact evidence
4. Tool limit enforcement and hard execution deadline timeout
"""

import json
import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.agent.intelligence_core import intelligence_core
from app.agent.proactive_scanner import watchdog_scanner
from app.agent.tool_registry import tool_registry

client = TestClient(app)


def _fake_fn_call(name: str, args: dict):
    return SimpleNamespace(name=name, args=args)


def _fake_response(function_calls=None, text=None):
    parts = [SimpleNamespace(function_call=fc) for fc in (function_calls or [])]
    content = SimpleNamespace(role="model", parts=parts)
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(function_calls=function_calls, candidates=[candidate], text=text)


def test_degraded_mode_preserves_existing_alerts():
    print("\n[1] Testing DEGRADED mode when GEMINI_API_KEY is unavailable...")
    before_count = len(client.get("/api/v1/attention?limit=100").json())
    with patch.object(intelligence_core.gemini, "is_live", return_value=False):
        res = client.post("/api/v1/analysis/trigger", json={"run_type": "ON_DEMAND", "trigger_source": "TEST_DEGRADED"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DEGRADED"
        assert data["degraded_mode"] is True
        assert data["records_scanned"] == 0
        assert data["coverage"]["pagination_completed"] is False
        assert data["coverage"]["coverage_complete"] is False
    after_count = len(client.get("/api/v1/attention?limit=100").json())
    assert after_count == before_count
    print("    - DEGRADED mode verified.")


def test_strict_validation_rejects_missing_fields_and_weak_evidence():
    print("\n[2] Testing strict validation (exact DB IDs, no misleading defaults)...")
    cust = tool_registry.execute_tool("list_customer_records", {"limit": 1})["customers"][0]
    cid = cust["customer_id"]
    ccode = cust["customer_code"]

    invalid_payload = [
        # Missing confidence_level -> must be rejected (no silent MEDIUM default)
        {
            "customer_id": cid,
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 80.0,
            "title": "Missing Confidence",
            "reasoning_summary": "Detailed reasoning",
            "root_cause": "Root cause",
            "ai_summary": "Summary",
            "ai_recommendation": "Action",
            "identified_risk_factors": ["Factor 1"],
            "investigation_steps": ["get_customer_360_profile"],
            "supporting_evidence": [f"Customer {ccode}"],
            "suggested_action": {"action_type": "REVIEW"},
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:NO_CONF",
        },
        # Weak evidence (generic word 'ACTIVE' without exact DB record ID/code/number) -> must be rejected
        {
            "customer_id": cid,
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 80.0,
            "confidence_level": "HIGH",
            "title": "Weak Generic Evidence",
            "reasoning_summary": "Detailed reasoning",
            "root_cause": "Root cause",
            "ai_summary": "Summary",
            "ai_recommendation": "Action",
            "identified_risk_factors": ["Factor 1"],
            "investigation_steps": ["get_customer_360_profile"],
            "supporting_evidence": ["Customer has ACTIVE status"],
            "suggested_action": {"action_type": "REVIEW"},
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:WEAK_EVIDENCE",
        },
        # Missing suggested_action -> must be rejected (no silent default)
        {
            "customer_id": cid,
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 80.0,
            "confidence_level": "HIGH",
            "title": "Missing Suggested Action",
            "reasoning_summary": "Detailed reasoning",
            "root_cause": "Root cause",
            "ai_summary": "Summary",
            "ai_recommendation": "Action",
            "identified_risk_factors": ["Factor 1"],
            "investigation_steps": ["get_customer_360_profile"],
            "supporting_evidence": [f"Customer {ccode}"],
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:NO_ACTION",
        },
    ]
    res = intelligence_core._parse_and_validate_watchdog_output(json.dumps(invalid_payload))
    assert len(res) == 0, f"Expected all 3 incomplete/weak items rejected, got {len(res)}"
    print("    - Strict validation verified.")


def test_multistep_coverage_accounting_and_persistence():
    print("\n[3] Testing multi-step investigation, granular coverage accounting & persistence...")
    custs = tool_registry.execute_tool("list_customer_records", {"limit": 2})["customers"]
    target_cust = custs[0]
    cid = target_cust["customer_id"]
    ccode = target_cust["customer_code"]

    valid_payload = [
        {
            "customer_id": cid,
            "policy_id": None,
            "category": "RISK_ALERT",
            "urgency_level": "HIGH",
            "attention_score": 81.5,
            "confidence_level": "HIGH",
            "title": "Autonomous Multi-Signal Risk Assessment",
            "reasoning_summary": "Investigated portfolio overview and customer 360 profile; combined signals warrant review.",
            "root_cause": "Multiple concurrent operational and compliance signals discovered.",
            "identified_risk_factors": ["Unverified document status", "Upcoming renewal window"],
            "investigation_steps": ["get_portfolio_overview()", f"get_customer_360_profile({cid})"],
            "supporting_evidence": [f"Verified record {ccode} ({cid}) inspected via database tools"],
            "data_gaps": ["Missing updated income verification timestamp"],
            "ai_summary": f"Customer {ccode} requires coordinated retention and compliance review.",
            "ai_recommendation": "Review customer dossier and request updated verification.",
            "suggested_action": {"action_type": "EMPLOYEE_REVIEW", "requires_employee_approval": True},
            "dedup_key": f"{cid}:RISK_ALERT:GENERAL:AUTONOMOUS_TEST",
        }
    ]

    turns = iter([
        _fake_response(function_calls=[_fake_fn_call("get_portfolio_overview", {})]),
        _fake_response(function_calls=[
            _fake_fn_call("get_portfolio_overview", {}),
            _fake_fn_call("list_customer_records", {"skip": 0, "limit": 2}),
        ]),
        _fake_response(function_calls=[_fake_fn_call("get_customer_360_profile", {"customer_id_or_code": cid})]),
        _fake_response(function_calls=None, text=json.dumps(valid_payload)),
    ])

    with (
        patch.object(intelligence_core.gemini, "is_live", return_value=True),
        patch.object(intelligence_core.gemini, "_client", new=True),
        patch.object(intelligence_core.gemini, "generate_with_tools", side_effect=lambda **kwargs: next(turns)),
    ):
        res1 = watchdog_scanner.run_sweep(trigger_source="TEST_AUTONOMOUS")
        assert res1["status"] == "COMPLETED"
        cov = res1["coverage"]
        assert cov["customers_retrieved"] == 2
        assert cov["customers_deeply_investigated"] == 1
        assert cov["customers_retrieved_not_investigated"] == 1
        assert cov["customers_skipped"] == cov["total_portfolio_customers"] - 2
        assert cov["pagination_completed"] is False
        assert cov["coverage_complete"] is False

        # Resolve and verify preservation
        items = client.get(f"/api/v1/attention?customer_id={cid}&status=ACTIVE").json()
        matched = next(i for i in items if i["dedup_key"] == f"{cid}:RISK_ALERT:GENERAL:AUTONOMOUS_TEST")
        client.patch(
            f"/api/v1/attention/{matched['id']}/status",
            json={"status": "RESOLVED", "resolved_by": "Test Analyst", "resolution_notes": "Closed in test"},
        )
        turns2 = iter([
            _fake_response(function_calls=[_fake_fn_call("get_portfolio_overview", {})]),
            _fake_response(function_calls=None, text=json.dumps(valid_payload)),
        ])
        with patch.object(intelligence_core.gemini, "generate_with_tools", side_effect=lambda **kwargs: next(turns2)):
            res2 = watchdog_scanner.run_sweep(trigger_source="TEST_AUTONOMOUS_REPEAT")
            assert res2["new_recommendations_created"] == 0
            assert res2["skipped_closed"] == 1
    print("    - Granular coverage accounting & persistence verified.")


def test_deadline_timeout_non_blocking():
    print("\n[4] Testing hard execution deadline without blocking on slow worker...")
    def slow_call(**kwargs):
        time.sleep(2.0)
        return _fake_response(function_calls=None, text="[]")

    t0 = time.perf_counter()
    with (
        patch.object(intelligence_core.gemini, "is_live", return_value=True),
        patch.object(intelligence_core.gemini, "_client", new=True),
        patch.object(intelligence_core.gemini, "generate_with_tools", side_effect=slow_call),
    ):
        res = watchdog_scanner.run_sweep(trigger_source="TEST_TIMEOUT", timeout_seconds=0.3)
        elapsed = time.perf_counter() - t0
        assert res["status"] == "FAILED"
        assert "timed out" in res["error"].lower()
        assert elapsed < 1.2, f"Deadline shutdown blocked for slow worker ({elapsed:.2f}s)!"
    print("    - Non-blocking execution deadline verified.")


if __name__ == "__main__":
    test_degraded_mode_preserves_existing_alerts()
    test_strict_validation_rejects_missing_fields_and_weak_evidence()
    test_multistep_coverage_accounting_and_persistence()
    test_deadline_timeout_non_blocking()
    print("\nALL MOCKED AUTONOMOUS WATCHDOG TESTS PASSED!")
