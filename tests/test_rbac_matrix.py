import pytest
from tests.conftest import get_auth_headers

@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/delivery-boy/deliveries/assigned", "get", None),
    ("/api/v1/admin/users", "get", None),
    ("/api/v1/admin/inventory", "get", None),
    ("/api/v1/auditor/reconciliation-reports", "get", None),
    ("/api/v1/auditor/discrepancy-evidence", "get", None),
    ("/api/v1/auditor/financial-summaries", "get", None),
])
def test_customer_denied_other_roles_routes(client, seed_data, endpoint, method, payload):
    headers = get_auth_headers(seed_data["customer"])
    func = getattr(client, method)
    res = func(endpoint, json=payload, headers=headers) if payload else func(endpoint, headers=headers)
    assert res.status_code == 403

@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/customer/profile", "get", None),
    ("/api/v1/customer/bookings", "get", None),
    ("/api/v1/admin/users", "get", None),
    ("/api/v1/admin/inventory", "get", None),
    ("/api/v1/auditor/reconciliation-reports", "get", None),
    ("/api/v1/auditor/financial-summaries", "get", None),
])
def test_delivery_boy_denied_other_roles_routes(client, seed_data, endpoint, method, payload):
    headers = get_auth_headers(seed_data["delivery_boy"])
    func = getattr(client, method)
    res = func(endpoint, json=payload, headers=headers) if payload else func(endpoint, headers=headers)
    assert res.status_code == 403

@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/customer/profile", "get", None),
    ("/api/v1/customer/bookings", "get", None),
    ("/api/v1/delivery-boy/deliveries/assigned", "get", None),
    ("/api/v1/admin/users", "get", None),
    ("/api/v1/admin/inventory", "get", None),
])
def test_auditor_denied_non_auditor_routes(client, seed_data, endpoint, method, payload):
    headers = get_auth_headers(seed_data["auditor"])
    func = getattr(client, method)
    res = func(endpoint, json=payload, headers=headers) if payload else func(endpoint, headers=headers)
    assert res.status_code == 403

@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/customer/profile", "get", None),
    ("/api/v1/customer/bookings", "get", None),
    ("/api/v1/delivery-boy/deliveries/assigned", "get", None),
    ("/api/v1/auditor/reconciliation-reports", "get", None),
])
def test_admin_denied_unauthorized_routes(client, seed_data, endpoint, method, payload):
    headers = get_auth_headers(seed_data["admin"])
    func = getattr(client, method)
    res = func(endpoint, json=payload, headers=headers) if payload else func(endpoint, headers=headers)
    assert res.status_code == 403
