from tests.conftest import get_auth_headers

def test_admin_get_users(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 6

def test_admin_create_staff_user(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    payload = {
        "email": "driver3@example.com",
        "password": "PassPassword123!",
        "full_name": "Rohan Das",
        "phone": "9887766554",
        "role": "DELIVERY_BOY",
        "employee_code": "EMP-003",
        "vehicle_number": "KA-01-EE-9999",
        "assigned_hub_zone": "East Hub"
    }
    res = client.post("/api/v1/admin/users", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["role"] == "DELIVERY_BOY"
    assert res.json()["staff_profile"]["employee_code"] == "EMP-003"

def test_admin_update_user_status(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    user_id = seed_data["customer"].id
    res = client.put(f"/api/v1/admin/users/{user_id}/status", json={"is_active": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

def test_admin_inventory_flow(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    res = client.get("/api/v1/admin/inventory", headers=headers)
    assert res.status_code == 200

    new_cyl = {
        "serial_number": "CYL-9003",
        "cylinder_type": "14.2kg",
        "status": "IN_STOCK",
        "batch_code": "BATCH-2026-B"
    }
    res_create = client.post("/api/v1/admin/inventory", json=new_cyl, headers=headers)
    assert res_create.status_code == 201
    cyl_id = res_create.json()["id"]

    res_update = client.put(f"/api/v1/admin/inventory/{cyl_id}", json={"status": "MAINTENANCE"}, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "MAINTENANCE"

def test_admin_assign_booking(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    booking_id = seed_data["booking"].id
    payload = {
        "delivery_boy_id": seed_data["delivery_boy2"].id,
        "notes": "Reassigned to South Hub driver"
    }
    res = client.post(f"/api/v1/admin/bookings/{booking_id}/assign", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["delivery_boy_id"] == seed_data["delivery_boy2"].id

def test_admin_financial_correction(client, seed_data):
    headers_driver = get_auth_headers(seed_data["delivery_boy"])
    assignment_id = seed_data["assignment"].id
    client.post(f"/api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment", json={
        "amount": 700.0,
        "payment_method": "CASH"
    }, headers=headers_driver)

    headers_admin = get_auth_headers(seed_data["admin"])
    cust_payments = client.get("/api/v1/customer/payments", headers=get_auth_headers(seed_data["customer"])).json()
    payment_id = cust_payments[0]["id"]

    correction_payload = {
        "payment_id": payment_id,
        "corrected_amount": 650.0,
        "reason": "Customer overcharged by 50 rupees by cash collection error",
        "audit_notes": "Correction verified against physical receipt 101"
    }
    res_corr = client.post("/api/v1/admin/financial/correct", json=correction_payload, headers=headers_admin)
    assert res_corr.status_code == 201
    assert res_corr.json()["original_amount"] == 700.0
    assert res_corr.json()["corrected_amount"] == 650.0

def test_admin_dashboard_overview(client, seed_data):
    headers = get_auth_headers(seed_data["admin"])
    res = client.get("/api/v1/admin/dashboard/overview", headers=headers)
    assert res.status_code == 200
    assert "total_customers" in res.json()
    assert "total_delivery_staff" in res.json()
