import pytest
from tests.conftest import get_auth_headers
from app.models import (
    DeliveryConfirmationRequest, DeliveryTransaction, DeliveryRequestStatus,
    PaymentRecord, PaymentStatus, BookingStatus
)

def test_delivery_partner_create_confirmation_request(client, seed_data, db_session):
    headers = get_auth_headers(seed_data["delivery_boy"])
    assignment = seed_data["assignment"]

    payload = {
        "cylinder_serial": "CYL-TEST-001",
        "notes": "Arrived at customer premises"
    }
    response = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json=payload,
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "REQUESTED"
    assert data["booking_id"] == assignment.booking_id
    assert data["customer_id"] == seed_data["customer"].id
    assert data["delivery_partner_id"] == seed_data["delivery_boy"].id
    assert data["amount_due"] == assignment.booking.net_payable
    assert data["cylinder_serial"] == "CYL-TEST-001"
    assert data["request_id"].startswith("REQ-")
    assert data["transaction_reference"] is None

    # Verify database persistence
    dcr = db_session.query(DeliveryConfirmationRequest).filter(
        DeliveryConfirmationRequest.request_id == data["request_id"]
    ).first()
    assert dcr is not None
    assert dcr.status == DeliveryRequestStatus.REQUESTED
    assert dcr.notes == "Arrived at customer premises"

def test_delivery_partner_cannot_request_unassigned_booking(client, seed_data):
    # Driver 2 is not assigned to this delivery
    headers = get_auth_headers(seed_data["delivery_boy2"])
    assignment = seed_data["assignment"]

    response = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=headers
    )
    assert response.status_code == 404

def test_customer_list_pending_requests(client, seed_data):
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust_headers = get_auth_headers(seed_data["customer"])
    other_cust_headers = get_auth_headers(seed_data["customer2"])
    assignment = seed_data["assignment"]

    # Driver requests confirmation
    req_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=driver_headers
    )
    assert req_res.status_code == 201
    req_id = req_res.json()["request_id"]

    # Customer 1 lists pending requests
    pending_res = client.get("/api/v1/customer/delivery-requests/pending", headers=cust_headers)
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    assert len(pending_list) >= 1
    assert any(r["request_id"] == req_id for r in pending_list)

    # Customer 2 (different customer) cannot see this pending request
    other_pending_res = client.get("/api/v1/customer/delivery-requests/pending", headers=other_cust_headers)
    assert other_pending_res.status_code == 200
    assert not any(r["request_id"] == req_id for r in other_pending_res.json())

def test_customer_accept_confirmation_request_generates_transaction(client, seed_data, db_session):
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust_headers = get_auth_headers(seed_data["customer"])
    assignment = seed_data["assignment"]

    # Driver requests confirmation
    req_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={"cylinder_serial": "CYL-9001"},
        headers=driver_headers
    )
    assert req_res.status_code == 201
    request_id = req_res.json()["request_id"]

    # Customer accepts
    accept_res = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust_headers
    )
    assert accept_res.status_code == 200
    data = accept_res.json()
    assert data["status"] == "ACCEPTED"
    tx_ref = data["transaction_reference"]
    assert tx_ref is not None
    assert tx_ref.startswith("TXN-")
    assert len(tx_ref) >= 36  # "TXN-" + 32 hex chars

    # Safe state transitions: Customer acceptance alone must not mark delivery completed or payment settled
    assert assignment.status != "DELIVERED"
    payment = db_session.query(PaymentRecord).filter(PaymentRecord.booking_id == assignment.booking_id).first()
    assert payment is not None
    assert payment.payment_status == PaymentStatus.PENDING  # Not settled
    assert payment.transaction_reference == tx_ref

    # Verify transaction record exists in DB
    tx = db_session.query(DeliveryTransaction).filter(DeliveryTransaction.transaction_reference == tx_ref).first()
    assert tx is not None
    assert tx.status == "ACCEPTED"
    assert tx.booking_id == assignment.booking_id
    assert tx.customer_id == seed_data["customer"].id
    assert tx.delivery_partner_id == seed_data["delivery_boy"].id
    assert tx.payment_record_id == payment.id
    assert tx.delivery_execution_id is None  # No outcome recorded yet

def test_duplicate_acceptance_is_idempotent(client, seed_data, db_session):
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust_headers = get_auth_headers(seed_data["customer"])
    assignment = seed_data["assignment"]

    # 1. Driver requests
    req_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=driver_headers
    )
    assert req_res.status_code == 201
    request_id = req_res.json()["request_id"]

    # 2. Customer accepts first time
    accept1 = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust_headers
    )
    assert accept1.status_code == 200
    tx_ref_1 = accept1.json()["transaction_reference"]

    # 3. Customer accepts second time (retry or double-click)
    accept2 = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust_headers
    )
    assert accept2.status_code == 200
    tx_ref_2 = accept2.json()["transaction_reference"]

    # Must return identical transaction reference
    assert tx_ref_1 == tx_ref_2

    # Verify NO duplicate transaction in database
    tx_count = db_session.query(DeliveryTransaction).filter(
        DeliveryTransaction.booking_id == assignment.booking_id
    ).count()
    assert tx_count == 1

