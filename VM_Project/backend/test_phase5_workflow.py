"""Phase 5 Human-in-the-Loop Outreach Draft & Audit Workflow Verification."""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_phase5_workflow():
    print("\n[PHASE 5] Testing Human-in-the-Loop Outreach Draft & Audit Logging...")
    att_list = client.get("/api/v1/attention?limit=1").json()
    assert len(att_list) > 0, "Expected at least one attention item"
    att_id = att_list[0]["id"]

    res = client.post(
        f"/api/v1/attention/{att_id}/draft-outreach",
        json={"channel": "EMAIL", "approved_by": "Phase 5 Verifier"},
    )
    assert res.status_code == 200, f"Draft outreach failed: {res.text}"
    draft = res.json()
    assert draft["is_draft"] is True
    assert draft["requires_employee_approval"] is True
    assert "subject" in draft and "body" in draft

    detail = client.get(f"/api/v1/attention/{att_id}").json()
    assert any(a["action_type"] == "OUTREACH_DRAFT_PREPARED" for a in detail["audit_history"])

    health = client.get("/api/v1/health").json()
    assert "ai_mode" in health and "gemini_live" in health
    print("    - Phase 5 human-in-the-loop draft & audit workflow verified.")


if __name__ == "__main__":
    test_phase5_workflow()
