from tests.conftest import get_auth_headers

def test_auditor_get_reconciliation_reports(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/auditor/reconciliation-reports", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert "is_reconciled" in res.json()[0]

def test_auditor_get_discrepancy_evidence(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/auditor/discrepancy-evidence", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_auditor_get_financial_summaries(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/auditor/financial-summaries", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_sales_value" in data
    assert "collections_by_method" in data
    assert "net_correction_variance" in data

def test_auditor_get_financial_corrections_history(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/auditor/financial-corrections", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_auditor_get_audit_logs(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/auditor/audit-logs", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_auditor_cannot_mutate_operational_records(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    assignment_id = seed_data["assignment"].id

    res_post_booking = client.post("/api/v1/customer/bookings", json={
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-10"
    }, headers=headers)
    assert res_post_booking.status_code == 403

    res_outcome = client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/outcome", json={
        "outcome": "DELIVERED_SUCCESS"
    }, headers=headers)
    assert res_outcome.status_code == 403

    res_payment = client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment", json={
        "amount": 650.0,
        "payment_method": "CASH"
    }, headers=headers)
    assert res_payment.status_code == 403

    res_inventory = client.post("/api/v1/admin/inventory", json={
        "serial_number": "CYL-9999",
        "cylinder_type": "14.2kg",
        "batch_code": "BATCH-X"
    }, headers=headers)
    assert res_inventory.status_code == 403

    res_correction = client.post("/api/v1/admin/financial/correct", json={
        "payment_id": 1,
        "corrected_amount": 500.0,
        "reason": "Auditor trial edit",
        "audit_notes": "Not permitted"
    }, headers=headers)
    assert res_correction.status_code == 403
