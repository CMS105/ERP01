from datetime import datetime, timezone
from tests.conftest import get_auth_headers

def test_delivery_boy_get_assigned_deliveries(client, seed_data):
    headers1 = get_auth_headers(seed_data["delivery_boy"])
    headers2 = get_auth_headers(seed_data["delivery_boy2"])

    res1 = client.get("/api/v1/delivery-boy/deliveries/assigned", headers=headers1)
    assert res1.status_code == 200
    assert len(res1.json()) == 1
    assert res1.json()[0]["id"] == seed_data["assignment"].id

    res2 = client.get("/api/v1/delivery-boy/deliveries/assigned", headers=headers2)
    assert res2.status_code == 200
    assert len(res2.json()) == 0

def test_delivery_boy_record_outcome_success(client, seed_data):
    headers = get_auth_headers(seed_data["delivery_boy"])
    assignment_id = seed_data["assignment"].id
    payload = {
        "outcome": "DELIVERED_SUCCESS",
        "empty_cylinder_returned_serial": "CYL-9002",
        "customer_signature_data": "base64_sig_data",
        "offline_sync_id": "OFFLINE-001"
    }
    res = client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/outcome", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["outcome"] == "DELIVERED_SUCCESS"

    res_dup = client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/outcome", json=payload, headers=headers)
    assert res_dup.status_code == 400

def test_delivery_boy_collect_payment(client, seed_data):
    headers = get_auth_headers(seed_data["delivery_boy"])
    assignment_id = seed_data["assignment"].id
    payload = {
        "amount": 650.0,
        "payment_method": "CASH",
        "transaction_reference": "CASH-REC-101"
    }
    res = client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["amount"] == 650.0
    assert res.json()["payment_status"] == "COLLECTED"
    assert res.json()["payment_method"] == "CASH"

def test_delivery_boy_sync_offline_batch(client, seed_data):
    headers = get_auth_headers(seed_data["delivery_boy"])
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "outcomes": [
            {
                "offline_sync_id": "OFFLINE-SYNC-999",
                "assignment_id": seed_data["assignment"].id,
                "outcome": "DELIVERED_SUCCESS",
                "outcome_timestamp": now_iso,
                "empty_cylinder_returned_serial": "CYL-9002",
                "failure_reason": None,
                "customer_signature_data": "data"
            }
        ],
        "payments": [
            {
                "booking_id": seed_data["booking"].id,
                "amount": 650.0,
                "payment_method": "UPI",
                "transaction_reference": "UPI-REF-888",
                "collected_at": now_iso
            }
        ]
    }
    res = client.post("/api/v1/delivery-boy/sync-offline", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["synced_outcomes_count"] == 1
    assert data["synced_payments_count"] == 1
    assert len(data["errors"]) == 0

    res_idempotent = client.post("/api/v1/delivery-boy/sync-offline", json=payload, headers=headers)
    assert res_idempotent.status_code == 200
    assert res_idempotent.json()["synced_outcomes_count"] == 0
