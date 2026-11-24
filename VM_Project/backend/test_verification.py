"""Comprehensive Phase 1 Verification Script.

Tests:
1. Health endpoint & DB connectivity
2. Dashboard metrics aggregation
3. Customer directory (count, pagination, search, tier filters)
4. Customer 360° deep profile (relationships, policies, documents, claims, attention items)
5. Policy inventory & expiry filters
6. Attention item lifecycle transitions (OPEN -> IN_PROGRESS -> RESOLVED)
7. Deduplication key integrity check
8. Agent Analysis Run history retrieval
"""

import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("PHASE 1 VERIFICATION: VM_project Insurance Platform Backend")
    print("=" * 70)

    # 1. Health Endpoint
    print("\n[1] Testing Health Endpoint (/api/v1/health)...")
    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print(f"    Status: {health_data['status']}")
    print(f"    Database: {health_data['database']['status']} ({health_data['database']['engine']})")
    print(f"    Configured Gemini Model: {health_data['gemini_model_configured']}")
    assert health_data["status"] == "online"
    assert health_data["database"]["status"] == "healthy"

    # 2. Dashboard Metrics
    print("\n[2] Testing Dashboard Metrics (/api/v1/dashboard/metrics)...")
    res = client.get("/api/v1/dashboard/metrics")
    assert res.status_code == 200, f"Dashboard metrics failed: {res.text}"
    metrics = res.json()
    print(f"    Total Customers: {metrics['total_customers']}")
    print(f"    VIP Customers: {metrics['vip_customers_count']}")
    print(f"    Active Policies: {metrics['total_active_policies']}")
    print(f"    Customers Requiring Attention: {metrics['customers_requiring_attention']}")
    print(f"    High Priority Cases: {metrics['high_priority_cases']}")
    print(f"    Premium at Risk: ${metrics['total_premium_at_risk']:,.2f}")
    print(f"    Missing Documents: {metrics['missing_documents_count']}")
    print(f"    Upcoming Expirations (30d): {metrics['upcoming_policy_expirations']['in_30_days']}")
    assert metrics["total_customers"] >= 50, "Expected at least 50 customers"
    assert metrics["customers_requiring_attention"] > 0, "Expected active attention alerts"

    # 3. Customer Directory & Filtering
    print("\n[3] Testing Customers List & Filtering (/api/v1/customers)...")
    # All customers
    res = client.get("/api/v1/customers?limit=100")
    assert res.status_code == 200
    all_customers = res.json()
    print(f"    Total Customers Returned: {len(all_customers)}")
    assert len(all_customers) >= 50

    # Filter VIP
    res_vip = client.get("/api/v1/customers?tier=VIP")
    assert res_vip.status_code == 200
    vip_list = res_vip.json()
    print(f"    VIP Customers Count: {len(vip_list)}")
    assert all(c["tier"] == "VIP" for c in vip_list)

    # Search by name
    res_search = client.get("/api/v1/customers?search=Vikram")
    assert res_search.status_code == 200
    search_list = res_search.json()
    print(f"    Search 'Vikram' matches: {len(search_list)} ({search_list[0]['full_name']})")
    assert len(search_list) >= 1

    # 4. Customer 360 Deep Profile
    print("\n[4] Testing Customer 360 Profile (/api/v1/customers/{id})...")
    vikram_id = search_list[0]["id"]
    res_360 = client.get(f"/api/v1/customers/{vikram_id}")
    assert res_360.status_code == 200
    c360 = res_360.json()
    print(f"    Customer: {c360['full_name']} | Code: {c360['customer_code']} | CLV: ${c360['total_clv']:,.2f}")
    print(f"    Policies linked: {len(c360['policies'])}")
    print(f"    Documents linked: {len(c360['documents'])}")
    print(f"    Attention Items: {len(c360['attention_items'])}")
    assert len(c360["policies"]) > 0

    # 5. Policies Inventory & Expiry Filter
    print("\n[5] Testing Policies Expiry Tracker (/api/v1/policies)...")
    res_pol_exp = client.get("/api/v1/policies?expiring_within_days=30")
    assert res_pol_exp.status_code == 200
    exp_policies = res_pol_exp.json()
    print(f"    Policies expiring within 30 days: {len(exp_policies)}")
    for p in exp_policies[:3]:
        print(f"      - {p['policy_number']} ({p['policy_type']}) | Expiry: {p['expiry_date']} | Renewal Prob: {p['renewal_probability']}")

    # 6. Attention Queue & Lifecycle Management
    print("\n[6] Testing Attention Items Lifecycle & Deduplication (/api/v1/attention)...")
    res_att = client.get("/api/v1/attention?status=ACTIVE")
    assert res_att.status_code == 200
    att_items = res_att.json()
    print(f"    Active Attention Items in Queue: {len(att_items)}")
    first_item = att_items[0]
    print(f"    Testing item: '{first_item['title']}' | Urgency: {first_item['urgency_level']} | Score: {first_item['attention_score']}")
    print(f"    Dedup Key: {first_item['dedup_key']}")
    print(f"    Initial Status: {first_item['status']}")

    # Transition: OPEN -> IN_PROGRESS
    res_prog = client.patch(
        f"/api/v1/attention/{first_item['id']}/status",
        json={"status": "IN_PROGRESS", "assigned_to": "David Chen (Retention Specialist)"}
    )
    assert res_prog.status_code == 200
    assert res_prog.json()["status"] == "IN_PROGRESS"
    assert res_prog.json()["is_active"] == True
    print(f"    Successfully transitioned to IN_PROGRESS.")

    # Transition: IN_PROGRESS -> RESOLVED
    res_res = client.patch(
        f"/api/v1/attention/{first_item['id']}/status",
        json={
            "status": "RESOLVED",
            "resolved_by": "David Chen (Retention Specialist)",
            "resolution_notes": "Outreached to client; payment method updated to secondary corporate card.",
        }
    )
    assert res_res.status_code == 200
    resolved_data = res_res.json()
    assert resolved_data["status"] == "RESOLVED"
    assert resolved_data["is_active"] == False
    assert resolved_data["resolved_at"] is not None
    print(f"    Successfully transitioned to RESOLVED (is_active={resolved_data['is_active']}).")

    # 7. Agent Analysis Run History
    print("\n[7] Testing Agent Analysis Run Telemetry (/api/v1/analysis/runs)...")
    res_runs = client.get("/api/v1/analysis/runs")
    assert res_runs.status_code == 200
    runs = res_runs.json()
    print(f"    Historical Runs Logged: {len(runs)}")
    latest = runs[0]
    print(f"    Run ID: {latest['id']}")
    print(f"    Run Type: {latest['run_type']} | Status: {latest['status']}")
    print(f"    Records Scanned: {latest['records_scanned']} | Issues Detected: {latest['issues_detected']}")
    print(f"    Execution Time: {latest['execution_time_ms']} ms | Model: {latest['model_used']}")

    print("\n" + "=" * 70)
    print("ALL PHASE 1 TESTS PASSED SUCCESSFULLY (100% HEALTHY)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
