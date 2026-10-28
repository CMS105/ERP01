from typing import Optional
from fastapi import APIRouter, Depends, Query, status, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_customer
from app.schemas import (
    ChatbotMessageRequest, ChatbotMessageResponse,
    ChatSessionHistoryOut
)
from app.services import ChatbotService

router = APIRouter(prefix="/api/v1/chatbot", tags=["AI Customer Support Chatbot"])

@router.post("/message", response_model=ChatbotMessageResponse, status_code=status.HTTP_200_OK)
def send_chatbot_message(
    payload: ChatbotMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Authenticated customer chat endpoint.
    Answers LPG ERP questions, performs grounded account/booking lookups,
    proposes troubleshooting steps with resolution tracking ('Has this resolved your issue?'),
    and automatically escalates unresolved or emergency issues to support tickets.
    """
    return ChatbotService.process_message(db, current_user, payload)

@router.get("/sessions/{session_id}/history", response_model=ChatSessionHistoryOut)
def get_chat_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Retrieves chronological chat history for a session owned by the authenticated customer.
    Enforces customer isolation and tenant privacy.
    """
    return ChatbotService.get_session_history(db, current_user, session_id=session_id, limit=limit)

@router.post("/sessions/{session_id}/escalate", response_model=ChatbotMessageResponse)
def escalate_chat_session(
    session_id: str,
    reason: Optional[str] = Query("Customer requested manual escalation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    """
    Manually escalates an active chat session to a human admin/staff support ticket.
    """
    return ChatbotService.manual_escalate_session(db, current_user, session_id=session_id, reason=reason)
