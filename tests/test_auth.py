from tests.conftest import get_auth_headers

def test_register_customer(client):
    payload = {
        "email": "newcustomer@example.com",
        "password": "SecurePassword123!",
        "full_name": "Ramesh Patel",
        "phone": "9123456780",
        "consumer_number": "CN-20001",
        "address": "45 Park Street",
        "city": "Mumbai",
        "pincode": "400001",
        "connection_type": "14.2kg Domestic"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newcustomer@example.com"
    assert data["role"] == "CUSTOMER"
    assert data["customer_profile"]["consumer_number"] == "CN-20001"

def test_register_duplicate_email(client, seed_data):
    payload = {
        "email": "customer1@example.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
        "phone": "9123456789",
        "consumer_number": "CN-99999",
        "address": "Anywhere",
        "city": "City",
        "pincode": "123456"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "Email is already registered" in response.json()["detail"]

def test_login_all_four_roles(client, seed_data):
    roles_credentials = [
        ("customer1@example.com", "Pass123!", "CUSTOMER"),
        ("driver1@example.com", "Pass123!", "DELIVERY_BOY"),
        ("admin@example.com", "AdminPass123!", "ADMIN"),
        ("auditor@example.com", "AuditorPass123!", "AUDITOR")
    ]
    for email, password, expected_role in roles_credentials:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        res = response.json()
        assert res["role"] == expected_role
        assert "access_token" in res
        assert res["token_type"] == "bearer"

def test_login_invalid_password(client, seed_data):
    response = client.post("/api/v1/auth/login", json={"email": "customer1@example.com", "password": "WrongPassword"})
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_get_current_user_me(client, seed_data):
    headers = get_auth_headers(seed_data["customer"])
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == seed_data["customer"].email

def test_get_me_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
