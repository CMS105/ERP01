from tests.conftest import get_auth_headers

def test_customer_get_profile(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    response = client.get("/api/v1/customer/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["consumer_number"] == "CN-10001"
    assert data["city"] == "Bengaluru"

def test_customer_update_profile(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    response = client.put("/api/v1/customer/profile", json={
        "address": "99 Residency Road",
        "city": "Bengaluru",
        "pincode": "560025",
        "phone": "9988776655"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["address"] == "99 Residency Road"

def test_customer_create_booking_success(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    payload = {
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-05"
    }
    response = client.post("/api/v1/customer/bookings", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["cylinder_type"] == "14.2kg"
    assert data["status"] == "PENDING"
    assert data["net_payable"] == 650.0

def test_customer_quota_exceeded(client, seed_data, db_session):
    headers = get_auth_headers(seed_data["customer"])
    profile = seed_data["customer"].customer_profile
    profile.quota_used_this_year = 12
    db_session.commit()

    payload = {
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-05"
    }
    response = client.post("/api/v1/customer/bookings", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Annual subsidized cylinder quota exceeded" in response.json()["detail"]

def test_customer_get_own_bookings_only(client, seed_data):
    headers1 = get_auth_headers(seed_data["customer"])
    headers2 = get_auth_headers(seed_data["customer2"])

    response1 = client.get("/api/v1/customer/bookings", headers=headers1)
    assert response1.status_code == 200
    assert len(response1.json()) >= 1
    assert response1.json()[0]["booking_number"] == "BK-TEST-1001"

    response2 = client.get("/api/v1/customer/bookings", headers=headers2)
    assert response2.status_code == 200
    assert len(response2.json()) == 0

def test_customer_cannot_access_other_customer_booking(client, seed_data):
    headers2 = get_auth_headers(seed_data["customer2"])
    booking_id = seed_data["booking"].id
    response = client.get(f"/api/v1/customer/bookings/{booking_id}", headers=headers2)
    assert response.status_code == 404

def test_customer_view_deliveries(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    response = client.get("/api/v1/customer/deliveries", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["booking_id"] == seed_data["booking"].id

def test_customer_view_payments(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    response = client.get("/api/v1/customer/payments", headers=headers)
    assert response.status_code == 200
