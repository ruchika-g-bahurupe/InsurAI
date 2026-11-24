"""Standalone Live Gemini Integration Test for the Autonomous Watchdog.

Requires a valid GEMINI_API_KEY in backend/.env.
Verifies:
- Real Gemini API response
- Actual function-call requests and database tool execution
- Multi-step investigation
- Portfolio coverage accounting
- Final structured, evidence-grounded recommendations
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agent.gemini_client import gemini_client
from app.agent.proactive_scanner import watchdog_scanner


def run_live_gemini_integration():
    print("=" * 80)
    print("LIVE GEMINI INTEGRATION TEST: AUTONOMOUS WATCHDOG")
    print("=" * 80)

    if not gemini_client.is_live():
        print("ABORTED: GEMINI_API_KEY is not configured in backend/.env.")
        print("Set a valid GEMINI_API_KEY and re-run: python test_watchdog_live_gemini.py")
        sys.exit(2)

    print(f"Using Analysis Model: {gemini_client.analysis_model}")
    result = watchdog_scanner.run_sweep(
        trigger_source="LIVE_GEMINI_INTEGRATION_TEST",
        run_type="ON_DEMAND",
        max_iterations=12,
        max_tool_calls=40,
        timeout_seconds=90.0,
    )

    print(f"Status: {result.get('status')}")
    print(f"Iterations Used: {result.get('iterations_used')}")
    print(f"Tool Calls Count: {result.get('tool_calls_count')}")
    print(f"Coverage: {result.get('coverage')}")
    print(f"Issues Detected: {result.get('issues_detected')}")
    print(f"Summary: {result.get('summary')}")

    assert result["status"] == "COMPLETED", f"Live Watchdog failed: {result}"
    assert result["degraded_mode"] is False
    assert result["tool_calls_count"] > 0, "Expected live Gemini to execute database tools."
    assert result["iterations_used"] >= 2, "Expected multi-step investigation (>= 2 iterations)."
    print("\nLIVE GEMINI INTEGRATION TEST PASSED!")


if __name__ == "__main__":
    run_live_gemini_integration()