def test_customer_reject_workflow(client, seed_data, db_session):
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust_headers = get_auth_headers(seed_data["customer"])
    assignment = seed_data["assignment"]

    # Driver requests
    req_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=driver_headers
    )
    assert req_res.status_code == 201
    request_id = req_res.json()["request_id"]

    # Customer rejects
    reject_res = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/reject",
        json={"rejection_reason": "Not at home, reschedule for tomorrow"},
        headers=cust_headers
    )
    assert reject_res.status_code == 200
    data = reject_res.json()
    assert data["status"] == "REJECTED"
    assert data["rejection_reason"] == "Not at home, reschedule for tomorrow"
    assert data["transaction_reference"] is None

    # Cannot accept a rejected request
    cannot_accept = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust_headers
    )
    assert cannot_accept.status_code == 400

    # Delivery partner cannot complete a rejected delivery
    outcome_payload = {
        "outcome": "DELIVERED_SUCCESS",
        "empty_cylinder_returned_serial": "CYL-9002",
        "customer_signature_data": "sig",
        "offline_sync_id": "OFFLINE-REJ-01"
    }
    outcome_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/outcome",
        json=outcome_payload,
        headers=driver_headers
    )
    assert outcome_res.status_code == 400

def test_unauthorized_access_protection(client, seed_data):
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust1_headers = get_auth_headers(seed_data["customer"])
    cust2_headers = get_auth_headers(seed_data["customer2"])
    assignment = seed_data["assignment"]

    # Driver requests confirmation
    req_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=driver_headers
    )
    assert req_res.status_code == 201
    request_id = req_res.json()["request_id"]

    # Customer 2 attempts to accept Customer 1's request -> 403 Forbidden
    unauth_accept = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust2_headers
    )
    assert unauth_accept.status_code == 403

    # Customer 2 attempts to reject Customer 1's request -> 403 Forbidden
    unauth_reject = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/reject",
        json={"rejection_reason": "Malicious reject"},
        headers=cust2_headers
    )
    assert unauth_reject.status_code == 403

    # Customer attempts to call delivery partner endpoints -> 403 Forbidden
    driver_endpoint_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={},
        headers=cust1_headers
    )
    assert driver_endpoint_res.status_code == 403

def test_full_state_transitions_lifecycle(client, seed_data, db_session):
    """
    Lifecycle:
    REQUESTED -> ACCEPTED -> IN_PROGRESS -> DELIVERED & Payment COLLECTED
    """
    driver_headers = get_auth_headers(seed_data["delivery_boy"])
    cust_headers = get_auth_headers(seed_data["customer"])
    assignment = seed_data["assignment"]

    # 1. Driver initiates: REQUESTED
    r1 = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/request-confirmation",
        json={"cylinder_serial": "CYL-101"},
        headers=driver_headers
    )
    assert r1.status_code == 201
    request_id = r1.json()["request_id"]
    assert r1.json()["status"] == "REQUESTED"

    # Driver cannot deliver while still REQUESTED
    premature_outcome = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/outcome",
        json={"outcome": "DELIVERED_SUCCESS"},
        headers=driver_headers
    )
    assert premature_outcome.status_code == 400

    # 2. Customer approves: ACCEPTED
    r2 = client.post(
        f"/api/v1/customer/delivery-requests/{request_id}/accept",
        headers=cust_headers
    )
    assert r2.status_code == 200
    tx_ref = r2.json()["transaction_reference"]
    assert r2.json()["status"] == "ACCEPTED"

    # 3. Driver starts handover: IN_PROGRESS
    r3 = client.post(
        f"/api/v1/delivery-boy/delivery-requests/{request_id}/in-progress",
        headers=driver_headers
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "IN_PROGRESS"

    # 4. Driver records outcome: DELIVERED
    outcome_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/outcome",
        json={
            "outcome": "DELIVERED_SUCCESS",
            "empty_cylinder_returned_serial": "CYL-OLD-99",
            "customer_signature_data": "sig_data_base64",
            "offline_sync_id": "OFFLINE-FLOW-01"
        },
        headers=driver_headers
    )
    assert outcome_res.status_code == 201
    assert outcome_res.json()["outcome"] == "DELIVERED_SUCCESS"
    assert outcome_res.json()["transaction_reference"] == tx_ref

    # Verify transaction record updated
    tx = db_session.query(DeliveryTransaction).filter(
        DeliveryTransaction.transaction_reference == tx_ref
    ).first()
    assert tx.status == "DELIVERED"
    assert tx.delivery_execution_id == outcome_res.json()["id"]

    # 5. Collect payment
    pay_res = client.post(
        f"/api/v1/delivery-boy/deliveries/{assignment.id}/collect-payment",
        json={
            "amount": 650.0,
            "payment_method": "UPI",
            "transaction_reference": tx_ref
        },
        headers=driver_headers
    )
    assert pay_res.status_code == 201
    assert pay_res.json()["payment_status"] == "COLLECTED"
    assert pay_res.json()["transaction_reference"] == tx_ref

    # 6. Retrieve shared transaction by both apps
    driver_tx_get = client.get(
        f"/api/v1/delivery-boy/transactions/{tx_ref}",
        headers=driver_headers
    )
    assert driver_tx_get.status_code == 200
    assert driver_tx_get.json()["transaction_reference"] == tx_ref
    assert driver_tx_get.json()["status"] == "DELIVERED"

    cust_tx_get = client.get(
        f"/api/v1/customer/transactions/{tx_ref}",
        headers=cust_headers
    )
    assert cust_tx_get.status_code == 200
    assert cust_tx_get.json()["transaction_reference"] == tx_ref

    shared_tx_get = client.get(
        f"/api/v1/transactions/{tx_ref}",
        headers=cust_headers
    )
    assert shared_tx_get.status_code == 200
    assert shared_tx_get.json()["transaction_reference"] == tx_ref
