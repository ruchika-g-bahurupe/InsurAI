"""Comprehensive Phase 3 AI Agent Verification Test Suite (Updated for Autonomous Watchdog)."""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agent.gemini_client import gemini_client
from app.agent.tool_registry import tool_registry
from app.agent.proactive_scanner import watchdog_scanner
from app.agent.copilot_agent import copilot_agent
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_phase3():
    print("=" * 80)
    print("PHASE 3 VERIFICATION: CENTRAL AI AGENT SUBSYSTEM")
    print("=" * 80)

    print("\n[TEST 1] Gemini Client Connectivity & Environment Configuration...")
    print(f"    - Configured Model: {gemini_client.model}")
    print(f"    - Analysis Model: {gemini_client.analysis_model}")
    print(f"    - Live API Key Detected: {gemini_client.is_live()}")

    print("\n[TEST 2] Python Tool Registry Verification (Total vs Watchdog Read-Only)...")
    metadata = tool_registry.get_tool_metadata()
    watchdog_tools = tool_registry.get_watchdog_callables()
    assert len(metadata) == 18, f"Expected 18 total registered tools, found {len(metadata)}"
    assert len(watchdog_tools) == 10, f"Expected 10 Watchdog read-only tools, found {len(watchdog_tools)}"
    print(f"    - Total Registered Tools: {len(metadata)} | Watchdog Read-Only Tools: {len(watchdog_tools)}")

    t1 = tool_registry.execute_tool("search_customer_records", {"query": "Vikram"})
    assert "customers" in t1 and len(t1["customers"]) > 0
    vikram = t1["customers"][0]

    t2 = tool_registry.execute_tool("get_customer_360_profile", {"customer_id_or_code": vikram["customer_code"]})
    assert "policies" in t2 and len(t2["policies"]) > 0

    pol_id = t2["policies"][0]["policy_id"]
    t3 = tool_registry.execute_tool("get_policy_compliance_status", {"policy_id_or_number": pol_id})
    assert "documents" in t3

    t4 = tool_registry.execute_tool("get_premium_payment_history", {"policy_id_or_number": pol_id})
    assert "schedules" in t4

    t5 = tool_registry.execute_tool("get_expiring_policies", {"within_days": 30})
    assert "policies" in t5

    t6 = tool_registry.execute_tool("get_missing_documents", {})
    assert "documents" in t6

    t7 = tool_registry.execute_tool("investigate_customer_case", {"customer_id_or_code": vikram["customer_code"]})
    assert "policies" in t7 and "documents" in t7 and "claims" in t7

    t8 = tool_registry.execute_tool("generate_outreach_draft", {"customer_id_or_code": vikram["customer_code"], "purpose": "RENEWAL_OFFER"})
    assert "subject" in t8 and "body" in t8
    print("    - Core database tools verified.")

    print("\n[TEST 3] The Watchdog: Autonomous Investigation Sweep...")
    sweep_result = watchdog_scanner.run_sweep(
        trigger_source="TEST_SUITE",
        run_type="PROACTIVE_SWEEP",
    )
    if gemini_client.is_live():
        assert sweep_result["status"] == "COMPLETED"
    else:
        assert sweep_result["status"] == "DEGRADED"
        assert sweep_result["degraded_mode"] is True
    print(f"    - Watchdog Status: {sweep_result['status']}")

    print("\n[TEST 4] The Investigator: Conversational Copilot Multi-Turn Testing...")
    turn1 = copilot_agent.handle_message(user_message="Which customers require immediate attention?")
    conv_id = turn1["conversation_id"]
    assert len(turn1["tool_calls"]) > 0

    turn2 = copilot_agent.handle_message(user_message="Show policies expiring within 15 days", conversation_id=conv_id)
    assert any(tc["name"] == "get_expiring_policies" for tc in turn2["tool_calls"])

    turn3 = copilot_agent.handle_message(user_message="Investigate Vikram Mehta's full profile", conversation_id=conv_id)
    assert "Vikram Mehta" in turn3["reply"]

    turn4 = copilot_agent.handle_message(user_message="Investigate customer John Nonexistent", conversation_id=conv_id)
    assert "No customer records found" in turn4["reply"] or "not found" in turn4["reply"].lower()
    print("    - Investigator multi-turn tests passed.")

    print("\n[TEST 5] HTTP API Endpoints Verification...")
    assert client.post("/api/v1/copilot/chat", json={"message": "Show customers with overdue premiums"}).status_code == 200
    tools_json = client.get("/api/v1/copilot/tools").json()
    assert tools_json["total_tools"] == 18

    res_trig = client.post("/api/v1/analysis/trigger", json={"trigger_source": "API_TEST"})
    assert res_trig.status_code == 200
    expected_status = "COMPLETED" if gemini_client.is_live() else "DEGRADED"
    assert res_trig.json()["status"] == expected_status
    print("    - HTTP API endpoints verified.")


if __name__ == "__main__":
    test_phase3()
    print("\nALL PHASE 3 AI AGENT TESTS PASSED!")
