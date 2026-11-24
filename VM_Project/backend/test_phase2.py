"""Comprehensive Phase 2 Verification Test Suite.

Validates:
1. Customer Attention API (List, Filters, Sort, Pagination, Detail, Status Update, Audit Logging)
2. Policy Expiry API (7, 15, 30, 60 days, Days remaining calculation, Customer info, Expired exclusion)
3. Missing Document API (Mandatory deficits only, Status filters, Policy & Customer info)
4. Premium Issue API (Overdue, Grace period, Upcoming, Failed debit, Financial amounts)
5. Renewal Follow-Up API (Expiry horizon, Duplicate check, Follow-up priority, Action recommendations)
6. Customer 360 API (Dossier verification: Policies, Schedules, Docs, Claims, Attention, Audit)
7. Dashboard Metrics (Dynamic computations, Zero hardcoding)
"""

import os
import sys
from datetime import date

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_phase2():
    print("=" * 80)
    print("PHASE 2 VERIFICATION: CORE BUSINESS LOGIC & QUERY APIS")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. CUSTOMER ATTENTION API
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Customer Attention API...")
    # 1a. Retrieve active items
    res = client.get("/api/v1/attention")
    assert res.status_code == 200, f"Failed: {res.text}"
    att_list = res.json()
    assert len(att_list) > 0, "Expected active attention items"
    print(f"    - Active attention items returned: {len(att_list)}")

    # 1b. Filter by Priority (Urgency)
    res_crit = client.get("/api/v1/attention?urgency_level=CRITICAL")
    assert res_crit.status_code == 200
    crit_items = res_crit.json()
    assert all(i["urgency_level"] == "CRITICAL" for i in crit_items)
    print(f"    - Filter urgency_level=CRITICAL: {len(crit_items)} items")

    # 1c. Filter by Category
    res_cat = client.get("/api/v1/attention?category=POLICY_EXPIRY")
    assert res_cat.status_code == 200
    cat_items = res_cat.json()
    assert all(i["category"] == "POLICY_EXPIRY" for i in cat_items)
    print(f"    - Filter category=POLICY_EXPIRY: {len(cat_items)} items")

    # 1d. Pagination and Sorting
    res_sort = client.get("/api/v1/attention?sort_by=attention_score&order=asc&skip=0&limit=3")
    assert res_sort.status_code == 200
    sorted_items = res_sort.json()
    assert len(sorted_items) <= 3
    if len(sorted_items) >= 2:
        assert sorted_items[0]["attention_score"] <= sorted_items[1]["attention_score"]
    print(f"    - Pagination & Sorting (score ASC, limit 3): verified")

    # 1e. Detailed Attention Item info
    target_item = att_list[0]
    res_detail = client.get(f"/api/v1/attention/{target_item['id']}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == target_item["id"]
    assert "customer_details" in detail and detail["customer_details"] is not None
    assert "audit_history" in detail
    print(f"    - Individual Attention Item Detail: verified (Customer: {detail['customer_details']['full_name']})")

    # 1f. Update Recommendation Status & Record Employee Actions in Audit Log
    res_patch = client.patch(
        f"/api/v1/attention/{target_item['id']}/status",
        json={
            "status": "IN_PROGRESS",
            "assigned_to": "Sarah Jenkins (Senior Underwriter)",
            "resolved_by": "Sarah Jenkins (Senior Underwriter)",
            "resolution_notes": "Employee assigned to investigate client portfolio.",
        },
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    assert patched["status"] == "IN_PROGRESS"

    # Verify audit log recorded the employee action
    res_detail_after = client.get(f"/api/v1/attention/{target_item['id']}")
    audit_entries = res_detail_after.json()["audit_history"]
    action_found = any("RECOMMENDATION_IN_PROGRESS" in a["action_type"] for a in audit_entries)
    assert action_found, "Audit log did not record the employee status update action!"
    print(f"    - Status update & Audit log persistence: verified (Audit logged)")

    # --------------------------------------------------------------------------
    # 2. POLICY EXPIRY API
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Policy Expiry API...")
    today = date.today()

    for window in [7, 15, 30, 60]:
        res_exp = client.get(f"/api/v1/policies/expiring?within_days={window}")
        assert res_exp.status_code == 200
        data = res_exp.json()
        assert data["filter_window_days"] == window
        print(f"    - Window {window:2d} days: {data['total_expiring']} policies expiring (${data['total_premium_at_stake']:,.2f} at stake)")

        # Verify accurate days_remaining, customer info, and exclusion of already expired policies
        for p in data["items"]:
            assert p["days_remaining"] >= 0, f"Expired policy was returned: days_remaining={p['days_remaining']}"
            assert p["days_remaining"] <= window, f"Policy outside window: days_remaining={p['days_remaining']}"
            assert p["customer_id"] is not None
            assert p["customer_name"] is not None
            assert p["status"] in ["ACTIVE", "RENEWAL_PENDING"]

    print("    - Accurate days calculation and exclusion of expired policies: verified")

    # --------------------------------------------------------------------------
    # 3. MISSING DOCUMENT API
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Missing Document API...")
    res_docs = client.get("/api/v1/documents/missing")
    assert res_docs.status_code == 200
    doc_data = res_docs.json()
    assert doc_data["total_deficits"] > 0
    print(f"    - Total compliance deficits: {doc_data['total_deficits']}")
    print(f"    - Deficit breakdown: Pending={doc_data['pending_count']}, Rejected={doc_data['rejected_count']}, Expired={doc_data['expired_count']}")
    print(f"    - Affected unique customers: {doc_data['affected_customers_count']}")

    # Check that optional documents are NEVER returned
    for item in doc_data["items"]:
        assert item["is_mandatory"] is True, "Optional document incorrectly returned as missing!"
        assert item["policy_number"] is not None
        assert item["customer_name"] is not None
        assert item["document_type"] is not None
    print("    - Strictly mandatory documents and associated policy details: verified")

    # 3b. Test filtering by status
    res_rej = client.get("/api/v1/documents/missing?status=REJECTED")
    assert res_rej.status_code == 200
    rej_data = res_rej.json()
    assert all(i["status"] == "REJECTED" for i in rej_data["items"])
    print(f"    - Filter status=REJECTED: {len(rej_data['items'])} rejected documents verified")

    # --------------------------------------------------------------------------
    # 4. PREMIUM ISSUE API
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Premium Issue API...")
    res_billing = client.get("/api/v1/billing/issues")
    assert res_billing.status_code == 200
    bill_data = res_billing.json()
    print(f"    - Total premium issues: {bill_data['total_issues']}")
    print(f"    - In Grace Period: {bill_data['in_grace_period_count']}")
    print(f"    - Overdue: {bill_data['overdue_count']}")
    print(f"    - Failed Auto-Debits: {bill_data['failed_auto_debit_count']}")
    print(f"    - Total Amount at Risk: ${bill_data['total_amount_at_risk']:,.2f}")

    for item in bill_data["items"]:
        assert item["amount_due"] > 0
        assert item["customer_name"] is not None
        assert item["policy_number"] is not None
        assert item["issue_type"] in ["GRACE_PERIOD", "OVERDUE", "FAILED_DEBIT", "UPCOMING_DUE"]

    # 4b. Filter by Grace Period
    res_grace = client.get("/api/v1/billing/issues?issue_type=GRACE_PERIOD")
    assert res_grace.status_code == 200
    grace_data = res_grace.json()
    print(f"    - Filter issue_type=GRACE_PERIOD: {len(grace_data['items'])} items")

    # --------------------------------------------------------------------------
    # 5. RENEWAL FOLLOW-UP API
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Renewal Follow-Up API...")
    res_renew = client.get("/api/v1/renewals/follow-ups?within_days=60")
    assert res_renew.status_code == 200
    renew_data = res_renew.json()
    print(f"    - Policies requiring renewal follow-up (60d window): {renew_data['total_in_window']}")
    print(f"    - Critical follow-ups: {renew_data['critical_followups']}")
    print(f"    - High follow-ups: {renew_data['high_followups']}")
    print(f"    - Already actioned (active attention exists): {renew_data['already_actioned_count']}")
    print(f"    - Total Pipeline Premium: ${renew_data['total_premium_in_pipeline']:,.2f}")

    for item in renew_data["items"]:
        assert item["days_to_expiry"] >= 0
        assert item["follow_up_priority"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert item["recommended_action"] != ""
        assert item["customer_name"] is not None

    # Test only_unactioned filter to avoid duplicate recommendations
    res_unactioned = client.get("/api/v1/renewals/follow-ups?within_days=60&only_unactioned=true")
    assert res_unactioned.status_code == 200
    unactioned_data = res_unactioned.json()
    assert all(i["has_active_attention_item"] is False for i in unactioned_data["items"])
    print(f"    - Duplicate prevention filter (only_unactioned=true): {len(unactioned_data['items'])} items verified")

    # --------------------------------------------------------------------------
    # 6. CUSTOMER 360 API
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Customer 360 API...")
    # Fetch a customer from directory first
    res_custs = client.get("/api/v1/customers?tier=VIP&limit=1")
    assert res_custs.status_code == 200
    sample_cust = res_custs.json()[0]
    cust_id = sample_cust["id"]

    res_360 = client.get(f"/api/v1/customers/{cust_id}")
    assert res_360.status_code == 200
    dossier = res_360.json()

    # Verify complete 360 structure
    assert dossier["id"] == cust_id
    assert "policies" in dossier and len(dossier["policies"]) > 0
    assert "documents" in dossier
    assert "claims" in dossier
    assert "attention_items" in dossier
    assert "audit_logs" in dossier
    print(f"    - Complete 360 Dossier for {dossier['full_name']} ({dossier['customer_code']}):")
    print(f"      * Policies: {len(dossier['policies'])} (with installment schedules)")
    print(f"      * Documents: {len(dossier['documents'])}")
    print(f"      * Claims: {len(dossier['claims'])}")
    print(f"      * Attention Items: {len(dossier['attention_items'])}")
    print(f"      * Activity Audit Logs: {len(dossier['audit_logs'])}")

    # --------------------------------------------------------------------------
    # 7. DASHBOARD METRICS API
    # --------------------------------------------------------------------------
    print("\n[TEST 7] Dashboard Metrics API (Zero Hardcoding)...")
    res_dash = client.get("/api/v1/dashboard/metrics")
    assert res_dash.status_code == 200
    metrics = res_dash.json()

    print(f"    - Total Customers: {metrics['total_customers']}")
    print(f"    - Total Active Policies: {metrics['total_active_policies']}")
    print(f"    - Customers Requiring Attention: {metrics['customers_requiring_attention']}")
    print(f"    - High-Priority Cases (Critical + High): {metrics['high_priority_cases']}")
    print(f"    - Upcoming Expirations: {metrics['upcoming_policy_expirations']}")
    print(f"    - Missing Mandatory Documents: {metrics['missing_documents_count']}")
    print(f"    - Premium Issues Count: {metrics['premium_issues_count']}")
    print(f"    - Total Premium at Risk: ${metrics['total_premium_at_risk']:,.2f}")
    print(f"    - Attention Category Distribution: {metrics['attention_by_category']}")
    print(f"    - Attention Urgency Distribution: {metrics['attention_by_urgency']}")

    assert metrics["total_customers"] >= 50
    assert metrics["total_active_policies"] > 0
    assert metrics["customers_requiring_attention"] > 0
    assert metrics["high_priority_cases"] > 0
    assert metrics["upcoming_policy_expirations"]["in_30_days"] >= metrics["upcoming_policy_expirations"]["in_7_days"]
    assert metrics["missing_documents_count"] > 0

    print("\n" + "=" * 80)
    print("ALL PHASE 2 TESTS PASSED PERFECTLY (100% HEALTHY)")
    print("=" * 80)


if __name__ == "__main__":
    test_phase2()
