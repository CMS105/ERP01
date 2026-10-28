from unittest.mock import MagicMock, patch
import pytest
from app.models import SupportTicketStatus, SupportTicket
from tests.conftest import get_auth_headers

def test_chatbot_query_resolution_mocked_gemini(client, seed_data):
    """Test standard query flow with mocked Gemini proposing a solution."""
    headers = get_auth_headers(seed_data["customer"])
    
    mock_response = MagicMock()
    mock_response.text = "Based on your records, your cylinder was dispatched. Check regulator connection.\n\nHas this resolved your issue?"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.get_gemini_client", return_value=mock_client):
        response = client.post(
            "/api/v1/chatbot/message",
            json={"message": "When will my cylinder arrive?"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resolution_state"] == "PROPOSED_SOLUTION"
        assert data["requires_confirmation"] is True
        assert data["escalated"] is False
        assert "Has this resolved your issue?" in data["assistant_message"]
        assert data["session_id"] is not None

def test_customer_confirms_resolution(client, seed_data):
    """Customer confirms resolution ('Yes') -> marks resolved."""
    headers = get_auth_headers(seed_data["customer"])
    
    mock_response = MagicMock()
    mock_response.text = "Try turning the regulator clockwise. Has this resolved your issue?"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.get_gemini_client", return_value=mock_client):
        res1 = client.post(
            "/api/v1/chatbot/message",
            json={"message": "Regulator seems stiff."},
            headers=headers
        )
        assert res1.status_code == 200
        session_id = res1.json()["session_id"]
        assert res1.json()["requires_confirmation"] is True

        res2 = client.post(
            "/api/v1/chatbot/message",
            json={"session_id": session_id, "message": "Yes, that worked, thank you!"},
            headers=headers
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["resolution_state"] == "RESOLVED"
        assert data2["requires_confirmation"] is False
        assert data2["escalated"] is False

def test_customer_rejects_solution_auto_escalates(client, seed_data, db_session):
    """Customer rejects solution ('No, didn't work') -> auto-escalates to WAITING_FOR_STAFF."""
    headers = get_auth_headers(seed_data["customer"])
    
    mock_response = MagicMock()
    mock_response.text = "Please check valve. Has this resolved your issue?"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.get_gemini_client", return_value=mock_client):
        res1 = client.post(
            "/api/v1/chatbot/message",
            json={"message": "Delivery is delayed 5 days."},
            headers=headers
        )
        session_id = res1.json()["session_id"]

        res2 = client.post(
            "/api/v1/chatbot/message",
            json={"session_id": session_id, "message": "No, it did not work. Still not delivered."},
            headers=headers
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["escalated"] is True
        assert data2["resolution_state"] == "ESCALATED"
        assert data2["ticket_number"] is not None
        assert data2["priority"] in ["HIGH", "CRITICAL"]

        # Check DB ticket status
        ticket = db_session.query(SupportTicket).filter(SupportTicket.id == data2["ticket_id"]).first()
        assert ticket is not None
        assert ticket.status == SupportTicketStatus.WAITING_FOR_STAFF
        assert "Customer confirmed troubleshooting steps did not resolve" in ticket.escalation_reason

def test_escalation_after_repeated_attempts(client, seed_data):
    """After configurable max attempts (3), conversation auto-escalates."""
    headers = get_auth_headers(seed_data["customer"])
    
    mock_response = MagicMock()
    mock_response.text = "Step advice. Has this resolved your issue?"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.get_gemini_client", return_value=mock_client):
        res1 = client.post("/api/v1/chatbot/message", json={"message": "Problem attempt 1"}, headers=headers)
        session_id = res1.json()["session_id"]

        res2 = client.post("/api/v1/chatbot/message", json={"session_id": session_id, "message": "Problem attempt 2"}, headers=headers)
        res3 = client.post("/api/v1/chatbot/message", json={"session_id": session_id, "message": "Problem attempt 3"}, headers=headers)
        
        data3 = res3.json()
        assert data3["escalated"] is True
        assert data3["resolution_state"] == "ESCALATED"
        assert data3["ticket_number"] is not None

def test_explicit_human_agent_request(client, seed_data, db_session):
    """Customer asks for human agent -> immediate ticket creation & escalation."""
    headers = get_auth_headers(seed_data["customer"])
    response = client.post(
        "/api/v1/chatbot/message",
        json={"message": "Please connect me to a human support agent immediately."},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["escalated"] is True
    assert data["ticket_number"] is not None
    assert data["priority"] == "HIGH"
    
    ticket = db_session.query(SupportTicket).filter(SupportTicket.id == data["ticket_id"]).first()
    assert ticket.status == SupportTicketStatus.WAITING_FOR_STAFF
    assert "explicitly requested a human" in ticket.escalation_reason

def test_gas_leak_emergency_handling(client, seed_data, db_session):
    """Gas leak trigger: CRITICAL priority, immediate safety protocol, no normal troubleshooting delay."""
    headers = get_auth_headers(seed_data["customer"])
    response = client.post(
        "/api/v1/chatbot/message",
        json={"message": "Help! There is a heavy gas leak and gas smell in my kitchen near the cylinder!"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["escalated"] is True
    assert data["priority"] == "CRITICAL"
    assert "1906" in data["assistant_message"]
    assert "regulator valve" in data["assistant_message"].lower()

    ticket = db_session.query(SupportTicket).filter(SupportTicket.id == data["ticket_id"]).first()
    assert ticket.priority == "CRITICAL"
    assert ticket.status == SupportTicketStatus.WAITING_FOR_STAFF
    assert ticket.category == "GAS_LEAK_EMERGENCY"

def test_duplicate_ticket_prevention(client, seed_data, db_session):
    """Repeated escalations reuse/append to existing open ticket without creating duplicate tickets."""
    headers = get_auth_headers(seed_data["customer"])
    
    # First escalation
    res1 = client.post("/api/v1/chatbot/message", json={"message": "Connect to support human agent."}, headers=headers)
    ticket_id1 = res1.json()["ticket_id"]
    tkt_num1 = res1.json()["ticket_number"]

    # Second escalation in new message
    res2 = client.post("/api/v1/chatbot/message", json={"message": "Talk to operator now."}, headers=headers)
    ticket_id2 = res2.json()["ticket_id"]
    tkt_num2 = res2.json()["ticket_number"]

    assert ticket_id1 == ticket_id2
    assert tkt_num1 == tkt_num2

def test_session_isolation_cross_tenant_access(client, seed_data):
    """Customer cannot access another customer's chat session or ticket."""
    headers1 = get_auth_headers(seed_data["customer"])
    headers2 = get_auth_headers(seed_data["customer2"])

    # Customer 1 starts a chat
    res1 = client.post("/api/v1/chatbot/message", json={"message": "Hello support"}, headers=headers1)
    session_id1 = res1.json()["session_id"]

    # Customer 2 tries to access customer 1's session history -> 403
    res_forbidden = client.get(f"/api/v1/chatbot/sessions/{session_id1}/history", headers=headers2)
    assert res_forbidden.status_code == 403
    assert "Access denied" in res_forbidden.json()["detail"]

    # Customer 2 tries to message into customer 1's session -> 403
    res_msg_forbidden = client.post(
        "/api/v1/chatbot/message",
        json={"session_id": session_id1, "message": "Injected message"},
        headers=headers2
    )
    assert res_msg_forbidden.status_code == 403

def test_admin_ticket_lifecycle_and_rbac(client, seed_data, db_session):
    """Admin can view pending queue, inspect ticket, assign staff, and update resolution notes."""
    customer_headers = get_auth_headers(seed_data["customer"])
    admin_headers = get_auth_headers(seed_data["admin"])

    # 1. Non-admin forbidden from admin ticket endpoints
    non_admin_res = client.get("/api/v1/admin/tickets", headers=customer_headers)
    assert non_admin_res.status_code == 403

    # 2. Customer creates an escalated ticket
    res_chat = client.post("/api/v1/chatbot/message", json={"message": "Talk to an admin executive"}, headers=customer_headers)
    ticket_id = res_chat.json()["ticket_id"]

    # 3. Admin gets pending queue summary
    queue_res = client.get("/api/v1/admin/tickets/queue/pending", headers=admin_headers)
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert queue_data["waiting_for_staff"] >= 1

    # 4. Admin lists tickets with filter
    list_res = client.get("/api/v1/admin/tickets?status=WAITING_FOR_STAFF", headers=admin_headers)
    assert list_res.status_code == 200
    assert any(t["id"] == ticket_id for t in list_res.json())

    # 5. Admin gets ticket details
    detail_res = client.get(f"/api/v1/admin/tickets/{ticket_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == ticket_id
    assert detail_res.json()["conversation_context"] is not None

    # 6. Admin assigns ticket to staff
    assign_res = client.post(
        f"/api/v1/admin/tickets/{ticket_id}/assign",
        json={"staff_user_id": seed_data["delivery_boy"].id},
        headers=admin_headers
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_staff_id"] == seed_data["delivery_boy"].id
    assert assign_res.json()["status"] == "IN_PROGRESS"

    # 7. Admin updates ticket resolution notes and marks RESOLVED
    update_res = client.put(
        f"/api/v1/admin/tickets/{ticket_id}",
        json={
            "status": "RESOLVED",
            "resolution_notes": "Cylinder dispatched via emergency vehicle. Delivery confirmed with customer."
        },
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "RESOLVED"
    assert "emergency vehicle" in update_res.json()["resolution_notes"]

def test_gemini_api_failure_manual_fallback(client, seed_data):
    """When Gemini client is unavailable or throws, system falls back gracefully to grounded account data."""
    headers = get_auth_headers(seed_data["customer"])

    # Simulate Gemini failure
    with patch("app.services.get_gemini_client", return_value=None):
        response = client.post(
            "/api/v1/chatbot/message",
            json={"message": "What is my cylinder quota status?"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_confirmation"] is True
        assert "quota" in data["assistant_message"].lower() or "subsidized" in data["assistant_message"].lower()
        assert "Has this resolved your issue?" in data["assistant_message"]

def test_customer_ticket_endpoints_and_history(client, seed_data):
    """Test customer listing own tickets and session history."""
    headers = get_auth_headers(seed_data["customer"])
    
    # Chat message
    chat_res = client.post("/api/v1/chatbot/message", json={"message": "Check my ticket status"}, headers=headers)
    session_id = chat_res.json()["session_id"]

    # History
    hist_res = client.get(f"/api/v1/chatbot/sessions/{session_id}/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()["messages"]) >= 2

    # Customer tickets list
    tkt_res = client.get("/api/v1/customer/tickets", headers=headers)
    assert tkt_res.status_code == 200
    assert isinstance(tkt_res.json(), list)
