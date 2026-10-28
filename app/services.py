import uuid
import re
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    User, UserRole, CustomerProfile, StaffProfile, CylinderInventory,
    Booking, BookingStatus, DeliveryAssignment, DeliveryExecution, DeliveryOutcome,
    PaymentRecord, PaymentStatus, PaymentMethod, CylinderStatus,
    FinancialCorrection, AuditLog, SupportTicket, SupportTicketStatus, SupportMessage,
    DeliveryConfirmationRequest, DeliveryTransaction, DeliveryRequestStatus,
    ChatSession, ChatMessage
)
from app.schemas import (
    BookingCreate, DeliveryOutcomeRequest, PaymentCollectRequest,
    OfflineSyncBatchRequest, OfflineSyncBatchResponse,
    FinancialCorrectionRequest, CylinderInventoryCreate, CylinderInventoryUpdate,
    UserCreate, CustomerProfileUpdate, SupportTicketCreate, SupportTicketEscalate,
    DeliveryConfirmationCreate, DeliveryRejectRequest,
    DeliveryConfirmationRequestOut, DeliveryTransactionOut,
    SupportTicketOut, TicketUpdateAdmin, TicketAssignAdmin,
    ChatbotMessageRequest, ChatbotMessageResponse, ChatMessageOut, ChatSessionHistoryOut
)
from app.auth import hash_password
from app.cache import cache

def redact_sensitive_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', 'XXXX-XXXX-XXXX', text)
    text = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\',\s]+', 'password="[REDACTED]"', text, flags=re.IGNORECASE)
    text = re.sub(r'token["\']?\s*[:=]\s*["\']?[^"\',\s]+', 'token="[REDACTED]"', text, flags=re.IGNORECASE)
    return text

def log_audit(db: Session, user: Optional[User], action: str, resource_type: str, resource_id: str, details: str):
    safe_details = redact_sensitive_text(details)
    log_entry = AuditLog(
        user_id=user.id if user else None,
        user_role=user.role.value if user else "SYSTEM",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=safe_details,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

class CustomerService:
    @staticmethod
    def get_profile(db: Session, current_user: User):
        profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        return profile

    @staticmethod
    def update_profile(db: Session, current_user: User, data: CustomerProfileUpdate):
        profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        if data.address is not None:
            profile.address = data.address
        if data.city is not None:
            profile.city = data.city
        if data.pincode is not None:
            profile.pincode = data.pincode
        if data.phone is not None:
            current_user.phone = data.phone
        db.commit()
        db.refresh(profile)
        cache.delete("dashboard:overview")
        log_audit(db, current_user, "UPDATE", "CustomerProfile", str(profile.id), "Customer updated contact and address details")
        return profile

    @staticmethod
    def create_booking(db: Session, current_user: User, data: BookingCreate):
        if data.idempotency_key:
            existing = db.query(Booking).filter(
                Booking.customer_id == current_user.id,
                Booking.idempotency_key == data.idempotency_key
            ).first()
            if existing:
                return existing

        is_postgres = db.bind and db.bind.dialect.name == "postgresql"

        if is_postgres:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.user_id == current_user.id
            ).with_for_update().first()
        else:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.user_id == current_user.id
            ).first()

        if not profile:
            raise HTTPException(status_code=404, detail="Customer profile not found")

        if profile.quota_used_this_year + data.quantity > profile.cylinder_quota_limit:
            raise HTTPException(status_code=400, detail="Annual subsidized cylinder quota exceeded")

        total_inventory_count = db.query(CylinderInventory).filter(
            CylinderInventory.cylinder_type == data.cylinder_type
        ).count()

        reserved_cylinders = []
        if total_inventory_count > 0:
            if is_postgres:
                available_cylinders = db.query(CylinderInventory).filter(
                    CylinderInventory.cylinder_type == data.cylinder_type,
                    CylinderInventory.status == CylinderStatus.IN_STOCK
                ).with_for_update(skip_locked=True).limit(data.quantity).all()
            else:
                available_cylinders = db.query(CylinderInventory).filter(
                    CylinderInventory.cylinder_type == data.cylinder_type,
                    CylinderInventory.status == CylinderStatus.IN_STOCK
                ).limit(data.quantity).all()

            if len(available_cylinders) < data.quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Cylinder stock unavailable: insufficient in-stock inventory"
                )

            for cyl in available_cylinders:
                cyl.status = CylinderStatus.RESERVED
                reserved_cylinders.append(cyl)

        booking_number = f"BK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        unit_price = 850.0
        total_amount = unit_price * data.quantity
        subsidy_amount = 200.0 * data.quantity
        net_payable = total_amount - subsidy_amount

        booking = Booking(
            booking_number=booking_number,
            idempotency_key=data.idempotency_key,
            customer_id=current_user.id,
            cylinder_type=data.cylinder_type,
            quantity=data.quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            subsidy_amount=subsidy_amount,
            net_payable=net_payable,
            status=BookingStatus.PENDING,
            scheduled_date=data.scheduled_date
        )
        profile.quota_used_this_year += data.quantity
        db.add(booking)
        try:
            db.commit()
            db.refresh(booking)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Booking creation failed: {e}")

        cache.delete("dashboard:overview")
        cache.delete_pattern("inventory:*")

        log_audit(db, current_user, "CREATE", "Booking", str(booking.id), f"Booking created {booking.booking_number} for net payable {net_payable}")
        return booking

    @staticmethod
    def get_bookings(db: Session, current_user: User, skip: int = 0, limit: int = 50):
        return db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(Booking.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_booking_by_id(db: Session, current_user: User, booking_id: int):
        booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == current_user.id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        return booking

    @staticmethod
    def get_deliveries(db: Session, current_user: User, skip: int = 0, limit: int = 50):
        return db.query(DeliveryAssignment).join(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(DeliveryAssignment.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_payments(db: Session, current_user: User, skip: int = 0, limit: int = 50):
        return db.query(PaymentRecord).filter(
            PaymentRecord.customer_id == current_user.id
        ).order_by(PaymentRecord.id.desc()).offset(skip).limit(limit).all()

import os
from app.config import settings

def get_gemini_client():
    gemini_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if not gemini_key or gemini_key == "MOCK_KEY":
        return None
    try:
        from google import genai
        return genai.Client(api_key=gemini_key)
    except Exception:
        return None

class SupportTicketService:
    @staticmethod
    def create_ticket(db: Session, current_user: User, data: SupportTicketCreate) -> SupportTicket:
        ticket_number = f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        ai_response_text = None

        client = get_gemini_client()
        if client:
            try:
                prompt = f"""You are a helpful customer support assistant for an LPG delivery service in India.
The customer has raised the following issue:
Category: {data.category}
Description: {data.description}
Booking ID: {data.booking_id or 'None provided'}
Transaction ID: {data.transaction_id or 'None provided'}
Priority: {data.priority or 'NORMAL'}
Language Preference: {data.language}

Provide a short, empathetic explanation and clear, safe next steps.
Do not make unauthorized promises regarding refunds or instant delivery.
Respond in {data.language}. Keep it under 3 sentences."""
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                ai_response_text = response.text
            except Exception:
                ai_response_text = "Thank you for reaching out. We have logged your issue and our support team will assist you shortly."
        else:
            ai_response_text = "Thank you for reaching out. We have logged your issue and our support team will assist you shortly."

        ticket = SupportTicket(
            ticket_number=ticket_number,
            customer_id=current_user.id,
            booking_id=data.booking_id,
            transaction_id=data.transaction_id,
            category=data.category,
            description=data.description,
            priority=data.priority or "NORMAL",
            language=data.language or "en",
            status=SupportTicketStatus.AI_ASSISTED if ai_response_text else SupportTicketStatus.OPEN,
            ai_response=ai_response_text,
            resolution_notes=data.resolution_notes,
            conversation_context=data.conversation_context
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        log_audit(db, current_user, "CREATE_TICKET", "SupportTicket", str(ticket.id), f"Created ticket {ticket_number} with priority {ticket.priority}")
        return ticket

    @staticmethod
    def get_tickets(db: Session, current_user: User, skip: int = 0, limit: int = 50) -> List[SupportTicket]:
        return db.query(SupportTicket).filter(
            SupportTicket.customer_id == current_user.id
        ).order_by(SupportTicket.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_ticket_by_id(db: Session, current_user: User, ticket_id: int) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id,
            SupportTicket.customer_id == current_user.id
        ).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")
        return ticket

    @staticmethod
    def escalate_ticket(db: Session, current_user: User, ticket_id: int, data: SupportTicketEscalate) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id,
            SupportTicket.customer_id == current_user.id
        ).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        ticket.status = SupportTicketStatus.WAITING_FOR_STAFF
        ticket.escalation_reason = data.escalation_reason
        if ticket.priority == "NORMAL":
            ticket.priority = "HIGH"
        db.commit()
        db.refresh(ticket)
        log_audit(db, current_user, "ESCALATE_TICKET", "SupportTicket", str(ticket.id), f"Escalated ticket {ticket.ticket_number} to human staff")
        return ticket

    @staticmethod
    def list_admin_tickets(
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportTicket]:
        query = db.query(SupportTicket)
        if status:
            try:
                status_enum = SupportTicketStatus(status.upper())
                query = query.filter(SupportTicket.status == status_enum)
            except ValueError:
                pass
        if priority:
            query = query.filter(SupportTicket.priority == priority.upper())
        if category:
            query = query.filter(SupportTicket.category.ilike(f"%{category}%"))
        return query.order_by(
            func.case(
                (SupportTicket.priority == 'CRITICAL', 1),
                (SupportTicket.priority == 'HIGH', 2),
                (SupportTicket.priority == 'NORMAL', 3),
                else_=4
            ),
            SupportTicket.id.desc()
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_admin_ticket(db: Session, ticket_id: int) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")
        return ticket

    @staticmethod
    def update_admin_ticket(db: Session, admin_user: User, ticket_id: int, data: TicketUpdateAdmin) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        if data.status:
            try:
                ticket.status = SupportTicketStatus(data.status.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status value: {data.status}")
        if data.priority:
            ticket.priority = data.priority.upper()
        if data.resolution_notes is not None:
            ticket.resolution_notes = data.resolution_notes
        if data.assigned_staff_id is not None:
            ticket.assigned_staff_id = data.assigned_staff_id

        db.commit()
        db.refresh(ticket)
        log_audit(
            db, admin_user, "UPDATE_TICKET_ADMIN", "SupportTicket", str(ticket.id),
            f"Admin {admin_user.username} updated ticket {ticket.ticket_number} (status={ticket.status.value}, priority={ticket.priority})"
        )
        return ticket

    @staticmethod
    def assign_admin_ticket(db: Session, admin_user: User, ticket_id: int, data: TicketAssignAdmin) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        staff_user = db.query(User).filter(User.id == data.staff_user_id).first()
        if not staff_user:
            raise HTTPException(status_code=404, detail="Assigned staff user not found")

        ticket.assigned_staff_id = data.staff_user_id
        if ticket.status in [SupportTicketStatus.OPEN, SupportTicketStatus.WAITING_FOR_STAFF, SupportTicketStatus.AI_ASSISTED]:
            ticket.status = SupportTicketStatus.IN_PROGRESS

        db.commit()
        db.refresh(ticket)
        log_audit(
            db, admin_user, "ASSIGN_TICKET", "SupportTicket", str(ticket.id),
            f"Ticket {ticket.ticket_number} assigned to staff ID {data.staff_user_id}"
        )
        return ticket

    @staticmethod
    def get_admin_queue_summary(db: Session) -> Dict[str, Any]:
        total_tickets = db.query(func.count(SupportTicket.id)).scalar() or 0
        waiting_for_staff = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.status == SupportTicketStatus.WAITING_FOR_STAFF
        ).scalar() or 0
        in_progress = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.status == SupportTicketStatus.IN_PROGRESS
        ).scalar() or 0
        open_tickets = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.status == SupportTicketStatus.OPEN
        ).scalar() or 0
        critical_count = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.priority == "CRITICAL",
            SupportTicket.status.in_([SupportTicketStatus.OPEN, SupportTicketStatus.WAITING_FOR_STAFF, SupportTicketStatus.IN_PROGRESS])
        ).scalar() or 0
        high_count = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.priority == "HIGH",
            SupportTicket.status.in_([SupportTicketStatus.OPEN, SupportTicketStatus.WAITING_FOR_STAFF, SupportTicketStatus.IN_PROGRESS])
        ).scalar() or 0

        return {
            "total_tickets": total_tickets,
            "waiting_for_staff": waiting_for_staff,
            "in_progress": in_progress,
            "open_tickets": open_tickets,
            "critical_unresolved": critical_count,
            "high_unresolved": high_count
        }


SAFETY_EMERGENCY_GUIDANCE = (
    "EMERGENCY SAFETY INSTRUCTION: Suspected LPG leak or hazard detected!\n"
    "1. Turn off the cylinder regulator valve immediately.\n"
    "2. Put out all open flames, candles, or incense.\n"
    "3. DO NOT operate any electrical switches, appliances, or mobile phones near the leak.\n"
    "4. Open all doors and windows to disperse the gas.\n"
    "5. Evacuate everyone from the premises immediately.\n"
    "6. Call the 24x7 LPG Emergency Helpline: 1906 or Fire Emergency: 101 from a safe location."
)

GAS_LEAK_KEYWORDS = [
    "gas leak", "smell gas", "lpg leak", "gas leakage", "cylinder leaking",
    "cylinder hiss", "fire", "blast", "explosion", "spark", "cylinder burning",
    "gas smell", "smelling gas", "regulator leak"
]

RESOLUTION_CONFIRMATION_KEYWORDS = [
    "yes", "yes it did", "resolved", "it worked", "fixed", "all good",
    "thank you", "thanks resolved", "solved", "no further help needed",
    "yes resolved", "it is resolved", "issue resolved", "working now"
]

RESOLUTION_REJECTION_KEYWORDS = [
    "no", "not resolved", "didn't work", "did not work", "still not working",
    "still an issue", "still having issue", "didn't solve", "no it did not",
    "problem persists", "not working", "still broken", "doesn't work"
]

HUMAN_AGENT_KEYWORDS = [
    "human", "agent", "executive", "representative", "operator", "person",
    "talk to human", "speak to human", "connect to agent", "customer care",
    "talk to someone", "admin", "speak with agent", "transfer to human"
]


class ChatbotService:
    @staticmethod
    def is_gas_leak_emergency(message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in GAS_LEAK_KEYWORDS)

    @staticmethod
    def is_resolution_confirmation(message: str) -> bool:
        cleaned = re.sub(r'[^\w\s]', '', message.lower()).strip()
        tokens = cleaned.split()
        if cleaned in RESOLUTION_CONFIRMATION_KEYWORDS:
            return True
        if tokens and tokens[0] in ["yes", "yeah", "yep", "solved", "fixed"]:
            return True
        return any(keyword in cleaned for keyword in ["it worked", "all good", "thank you", "issue resolved", "problem solved"])

    @staticmethod
    def is_resolution_rejection(message: str) -> bool:
        cleaned = re.sub(r'[^\w\s]', '', message.lower()).strip()
        tokens = cleaned.split()
        if cleaned in ["no", "nope", "not yet", "not really", "didnt work", "did not work"]:
            return True
        if tokens and tokens[0] in ["no", "nope"]:
            return True
        return any(keyword in cleaned for keyword in RESOLUTION_REJECTION_KEYWORDS)

    @staticmethod
    def is_human_agent_requested(message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in HUMAN_AGENT_KEYWORDS)

    @staticmethod
    def get_or_create_session(db: Session, current_user: User, session_id: Optional[str] = None) -> ChatSession:
        if session_id:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
            if session.customer_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this chat session")
            return session

        new_session = ChatSession(
            session_id=f"CS-{uuid.uuid4().hex[:12].upper()}",
            customer_id=current_user.id,
            status="IN_PROGRESS",
            unresolved_attempts=0
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    @staticmethod
    def build_grounding_context(db: Session, current_user: User) -> Dict[str, Any]:
        profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == current_user.id).first()
        bookings = db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(Booking.id.desc()).limit(3).all()

        payments = db.query(PaymentRecord).filter(
            PaymentRecord.customer_id == current_user.id
        ).order_by(PaymentRecord.id.desc()).limit(3).all()

        tickets = db.query(SupportTicket).filter(
            SupportTicket.customer_id == current_user.id
        ).order_by(SupportTicket.id.desc()).limit(3).all()

        pending_delivery_req = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.customer_id == current_user.id,
            DeliveryConfirmationRequest.status == DeliveryRequestStatus.REQUESTED
        ).first()

        context_data = {
            "customer": {
                "id": current_user.id,
                "name": current_user.full_name if current_user.full_name else current_user.email,
                "phone": current_user.phone if current_user.phone else "N/A",
                "consumer_number": profile.consumer_number if profile else "N/A",
                "quota_used": profile.quota_used_this_year if profile else 0,
                "quota_total": profile.cylinder_quota_limit if profile else 12,
                "connection_type": profile.connection_type if profile else "14.2kg Domestic"
            },
            "recent_bookings": [
                {
                    "id": b.id,
                    "booking_number": b.booking_number,
                    "date": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "N/A",
                    "status": b.status.value,
                    "cylinder_type": b.cylinder_type,
                    "amount": float(b.net_payable) if b.net_payable is not None else 0.0,
                    "scheduled_date": b.scheduled_date
                }
                for b in bookings
            ],
            "recent_payments": [
                {
                    "id": p.id,
                    "transaction_id": p.transaction_id,
                    "amount": float(p.amount),
                    "method": p.payment_method.value,
                    "status": p.status.value,
                    "date": p.payment_date.strftime("%Y-%m-%d %H:%M") if p.payment_date else "N/A"
                }
                for p in payments
            ],
            "support_tickets": [
                {
                    "id": t.id,
                    "ticket_number": t.ticket_number,
                    "category": t.category,
                    "status": t.status.value,
                    "priority": t.priority,
                    "created_at": t.created_at.strftime("%Y-%m-%d") if t.created_at else "N/A"
                }
                for t in tickets
            ],
            "active_pending_delivery_confirmation": {
                "request_id": pending_delivery_req.request_id,
                "booking_id": pending_delivery_req.booking_id,
                "amount_due": float(pending_delivery_req.amount_due)
            } if pending_delivery_req else None
        }
        return context_data

    @staticmethod
    def escalate_chat_to_ticket(
        db: Session,
        current_user: User,
        session: ChatSession,
        category: str,
        summary: str,
        priority: str = "NORMAL",
        escalation_reason: str = "Chatbot automatic escalation",
        booking_id: Optional[int] = None
    ) -> SupportTicket:
        open_ticket = db.query(SupportTicket).filter(
            SupportTicket.customer_id == current_user.id,
            SupportTicket.status.in_([
                SupportTicketStatus.OPEN,
                SupportTicketStatus.AI_ASSISTED,
                SupportTicketStatus.WAITING_FOR_STAFF,
                SupportTicketStatus.IN_PROGRESS
            ])
        ).order_by(SupportTicket.id.desc()).first()

        history_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.session_id
        ).order_by(ChatMessage.id.asc()).limit(10).all()

        formatted_convo = "\n".join([f"{m.sender_role.upper()}: {m.message}" for m in history_messages])

        if open_ticket:
            ticket = open_ticket
            ticket.status = SupportTicketStatus.WAITING_FOR_STAFF
            ticket.escalation_reason = escalation_reason
            if priority == "CRITICAL" or (priority == "HIGH" and ticket.priority != "CRITICAL"):
                ticket.priority = priority
            if formatted_convo:
                prev_context = ticket.conversation_context or ""
                ticket.conversation_context = f"{prev_context}\n--- Escalation Update ---\n{formatted_convo}".strip()
            if booking_id and not ticket.booking_id:
                ticket.booking_id = booking_id
        else:
            ticket_number = f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            ticket = SupportTicket(
                ticket_number=ticket_number,
                customer_id=current_user.id,
                booking_id=booking_id,
                category=category,
                description=summary,
                priority=priority,
                status=SupportTicketStatus.WAITING_FOR_STAFF,
                escalation_reason=escalation_reason,
                conversation_context=formatted_convo
            )
            db.add(ticket)

        db.flush()
        session.associated_ticket_id = ticket.id
        session.status = "ESCALATED"

        db.commit()
        db.refresh(ticket)
        log_audit(
            db, current_user, "CHATBOT_ESCALATE_TICKET", "SupportTicket", str(ticket.id),
            f"Escalated session {session.session_id} to ticket {ticket.ticket_number} (priority={ticket.priority})"
        )
        return ticket

    @staticmethod
    def generate_grounded_fallback_response(message: str, grounding_data: Dict[str, Any]) -> str:
        lowered = message.lower()
        customer = grounding_data.get("customer", {})
        bookings = grounding_data.get("recent_bookings", [])
        payments = grounding_data.get("recent_payments", [])
        tickets = grounding_data.get("support_tickets", [])
        pending_del = grounding_data.get("active_pending_delivery_confirmation")

        if "ticket" in lowered:
            if tickets:
                t = tickets[0]
                return f"Your latest support ticket is #{t['ticket_number']} for {t['category']} with status: {t['status']} (Priority: {t['priority']}). Has this resolved your issue?"
            return "You do not have any open support tickets at the moment. If you are experiencing an issue, please let me know details so I can log one for you. Has this resolved your issue?"

        if "pay" in lowered or "money" in lowered or "receipt" in lowered:
            if payments:
                p = payments[0]
                return f"Your most recent payment record is Transaction #{p['transaction_id']} for ₹{p['amount']} via {p['method']} with status: {p['status']}. Has this resolved your issue?"
            return "No recent payment records found for your account. Please share your transaction reference if you were debited. Has this resolved your issue?"

        if "delivery" in lowered or "cylinder" in lowered or "boy" in lowered:
            if pending_del:
                return f"You have an active delivery confirmation request #{pending_del['request_id']} for Booking #{pending_del['booking_id']} with ₹{pending_del['amount_due']} due. Please approve or reject via your delivery screen. Has this resolved your issue?"
            if bookings:
                b = bookings[0]
                return f"Your latest booking #{b.get('booking_number', b['id'])} ({b['cylinder_type']}) has status: {b['status']}. Scheduled date: {b.get('scheduled_date', 'N/A')}. Has this resolved your issue?"
            return "You have no active cylinder deliveries in progress right now. Would you like to book a refill? Has this resolved your issue?"

        if "quota" in lowered or "refill" in lowered or "booking" in lowered:
            used = customer.get("quota_used", 0)
            total = customer.get("quota_total", 12)
            rem = max(0, total - used)
            return f"You have used {used} of your {total} subsidized cylinders for this fiscal year ({rem} remaining). Has this resolved your issue?"

        return "Thank you for contacting LPG Customer Care. I have verified your account and recent records. Please let me know if you would like me to connect you with an admin support agent. Has this resolved your issue?"

    @staticmethod
    def call_gemini_chat(prompt: str, grounding_data: Dict[str, Any], conversation_history: List[ChatMessage]) -> Optional[str]:
        client = get_gemini_client()
        if not client:
            return None

        recent_dialogue = "\n".join([f"{m.sender_role.upper()}: {m.message}" for m in conversation_history[-6:]])

        system_instruction = f"""You are the official AI Customer Support and Complaint Resolution Agent for LPG Smart ERP.
Your role: Answer customer questions, troubleshoot LPG cylinder refill/delivery/payment issues, and assist customers.

STRICT FACTUAL GROUNDING RULES:
1. ONLY state facts and numbers that appear in the customer's verified database records below.
2. NEVER hallucinate or invent booking IDs, payment amounts, delivery times, or ticket statuses.
3. If an answer cannot be determined from the records, clearly say so and offer human escalation.
4. Keep answers concise, empathetic, and professional (under 4 sentences).
5. At the very end of every troubleshooting proposal, you MUST include the exact question:
   "Has this resolved your issue?"

VERIFIED CUSTOMER RECORDS (GROUND TRUTH):
Customer Info: {grounding_data.get('customer')}
Recent Bookings: {grounding_data.get('recent_bookings')}
Recent Payments: {grounding_data.get('recent_payments')}
Support Tickets: {grounding_data.get('support_tickets')}
Active Delivery Confirmation: {grounding_data.get('active_pending_delivery_confirmation')}

RECENT CONVERSATION HISTORY:
{recent_dialogue}
"""
        full_content = f"{system_instruction}\n\nCustomer Query: {prompt}"

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=full_content
            )
            return response.text
        except Exception:
            return None

    @staticmethod
    def process_message(db: Session, current_user: User, request_data: ChatbotMessageRequest) -> ChatbotMessageResponse:
        message = (request_data.message or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if len(message) > 2000:
            raise HTTPException(status_code=400, detail="Message exceeds maximum limit of 2000 characters")

        session = ChatbotService.get_or_create_session(db, current_user, request_data.session_id)

        user_chat_msg = ChatMessage(
            session_id=session.session_id,
            sender_role="user",
            message=message,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user_chat_msg)
        db.commit()

        # 1. EMERGENCY SAFETY CHECK
        if ChatbotService.is_gas_leak_emergency(message):
            ticket = ChatbotService.escalate_chat_to_ticket(
                db=db,
                current_user=current_user,
                session=session,
                category="GAS_LEAK_EMERGENCY",
                summary=f"CRITICAL SAFETY: Customer reported suspected LPG leak or hazard: '{message[:120]}'",
                priority="CRITICAL",
                escalation_reason="Suspected LPG leak or safety emergency reported in chat"
            )
            assistant_reply = (
                f"{SAFETY_EMERGENCY_GUIDANCE}\n\n"
                f"Emergency Support Ticket #{ticket.ticket_number} has been logged with CRITICAL priority. "
                "Our emergency response coordinator has been alerted."
            )
            assistant_chat_msg = ChatMessage(
                session_id=session.session_id,
                sender_role="assistant",
                message=assistant_reply,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assistant_chat_msg)
            session.status = "ESCALATED"
            db.commit()

            return ChatbotMessageResponse(
                session_id=session.session_id,
                response=assistant_reply,
                assistant_message=assistant_reply,
                resolution_state="ESCALATED",
                escalation_state="ESCALATED",
                requires_confirmation=False,
                escalated=True,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                ticket_status=ticket.status.value,
                priority="CRITICAL",
                suggested_actions=["Call 1906 Emergency", "Evacuate Premises", "Turn off Regulator"],
                is_safety_emergency=True
            )

        # 2. RESOLUTION CONFIRMATION LOOP
        if session.status == "PROPOSED_SOLUTION":
            if ChatbotService.is_resolution_confirmation(message):
                session.status = "RESOLVED"
                session.unresolved_attempts = 0

                if session.associated_ticket_id:
                    ticket = db.query(SupportTicket).filter(SupportTicket.id == session.associated_ticket_id).first()
                    if ticket and ticket.status in [SupportTicketStatus.OPEN, SupportTicketStatus.AI_ASSISTED]:
                        ticket.status = SupportTicketStatus.RESOLVED
                        ticket.resolution_notes = "Customer confirmed resolution via AI chatbot."

                assistant_reply = (
                    "Thank you for confirming! I am glad your issue is resolved. "
                    "Feel free to reach out anytime if you need further help with your LPG service."
                )
                assistant_chat_msg = ChatMessage(
                    session_id=session.session_id,
                    sender_role="assistant",
                    message=assistant_reply,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(assistant_chat_msg)
                db.commit()

                return ChatbotMessageResponse(
                    session_id=session.session_id,
                    response=assistant_reply,
                    assistant_message=assistant_reply,
                    resolution_state="RESOLVED",
                    escalation_state="NONE",
                    requires_confirmation=False,
                    escalated=False,
                    ticket_id=session.associated_ticket_id,
                    ticket_number=None,
                    ticket_status=None,
                    priority="NORMAL",
                    suggested_actions=["Book Refill", "View Receipts", "Check Quota"],
                    is_safety_emergency=False
                )

            elif ChatbotService.is_resolution_rejection(message):
                ticket = ChatbotService.escalate_chat_to_ticket(
                    db=db,
                    current_user=current_user,
                    session=session,
                    category="UNRESOLVED_TROUBLESHOOTING",
                    summary=f"Automated troubleshooting failed. Customer reported: '{message[:120]}'",
                    priority="HIGH",
                    escalation_reason="Customer confirmed troubleshooting steps did not resolve the issue"
                )
                assistant_reply = (
                    f"I understand the suggested solution did not resolve your issue. "
                    f"I have escalated your case to our human support team under Ticket #{ticket.ticket_number}. "
                    "An admin or support agent will review your records and contact you."
                )
                assistant_chat_msg = ChatMessage(
                    session_id=session.session_id,
                    sender_role="assistant",
                    message=assistant_reply,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(assistant_chat_msg)
                db.commit()

                return ChatbotMessageResponse(
                    session_id=session.session_id,
                    response=assistant_reply,
                    assistant_message=assistant_reply,
                    resolution_state="ESCALATED",
                    escalation_state="ESCALATED",
                    requires_confirmation=False,
                    escalated=True,
                    ticket_id=ticket.id,
                    ticket_number=ticket.ticket_number,
                    ticket_status=ticket.status.value,
                    priority=ticket.priority,
                    suggested_actions=["View Ticket Status", "Wait for Support Agent"],
                    is_safety_emergency=False
                )

        # 3. EXPLICIT HUMAN AGENT REQUEST
        if ChatbotService.is_human_agent_requested(message):
            ticket = ChatbotService.escalate_chat_to_ticket(
                db=db,
                current_user=current_user,
                session=session,
                category="HUMAN_SUPPORT_REQUEST",
                summary=f"Customer requested human agent: '{message[:120]}'",
                priority="HIGH",
                escalation_reason="Customer explicitly requested a human support agent"
            )
            assistant_reply = (
                f"I am routing your request to our support team. "
                f"I have created Ticket #{ticket.ticket_number} for you. "
                "A support representative will review your inquiry and follow up shortly."
            )
            assistant_chat_msg = ChatMessage(
                session_id=session.session_id,
                sender_role="assistant",
                message=assistant_reply,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assistant_chat_msg)
            db.commit()

            return ChatbotMessageResponse(
                session_id=session.session_id,
                response=assistant_reply,
                assistant_message=assistant_reply,
                resolution_state="ESCALATED",
                escalation_state="ESCALATED",
                requires_confirmation=False,
                escalated=True,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                ticket_status=ticket.status.value,
                priority=ticket.priority,
                suggested_actions=["View Ticket Details"],
                is_safety_emergency=False
            )

        # 4. EXCEEDED UNRESOLVED ATTEMPTS ESCALATION
        session.unresolved_attempts = (session.unresolved_attempts or 0) + 1
        if session.unresolved_attempts >= settings.CHATBOT_MAX_UNRESOLVED_ATTEMPTS:
            ticket = ChatbotService.escalate_chat_to_ticket(
                db=db,
                current_user=current_user,
                session=session,
                category="MAX_ATTEMPTS_ESCALATION",
                summary=f"Issue unresolved after {session.unresolved_attempts} attempts. Query: '{message[:120]}'",
                priority="HIGH",
                escalation_reason=f"Exceeded max troubleshooting attempts ({settings.CHATBOT_MAX_UNRESOLVED_ATTEMPTS})"
            )
            assistant_reply = (
                f"We have completed multiple troubleshooting attempts without resolution. "
                f"To ensure you receive proper assistance, I have escalated this issue to our support team under Ticket #{ticket.ticket_number}. "
                "Our team will review your chat history and assist you directly."
            )
            assistant_chat_msg = ChatMessage(
                session_id=session.session_id,
                sender_role="assistant",
                message=assistant_reply,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assistant_chat_msg)
            db.commit()

            return ChatbotMessageResponse(
                session_id=session.session_id,
                response=assistant_reply,
                assistant_message=assistant_reply,
                resolution_state="ESCALATED",
                escalation_state="ESCALATED",
                requires_confirmation=False,
                escalated=True,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                ticket_status=ticket.status.value,
                priority=ticket.priority,
                suggested_actions=["View Ticket Status"],
                is_safety_emergency=False
            )

        # 5. GROUNDED AI QUERY RESOLUTION
        grounding_data = ChatbotService.build_grounding_context(db, current_user)
        history_msgs = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.session_id
        ).order_by(ChatMessage.id.asc()).limit(8).all()

        ai_reply = ChatbotService.call_gemini_chat(message, grounding_data, history_msgs)
        if not ai_reply:
            ai_reply = ChatbotService.generate_grounded_fallback_response(message, grounding_data)

        # Enforce "Has this resolved your issue?"
        if "Has this resolved your issue?" not in ai_reply and "has this resolved your issue" not in ai_reply.lower():
            ai_reply = ai_reply.rstrip() + "\n\nHas this resolved your issue?"

        session.status = "PROPOSED_SOLUTION"

        assistant_chat_msg = ChatMessage(
            session_id=session.session_id,
            sender_role="assistant",
            message=ai_reply,
            created_at=datetime.now(timezone.utc)
        )
        db.add(assistant_chat_msg)
        db.commit()

        return ChatbotMessageResponse(
            session_id=session.session_id,
            response=ai_reply,
            assistant_message=ai_reply,
            resolution_state="PROPOSED_SOLUTION",
            escalation_state="NONE",
            requires_confirmation=True,
            escalated=False,
            ticket_id=session.associated_ticket_id,
            ticket_number=None,
            ticket_status=None,
            priority="NORMAL",
            suggested_actions=["Yes, resolved", "No, still need help", "Connect to human agent"],
            is_safety_emergency=False
        )

    @staticmethod
    def get_session_history(db: Session, current_user: User, session_id: str, limit: int = 50) -> ChatSessionHistoryOut:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this chat session")

        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.session_id
        ).order_by(ChatMessage.id.asc()).limit(limit).all()

        ticket_number = None
        if session.associated_ticket_id:
            ticket = db.query(SupportTicket).filter(SupportTicket.id == session.associated_ticket_id).first()
            if ticket:
                ticket_number = ticket.ticket_number

        return ChatSessionHistoryOut(
            session_id=session.session_id,
            customer_id=session.customer_id,
            status=session.status,
            unresolved_attempts=session.unresolved_attempts,
            associated_ticket_id=session.associated_ticket_id,
            ticket_number=ticket_number,
            messages=[
                ChatMessageOut(
                    id=m.id,
                    sender_role=m.sender_role,
                    message=m.message,
                    metadata_json=m.metadata_json,
                    created_at=m.created_at
                )
                for m in messages
            ]
        )

    @staticmethod
    def manual_escalate_session(
        db: Session,
        current_user: User,
        session_id: str,
        reason: Optional[str] = "Customer requested manual escalation"
    ) -> ChatbotMessageResponse:
        session = ChatbotService.get_or_create_session(db, current_user, session_id)
        ticket = ChatbotService.escalate_chat_to_ticket(
            db=db,
            current_user=current_user,
            session=session,
            category="MANUAL_ESCALATION",
            summary=f"Manual customer escalation: {reason}",
            priority="HIGH",
            escalation_reason=reason or "Customer requested manual escalation"
        )
        assistant_reply = (
            f"Your chat session has been escalated to our human support team under Ticket #{ticket.ticket_number}. "
            "An agent will review your conversation history and contact you shortly."
        )
        assistant_chat_msg = ChatMessage(
            session_id=session.session_id,
            sender_role="assistant",
            message=assistant_reply,
            created_at=datetime.now(timezone.utc)
        )
        db.add(assistant_chat_msg)
        db.commit()

        return ChatbotMessageResponse(
            session_id=session.session_id,
            response=assistant_reply,
            assistant_message=assistant_reply,
            resolution_state="ESCALATED",
            escalation_state="ESCALATED",
            requires_confirmation=False,
            escalated=True,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            ticket_status=ticket.status.value,
            priority=ticket.priority,
            suggested_actions=["View Ticket Status"],
            is_safety_emergency=False
        )

class DeliveryBoyService:
    @staticmethod
    def get_assigned_deliveries(db: Session, current_user: User, skip: int = 0, limit: int = 50):
        return db.query(DeliveryAssignment).filter(
            DeliveryAssignment.delivery_boy_id == current_user.id
        ).order_by(DeliveryAssignment.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def record_delivery_outcome(db: Session, current_user: User, assignment_id: int, data: DeliveryOutcomeRequest):
        assignment = db.query(DeliveryAssignment).filter(
            DeliveryAssignment.id == assignment_id,
            DeliveryAssignment.delivery_boy_id == current_user.id
        ).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assigned delivery not found")

        booking = db.query(Booking).filter(Booking.id == assignment.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Associated booking not found")

        # Check if there is an active confirmation request for this assignment
        dcr = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.assignment_id == assignment.id
        ).order_by(DeliveryConfirmationRequest.id.desc()).first()

        if dcr:
            if dcr.status == DeliveryRequestStatus.REQUESTED:
                raise HTTPException(status_code=400, detail="Cannot record outcome: delivery confirmation request is awaiting customer approval")
            elif dcr.status == DeliveryRequestStatus.REJECTED:
                if data.outcome == DeliveryOutcome.DELIVERED_SUCCESS:
                    raise HTTPException(status_code=400, detail="Cannot complete delivery: request was rejected by customer")

        existing_execution = db.query(DeliveryExecution).filter(DeliveryExecution.assignment_id == assignment.id).first()
        if existing_execution:
            raise HTTPException(status_code=400, detail="Outcome already recorded for this assignment")

        tx_ref_to_link = dcr.transaction_reference if (dcr and dcr.transaction_reference) else None

        execution = DeliveryExecution(
            assignment_id=assignment.id,
            booking_id=booking.id,
            delivery_boy_id=current_user.id,
            outcome=data.outcome,
            outcome_timestamp=datetime.now(timezone.utc),
            offline_sync_id=data.offline_sync_id,
            synced_at=datetime.now(timezone.utc),
            empty_cylinder_returned_serial=data.empty_cylinder_returned_serial,
            customer_signature_data=data.customer_signature_data,
            failure_reason=data.failure_reason,
            transaction_reference=tx_ref_to_link
        )
        db.add(execution)
        db.flush()

        if dcr and dcr.status in (DeliveryRequestStatus.ACCEPTED, DeliveryRequestStatus.IN_PROGRESS):
            if data.outcome == DeliveryOutcome.DELIVERED_SUCCESS:
                dcr.status = DeliveryRequestStatus.DELIVERED
                dcr.updated_at = datetime.now(timezone.utc)
                if dcr.transaction:
                    dcr.transaction.status = "DELIVERED"
                    dcr.transaction.delivery_execution_id = execution.id
                    dcr.transaction.updated_at = datetime.now(timezone.utc)
            else:
                dcr.status = DeliveryRequestStatus.CANCELLED
                dcr.updated_at = datetime.now(timezone.utc)
                if dcr.transaction:
                    dcr.transaction.status = "CANCELLED"
                    dcr.transaction.delivery_execution_id = execution.id
                    dcr.transaction.updated_at = datetime.now(timezone.utc)

        if data.outcome == DeliveryOutcome.DELIVERED_SUCCESS:
            assignment.status = "DELIVERED"
            booking.status = BookingStatus.DELIVERED
            if assignment.cylinder_id:
                cylinder = db.query(CylinderInventory).filter(CylinderInventory.id == assignment.cylinder_id).first()
                if cylinder:
                    cylinder.status = CylinderStatus.DELIVERED_FULL
            if data.empty_cylinder_returned_serial:
                returned_cyl = db.query(CylinderInventory).filter(
                    CylinderInventory.serial_number == data.empty_cylinder_returned_serial
                ).first()
                if returned_cyl:
                    returned_cyl.status = CylinderStatus.RETURNED_EMPTY
        else:
            assignment.status = "FAILED"
            booking.status = BookingStatus.CANCELLED
            if assignment.cylinder_id:
                cylinder = db.query(CylinderInventory).filter(CylinderInventory.id == assignment.cylinder_id).first()
                if cylinder:
                    cylinder.status = CylinderStatus.IN_STOCK

        db.commit()
        db.refresh(execution)
        cache.delete("dashboard:overview")
        cache.delete_pattern("inventory:*")
        log_audit(db, current_user, "RECORD_OUTCOME", "DeliveryAssignment", str(assignment.id), f"Outcome: {data.outcome.value}")
        return execution

    @staticmethod
    def collect_payment(db: Session, current_user: User, assignment_id: int, data: PaymentCollectRequest):
        assignment = db.query(DeliveryAssignment).filter(
            DeliveryAssignment.id == assignment_id,
            DeliveryAssignment.delivery_boy_id == current_user.id
        ).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assigned delivery not found")

        booking = db.query(Booking).filter(Booking.id == assignment.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Associated booking not found")

        dcr = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.assignment_id == assignment.id
        ).order_by(DeliveryConfirmationRequest.id.desc()).first()

        payment = db.query(PaymentRecord).filter(PaymentRecord.booking_id == booking.id).first()

        tx_ref = data.transaction_reference
        if not tx_ref and payment and payment.transaction_reference:
            tx_ref = payment.transaction_reference
        elif not tx_ref and dcr and dcr.transaction_reference:
            tx_ref = dcr.transaction_reference
        elif not tx_ref:
            tx_ref = f"TXN-{uuid.uuid4().hex[:8].upper()}"

        if payment:
            payment.amount = data.amount
            payment.payment_method = data.payment_method
            payment.payment_status = PaymentStatus.COLLECTED
            payment.delivery_boy_id = current_user.id
            payment.transaction_reference = tx_ref
            payment.collected_at = datetime.now(timezone.utc)
        else:
            payment = PaymentRecord(
                booking_id=booking.id,
                customer_id=booking.customer_id,
                delivery_boy_id=current_user.id,
                amount=data.amount,
                payment_method=data.payment_method,
                payment_status=PaymentStatus.COLLECTED,
                transaction_reference=tx_ref,
                collected_at=datetime.now(timezone.utc)
            )
            db.add(payment)

        db.flush()
        if dcr and dcr.transaction:
            dcr.transaction.payment_record_id = payment.id

        db.commit()
        db.refresh(payment)
        cache.delete("dashboard:overview")
        cache.delete("reports:financial_summary")
        log_audit(db, current_user, "COLLECT_PAYMENT", "PaymentRecord", str(payment.id), f"Collected {data.amount} via {data.payment_method.value}")
        return payment

    @staticmethod
    def sync_offline(db: Session, current_user: User, data: OfflineSyncBatchRequest):
        synced_outcomes = 0
        synced_payments = 0
        errors = []

        for item in data.outcomes:
            if item.offline_sync_id:
                already_synced = db.query(DeliveryExecution).filter(
                    DeliveryExecution.offline_sync_id == item.offline_sync_id
                ).first()
                if already_synced:
                    continue

            assignment = db.query(DeliveryAssignment).filter(
                DeliveryAssignment.id == item.assignment_id,
                DeliveryAssignment.delivery_boy_id == current_user.id
            ).first()
            if not assignment:
                errors.append(f"Assignment {item.assignment_id} not found or not assigned to user")
                continue

            booking = db.query(Booking).filter(Booking.id == assignment.booking_id).first()
            execution = DeliveryExecution(
                assignment_id=assignment.id,
                booking_id=booking.id,
                delivery_boy_id=current_user.id,
                outcome=item.outcome,
                outcome_timestamp=item.outcome_timestamp,
                offline_sync_id=item.offline_sync_id,
                synced_at=datetime.now(timezone.utc),
                empty_cylinder_returned_serial=item.empty_cylinder_returned_serial,
                customer_signature_data=item.customer_signature_data,
                failure_reason=item.failure_reason
            )
            db.add(execution)

            if item.outcome == DeliveryOutcome.DELIVERED_SUCCESS:
                assignment.status = "DELIVERED"
                if booking:
                    booking.status = BookingStatus.DELIVERED
                if assignment.cylinder_id:
                    cyl = db.query(CylinderInventory).filter(CylinderInventory.id == assignment.cylinder_id).first()
                    if cyl:
                        cyl.status = CylinderStatus.DELIVERED_FULL
            else:
                assignment.status = "FAILED"
                if booking:
                    booking.status = BookingStatus.CANCELLED

            synced_outcomes += 1

        for item in data.payments:
            booking = db.query(Booking).filter(Booking.id == item.booking_id).first()
            if not booking:
                errors.append(f"Booking {item.booking_id} for payment not found")
                continue

            assignment = db.query(DeliveryAssignment).filter(
                DeliveryAssignment.booking_id == booking.id,
                DeliveryAssignment.delivery_boy_id == current_user.id
            ).first()
            if not assignment:
                errors.append(f"Booking {item.booking_id} was not assigned to current delivery boy")
                continue

            existing_payment = db.query(PaymentRecord).filter(PaymentRecord.booking_id == booking.id).first()
            tx_ref = item.transaction_reference or f"TXN-OFFLINE-{uuid.uuid4().hex[:6].upper()}"

            if existing_payment:
                existing_payment.amount = item.amount
                existing_payment.payment_method = item.payment_method
                existing_payment.payment_status = PaymentStatus.COLLECTED
                existing_payment.delivery_boy_id = current_user.id
                existing_payment.transaction_reference = tx_ref
                existing_payment.collected_at = item.collected_at
            else:
                payment = PaymentRecord(
                    booking_id=booking.id,
                    customer_id=booking.customer_id,
                    delivery_boy_id=current_user.id,
                    amount=item.amount,
                    payment_method=item.payment_method,
                    payment_status=PaymentStatus.COLLECTED,
                    transaction_reference=tx_ref,
                    collected_at=item.collected_at
                )
                db.add(payment)
            synced_payments += 1

        db.commit()
        cache.delete("dashboard:overview")
        cache.delete("reports:financial_summary")
        log_audit(db, current_user, "OFFLINE_SYNC", "BatchSync", f"{synced_outcomes}:{synced_payments}", f"Synced outcomes: {synced_outcomes}, payments: {synced_payments}")
        return OfflineSyncBatchResponse(
            synced_outcomes_count=synced_outcomes,
            synced_payments_count=synced_payments,
            errors=errors
        )

class AdminService:
    @staticmethod
    def create_user(db: Session, current_user: User, data: UserCreate):
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=data.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        if data.role == UserRole.DELIVERY_BOY:
            staff_profile = StaffProfile(
                user_id=new_user.id,
                employee_code=data.employee_code or f"EMP-{new_user.id:04d}",
                vehicle_number=data.vehicle_number or "NA",
                assigned_hub_zone=data.assigned_hub_zone or "Default Hub"
            )
            db.add(staff_profile)
            db.commit()

        cache.delete("dashboard:overview")
        log_audit(db, current_user, "CREATE", "User", str(new_user.id), f"Created user with role {data.role.value}")
        return new_user

    @staticmethod
    def get_users(db: Session, role: Optional[UserRole] = None, skip: int = 0, limit: int = 50):
        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        return query.order_by(User.id.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_user_status(db: Session, current_user: User, user_id: int, is_active: bool):
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        target.is_active = is_active
        db.commit()
        cache.delete("dashboard:overview")
        log_audit(db, current_user, "UPDATE_STATUS", "User", str(target.id), f"Set active status to {is_active}")
        return target

    @staticmethod
    def get_customers(db: Session, skip: int = 0, limit: int = 50):
        return db.query(CustomerProfile).offset(skip).limit(limit).all()

    @staticmethod
    def get_customer_by_id(db: Session, customer_id: int):
        customer = db.query(CustomerProfile).filter(CustomerProfile.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    @staticmethod
    def get_inventory(db: Session, skip: int = 0, limit: int = 100):
        return db.query(CylinderInventory).order_by(CylinderInventory.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_inventory(db: Session, current_user: User, data: CylinderInventoryCreate):
        existing = db.query(CylinderInventory).filter(CylinderInventory.serial_number == data.serial_number).first()
        if existing:
            raise HTTPException(status_code=400, detail="Cylinder serial number already exists")

        item = CylinderInventory(
            serial_number=data.serial_number,
            cylinder_type=data.cylinder_type,
            status=data.status,
            batch_code=data.batch_code
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        cache.delete("dashboard:overview")
        cache.delete_pattern("inventory:*")
        log_audit(db, current_user, "CREATE", "CylinderInventory", str(item.id), f"Added cylinder {item.serial_number}")
        return item

    @staticmethod
    def update_inventory(db: Session, current_user: User, cylinder_id: int, data: CylinderInventoryUpdate):
        item = db.query(CylinderInventory).filter(CylinderInventory.id == cylinder_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Cylinder not found")
        if data.status:
            item.status = data.status
        if data.batch_code:
            item.batch_code = data.batch_code
        db.commit()
        db.refresh(item)
        cache.delete("dashboard:overview")
        cache.delete_pattern("inventory:*")
        log_audit(db, current_user, "UPDATE", "CylinderInventory", str(item.id), f"Updated cylinder {item.serial_number}")
        return item

    @staticmethod
    def get_bookings(db: Session, skip: int = 0, limit: int = 50):
        return db.query(Booking).order_by(Booking.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def assign_booking(db: Session, current_user: User, booking_id: int, delivery_boy_id: int, cylinder_id: Optional[int] = None, notes: Optional[str] = None):
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        delivery_boy = db.query(User).filter(User.id == delivery_boy_id, User.role == UserRole.DELIVERY_BOY).first()
        if not delivery_boy:
            raise HTTPException(status_code=404, detail="Delivery boy not found")

        if cylinder_id:
            cylinder = db.query(CylinderInventory).filter(CylinderInventory.id == cylinder_id).first()
            if not cylinder:
                raise HTTPException(status_code=404, detail="Cylinder not found")
            if cylinder.status not in (CylinderStatus.IN_STOCK, CylinderStatus.RESERVED):
                raise HTTPException(status_code=400, detail="Cylinder is not in stock or reserved")
            cylinder.status = CylinderStatus.ASSIGNED

        assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.booking_id == booking.id).first()
        if assignment:
            assignment.delivery_boy_id = delivery_boy_id
            assignment.cylinder_id = cylinder_id
            assignment.notes = notes
            assignment.status = "ASSIGNED"
        else:
            assignment = DeliveryAssignment(
                booking_id=booking.id,
                delivery_boy_id=delivery_boy_id,
                cylinder_id=cylinder_id,
                notes=notes,
                status="ASSIGNED"
            )
            db.add(assignment)

        booking.status = BookingStatus.ASSIGNED
        db.commit()
        db.refresh(assignment)
        cache.delete("dashboard:overview")
        log_audit(db, current_user, "ASSIGN", "DeliveryAssignment", str(assignment.id), f"Assigned booking {booking.booking_number} to delivery boy {delivery_boy.full_name}")
        return assignment

    @staticmethod
    def apply_financial_correction(db: Session, current_user: User, data: FinancialCorrectionRequest):
        payment = db.query(PaymentRecord).filter(PaymentRecord.id == data.payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        original_amount = payment.amount
        correction = FinancialCorrection(
            payment_id=payment.id,
            booking_id=payment.booking_id,
            corrected_by_user_id=current_user.id,
            original_amount=original_amount,
            corrected_amount=data.corrected_amount,
            reason=data.reason,
            audit_notes=data.audit_notes,
            created_at=datetime.now(timezone.utc)
        )
        payment.amount = data.corrected_amount
        db.add(correction)
        db.commit()
        db.refresh(correction)
        cache.delete("dashboard:overview")
        cache.delete("reports:financial_summary")
        log_audit(db, current_user, "FINANCIAL_CORRECTION", "PaymentRecord", str(payment.id), f"Amount changed from {original_amount} to {data.corrected_amount}. Reason: {data.reason}")
        return correction

    @staticmethod
    def get_dashboard_overview(db: Session):
        cache_key = "dashboard:overview"
        cached = cache.get(cache_key)
        if cached:
            return cached

        total_customers = db.query(CustomerProfile).count()
        total_staff = db.query(StaffProfile).count()
        total_bookings = db.query(Booking).count()
        pending_bookings = db.query(Booking).filter(Booking.status == BookingStatus.PENDING).count()
        in_stock_cylinders = db.query(CylinderInventory).filter(CylinderInventory.status == CylinderStatus.IN_STOCK).count()

        overview = {
            "total_customers": total_customers,
            "total_delivery_staff": total_staff,
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "in_stock_cylinders": in_stock_cylinders
        }
        cache.set(cache_key, overview, ttl_seconds=120)
        return overview

class AuditorService:
    @staticmethod
    def get_reconciliation_reports(db: Session, skip: int = 0, limit: int = 50):
        bookings = db.query(Booking).order_by(Booking.id.desc()).offset(skip).limit(limit).all()
        report = []

        for b in bookings:
            assignment = b.assignment
            execution = assignment.execution if assignment else None
            payment = b.payment

            delivery_status = assignment.status if assignment else "NOT_ASSIGNED"
            delivery_outcome = execution.outcome.value if execution else None
            payment_status = payment.payment_status.value if payment else "NOT_PAID"
            collected_amount = payment.amount if payment and payment.payment_status == PaymentStatus.COLLECTED else 0.0

            is_reconciled = False
            notes = ""

            if b.status == BookingStatus.DELIVERED:
                if payment and payment.payment_status == PaymentStatus.COLLECTED and abs(collected_amount - b.net_payable) < 0.01:
                    is_reconciled = True
                    notes = "Fully reconciled: delivered and paid"
                else:
                    notes = f"Discrepancy: delivered but expected {b.net_payable} and collected {collected_amount}"
            elif b.status == BookingStatus.CANCELLED:
                if collected_amount > 0:
                    notes = "Discrepancy: cancelled booking has collected funds"
                else:
                    is_reconciled = True
                    notes = "Reconciled: cancelled without payment collected"
            else:
                is_reconciled = True
                notes = "In progress"

            report.append({
                "booking_id": b.id,
                "booking_number": b.booking_number,
                "customer_id": b.customer_id,
                "booking_status": b.status.value,
                "delivery_status": delivery_status,
                "delivery_outcome": delivery_outcome,
                "payment_status": payment_status,
                "expected_amount": b.net_payable,
                "collected_amount": collected_amount,
                "is_reconciled": is_reconciled,
                "notes": notes
            })
        return report

    @staticmethod
    def get_discrepancy_evidence(db: Session, limit: int = 50):
        discrepancies = []

        unpaid_deliveries = db.query(Booking).filter(
            Booking.status == BookingStatus.DELIVERED
        ).limit(limit).all()
        for b in unpaid_deliveries:
            payment = b.payment
            if not payment or payment.payment_status != PaymentStatus.COLLECTED:
                discrepancies.append({
                    "issue_type": "DELIVERY_WITHOUT_PAYMENT",
                    "booking_id": b.id,
                    "customer_id": b.customer_id,
                    "delivery_boy_id": b.assignment.delivery_boy_id if b.assignment else None,
                    "details": f"Booking {b.booking_number} marked DELIVERED but no payment recorded",
                    "severity": "HIGH"
                })
            elif abs(payment.amount - b.net_payable) > 0.01:
                discrepancies.append({
                    "issue_type": "PAYMENT_AMOUNT_MISMATCH",
                    "booking_id": b.id,
                    "customer_id": b.customer_id,
                    "delivery_boy_id": b.assignment.delivery_boy_id if b.assignment else None,
                    "details": f"Booking {b.booking_number} expected {b.net_payable} but collected {payment.amount}",
                    "severity": "HIGH"
                })

        cancelled_with_money = db.query(Booking).filter(
            Booking.status == BookingStatus.CANCELLED
        ).limit(limit).all()
        for b in cancelled_with_money:
            if b.payment and b.payment.payment_status == PaymentStatus.COLLECTED:
                discrepancies.append({
                    "issue_type": "CANCELLED_BOOKING_WITH_PAYMENT",
                    "booking_id": b.id,
                    "customer_id": b.customer_id,
                    "delivery_boy_id": b.assignment.delivery_boy_id if b.assignment else None,
                    "details": f"Cancelled booking {b.booking_number} holds collected payment of {b.payment.amount}",
                    "severity": "CRITICAL"
                })

        failed_executions = db.query(DeliveryExecution).filter(
            DeliveryExecution.outcome != DeliveryOutcome.DELIVERED_SUCCESS,
            (DeliveryExecution.failure_reason == None) | (DeliveryExecution.failure_reason == "")
        ).limit(limit).all()
        for fe in failed_executions:
            discrepancies.append({
                "issue_type": "UNDOCUMENTED_DELIVERY_FAILURE",
                "booking_id": fe.booking_id,
                "customer_id": None,
                "delivery_boy_id": fe.delivery_boy_id,
                "details": f"Delivery failure on assignment {fe.assignment_id} missing documented reason",
                "severity": "MEDIUM"
            })

        quota_exceeded_profiles = db.query(CustomerProfile).filter(
            CustomerProfile.quota_used_this_year > CustomerProfile.cylinder_quota_limit
        ).limit(limit).all()
        for cp in quota_exceeded_profiles:
            discrepancies.append({
                "issue_type": "QUOTA_EXCEEDED",
                "booking_id": None,
                "customer_id": cp.user_id,
                "delivery_boy_id": None,
                "details": f"Consumer {cp.consumer_number} used {cp.quota_used_this_year} beyond limit of {cp.cylinder_quota_limit}",
                "severity": "MEDIUM"
            })

        return discrepancies[:limit]

    @staticmethod
    def get_financial_summaries(db: Session):
        cache_key = "reports:financial_summary"
        cached = cache.get(cache_key)
        if cached:
            return cached

        total_bookings = db.query(Booking).count()
        total_sales_value = db.query(func.coalesce(func.sum(Booking.net_payable), 0.0)).scalar()

        collected_records = db.query(PaymentRecord).filter(PaymentRecord.payment_status == PaymentStatus.COLLECTED).all()
        total_collected = sum(p.amount for p in collected_records)
        total_pending = max(0.0, float(total_sales_value) - total_collected)

        method_breakdown = {
            PaymentMethod.CASH.value: 0.0,
            PaymentMethod.UPI.value: 0.0,
            PaymentMethod.CARD.value: 0.0,
            PaymentMethod.ONLINE.value: 0.0
        }
        for p in collected_records:
            method_breakdown[p.payment_method.value] += p.amount

        corrections = db.query(FinancialCorrection).all()
        total_corrections_count = len(corrections)
        net_variance = sum(c.corrected_amount - c.original_amount for c in corrections)

        summary = {
            "total_bookings": total_bookings,
            "total_sales_value": float(total_sales_value),
            "total_collected_amount": float(total_collected),
            "total_pending_amount": float(total_pending),
            "collections_by_method": method_breakdown,
            "total_corrections_count": total_corrections_count,
            "net_correction_variance": float(net_variance)
        }
        cache.set(cache_key, summary, ttl_seconds=180)
        return summary

    @staticmethod
    def get_financial_corrections(db: Session, skip: int = 0, limit: int = 50):
        return db.query(FinancialCorrection).order_by(FinancialCorrection.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_audit_logs(db: Session, skip: int = 0, limit: int = 50):
        return db.query(AuditLog).order_by(AuditLog.id.desc()).offset(skip).limit(limit).all()

def generate_transaction_reference() -> str:
    # 128-bit cryptographically secure random identifier (32 hex characters)
    # References, rather than encodes, customer, booking, delivery and payment data
    return f"TXN-{secrets.token_hex(16).upper()}"

def generate_request_id() -> str:
    # 64-bit cryptographically secure random identifier
    return f"REQ-{secrets.token_hex(8).upper()}"

def to_confirmation_out(req: DeliveryConfirmationRequest) -> DeliveryConfirmationRequestOut:
    return DeliveryConfirmationRequestOut(
        id=req.id,
        request_id=req.request_id,
        booking_id=req.booking_id,
        booking_number=req.booking.booking_number if req.booking else None,
        customer_id=req.customer_id,
        customer_name=req.customer.full_name if req.customer else None,
        customer_phone=req.customer.phone if req.customer else None,
        customer_address=req.customer.customer_profile.address if (req.customer and req.customer.customer_profile) else None,
        delivery_partner_id=req.delivery_partner_id,
        delivery_partner_name=req.delivery_partner.full_name if req.delivery_partner else None,
        delivery_partner_phone=req.delivery_partner.phone if req.delivery_partner else None,
        assignment_id=req.assignment_id,
        amount_due=req.amount_due,
        cylinder_serial=req.cylinder_serial,
        cylinder_type=req.cylinder_type,
        status=req.status.value if hasattr(req.status, "value") else str(req.status),
        rejection_reason=req.rejection_reason,
        notes=req.notes,
        transaction_reference=req.transaction_reference,
        created_at=req.created_at,
        updated_at=req.updated_at
    )

def to_transaction_out(tx: DeliveryTransaction) -> DeliveryTransactionOut:
    return DeliveryTransactionOut(
        id=tx.id,
        transaction_reference=tx.transaction_reference,
        confirmation_request_id=tx.confirmation_request_id,
        request_id=tx.confirmation_request.request_id if tx.confirmation_request else None,
        booking_id=tx.booking_id,
        booking_number=tx.booking.booking_number if tx.booking else None,
        customer_id=tx.customer_id,
        customer_name=tx.customer.full_name if tx.customer else None,
        delivery_partner_id=tx.delivery_partner_id,
        delivery_partner_name=tx.delivery_partner.full_name if tx.delivery_partner else None,
        assignment_id=tx.assignment_id,
        delivery_execution_id=tx.delivery_execution_id,
        payment_record_id=tx.payment_record_id,
        amount=tx.amount,
        status=tx.status,
        created_at=tx.created_at,
        updated_at=tx.updated_at
    )

class DeliveryConfirmationService:
    @staticmethod
    def create_confirmation_request(
        db: Session,
        current_user: User,
        assignment_id: Optional[int] = None,
        data: Optional[DeliveryConfirmationCreate] = None,
        booking_id: Optional[int] = None
    ) -> DeliveryConfirmationRequestOut:
        target_assignment_id = assignment_id or (data.assignment_id if data else None)
        target_booking_id = booking_id or (data.booking_id if data else None)

        query = db.query(DeliveryAssignment).filter(DeliveryAssignment.delivery_boy_id == current_user.id)
        if target_assignment_id:
            assignment = query.filter(DeliveryAssignment.id == target_assignment_id).first()
        elif target_booking_id:
            assignment = query.filter(DeliveryAssignment.booking_id == target_booking_id).first()
        else:
            raise HTTPException(status_code=400, detail="Either assignment_id or booking_id must be provided")

        if not assignment:
            raise HTTPException(status_code=404, detail="Assigned delivery not found for this delivery partner")

        booking = db.query(Booking).filter(Booking.id == assignment.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Associated booking not found")

        if assignment.status in ("DELIVERED", "FAILED") or booking.status in (BookingStatus.DELIVERED, BookingStatus.CANCELLED):
            raise HTTPException(status_code=400, detail="Cannot request delivery confirmation for a completed or cancelled booking")

        existing = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.assignment_id == assignment.id
        ).order_by(DeliveryConfirmationRequest.id.desc()).first()

        if existing:
            if existing.status == DeliveryRequestStatus.REQUESTED:
                return to_confirmation_out(existing)
            elif existing.status in (DeliveryRequestStatus.ACCEPTED, DeliveryRequestStatus.IN_PROGRESS):
                return to_confirmation_out(existing)
            elif existing.status == DeliveryRequestStatus.DELIVERED:
                raise HTTPException(status_code=400, detail="Delivery has already been confirmed and completed")

        req_id = generate_request_id()
        while db.query(DeliveryConfirmationRequest).filter(DeliveryConfirmationRequest.request_id == req_id).first() is not None:
            req_id = generate_request_id()

        serial = (data.cylinder_serial if data and data.cylinder_serial else None)
        if not serial and assignment.cylinder:
            serial = assignment.cylinder.serial_number

        notes = (data.notes if data and data.notes else None)

        request = DeliveryConfirmationRequest(
            request_id=req_id,
            booking_id=booking.id,
            customer_id=booking.customer_id,
            delivery_partner_id=current_user.id,
            assignment_id=assignment.id,
            amount_due=booking.net_payable,
            cylinder_serial=serial,
            cylinder_type=booking.cylinder_type,
            status=DeliveryRequestStatus.REQUESTED,
            notes=notes,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        if assignment.status == "ASSIGNED":
            assignment.status = "OUT_FOR_DELIVERY"
        if booking.status == BookingStatus.ASSIGNED:
            booking.status = BookingStatus.OUT_FOR_DELIVERY

        db.add(request)
        db.commit()
        db.refresh(request)
        log_audit(db, current_user, "CREATE_DELIVERY_REQUEST", "DeliveryConfirmationRequest", str(request.id), f"Created delivery confirmation request {request.request_id} for booking {booking.booking_number}")
        return to_confirmation_out(request)

    @staticmethod
    def list_customer_pending_requests(db: Session, current_user: User, skip: int = 0, limit: int = 50) -> List[DeliveryConfirmationRequestOut]:
        requests = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.customer_id == current_user.id,
            DeliveryConfirmationRequest.status == DeliveryRequestStatus.REQUESTED
        ).order_by(DeliveryConfirmationRequest.id.desc()).offset(skip).limit(limit).all()
        return [to_confirmation_out(r) for r in requests]

    @staticmethod
    def list_customer_requests(db: Session, current_user: User, status_filter: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[DeliveryConfirmationRequestOut]:
        query = db.query(DeliveryConfirmationRequest).filter(DeliveryConfirmationRequest.customer_id == current_user.id)
        if status_filter:
            query = query.filter(DeliveryConfirmationRequest.status == status_filter)
        requests = query.order_by(DeliveryConfirmationRequest.id.desc()).offset(skip).limit(limit).all()
        return [to_confirmation_out(r) for r in requests]

    @staticmethod
    def get_customer_request(db: Session, current_user: User, request_id: str) -> DeliveryConfirmationRequestOut:
        query = db.query(DeliveryConfirmationRequest)
        if request_id.isdigit():
            req = query.filter((DeliveryConfirmationRequest.id == int(request_id)) | (DeliveryConfirmationRequest.request_id == request_id)).first()
        else:
            req = query.filter(DeliveryConfirmationRequest.request_id == request_id).first()

        if not req:
            raise HTTPException(status_code=404, detail="Delivery confirmation request not found")
        if req.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: this request belongs to another customer")
        return to_confirmation_out(req)

    @staticmethod
    def accept_delivery_request(db: Session, current_user: User, request_id: str) -> DeliveryConfirmationRequestOut:
        query = db.query(DeliveryConfirmationRequest)
        if request_id.isdigit():
            req = query.filter((DeliveryConfirmationRequest.id == int(request_id)) | (DeliveryConfirmationRequest.request_id == request_id)).first()
        else:
            req = query.filter(DeliveryConfirmationRequest.request_id == request_id).first()

        if not req:
            raise HTTPException(status_code=404, detail="Delivery confirmation request not found")

        # Enforce customer ownership
        if req.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: this request belongs to another customer")

        # State transition handling
        if req.status == DeliveryRequestStatus.ACCEPTED:
            return to_confirmation_out(req)

        if req.status == DeliveryRequestStatus.REJECTED:
            raise HTTPException(status_code=400, detail="Cannot accept a delivery request that was previously rejected")

        if req.status in (DeliveryRequestStatus.DELIVERED, DeliveryRequestStatus.CANCELLED):
            raise HTTPException(status_code=400, detail=f"Invalid state transition: request is already {req.status.value}")

        if req.status != DeliveryRequestStatus.REQUESTED:
            raise HTTPException(status_code=400, detail=f"Invalid state transition from {req.status.value} to ACCEPTED")

        # Check if transaction already exists for this booking to avoid duplicate transactions
        existing_tx = db.query(DeliveryTransaction).filter(
            DeliveryTransaction.booking_id == req.booking_id
        ).first()

        if existing_tx:
            tx_ref = existing_tx.transaction_reference
            tx = existing_tx
            tx.confirmation_request_id = req.id
            tx.status = "ACCEPTED"
            tx.updated_at = datetime.now(timezone.utc)
        else:
            tx_ref = generate_transaction_reference()
            while db.query(DeliveryTransaction).filter(DeliveryTransaction.transaction_reference == tx_ref).first() is not None:
                tx_ref = generate_transaction_reference()

            tx = DeliveryTransaction(
                transaction_reference=tx_ref,
                confirmation_request_id=req.id,
                booking_id=req.booking_id,
                customer_id=req.customer_id,
                delivery_partner_id=req.delivery_partner_id,
                assignment_id=req.assignment_id,
                amount=req.amount_due,
                status="ACCEPTED",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(tx)
            db.flush()

        req.transaction_reference = tx_ref
        req.status = DeliveryRequestStatus.ACCEPTED
        req.updated_at = datetime.now(timezone.utc)

        # Link to PaymentRecord (ensures payment is PENDING, not settled)
        payment = db.query(PaymentRecord).filter(PaymentRecord.booking_id == req.booking_id).first()
        if payment:
            if not payment.transaction_reference:
                payment.transaction_reference = tx_ref
            tx.payment_record_id = payment.id
        else:
            payment = PaymentRecord(
                booking_id=req.booking_id,
                customer_id=req.customer_id,
                delivery_boy_id=req.delivery_partner_id,
                amount=req.amount_due,
                payment_method=PaymentMethod.CASH,
                payment_status=PaymentStatus.PENDING,
                transaction_reference=tx_ref,
                created_at=datetime.now(timezone.utc)
            )
            db.add(payment)
            db.flush()
            tx.payment_record_id = payment.id

        assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.id == req.assignment_id).first()
        if assignment and assignment.status not in ("DELIVERED", "FAILED"):
            assignment.status = "ACCEPTED"

        db.commit()
        db.refresh(req)
        log_audit(db, current_user, "ACCEPT_DELIVERY_REQUEST", "DeliveryConfirmationRequest", str(req.id), f"Customer approved. Shared Transaction Reference: {tx_ref}")
        return to_confirmation_out(req)

    @staticmethod
    def reject_delivery_request(db: Session, current_user: User, request_id: str, data: Optional[DeliveryRejectRequest] = None) -> DeliveryConfirmationRequestOut:
        query = db.query(DeliveryConfirmationRequest)
        if request_id.isdigit():
            req = query.filter((DeliveryConfirmationRequest.id == int(request_id)) | (DeliveryConfirmationRequest.request_id == request_id)).first()
        else:
            req = query.filter(DeliveryConfirmationRequest.request_id == request_id).first()

        if not req:
            raise HTTPException(status_code=404, detail="Delivery confirmation request not found")

        # Enforce customer ownership
        if req.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: this request belongs to another customer")

        if req.status == DeliveryRequestStatus.REJECTED:
            return to_confirmation_out(req)

        if req.status in (DeliveryRequestStatus.ACCEPTED, DeliveryRequestStatus.IN_PROGRESS, DeliveryRequestStatus.DELIVERED):
            raise HTTPException(status_code=400, detail=f"Cannot reject a request that is already {req.status.value}")

        req.status = DeliveryRequestStatus.REJECTED
        req.rejection_reason = data.rejection_reason if data and data.rejection_reason else "Customer rejected delivery"
        req.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(req)
        log_audit(db, current_user, "REJECT_DELIVERY_REQUEST", "DeliveryConfirmationRequest", str(req.id), f"Customer rejected: {req.rejection_reason}")
        return to_confirmation_out(req)

    @staticmethod
    def mark_in_progress(db: Session, current_user: User, request_id: str) -> DeliveryConfirmationRequestOut:
        query = db.query(DeliveryConfirmationRequest)
        if request_id.isdigit():
            req = query.filter((DeliveryConfirmationRequest.id == int(request_id)) | (DeliveryConfirmationRequest.request_id == request_id)).first()
        else:
            req = query.filter(DeliveryConfirmationRequest.request_id == request_id).first()

        if not req:
            raise HTTPException(status_code=404, detail="Delivery confirmation request not found")

        if req.delivery_partner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: request assigned to another delivery partner")

        if req.status == DeliveryRequestStatus.IN_PROGRESS:
            return to_confirmation_out(req)

        if req.status != DeliveryRequestStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail=f"Cannot mark IN_PROGRESS from status {req.status.value}. Request must be ACCEPTED first.")

        req.status = DeliveryRequestStatus.IN_PROGRESS
        req.updated_at = datetime.now(timezone.utc)
        if req.transaction:
            req.transaction.status = "IN_PROGRESS"
            req.transaction.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(req)
        log_audit(db, current_user, "MARK_IN_PROGRESS", "DeliveryConfirmationRequest", str(req.id), "Delivery transitioned to IN_PROGRESS")
        return to_confirmation_out(req)

    @staticmethod
    def get_partner_request_status(db: Session, current_user: User, assignment_id: int) -> DeliveryConfirmationRequestOut:
        assignment = db.query(DeliveryAssignment).filter(
            DeliveryAssignment.id == assignment_id,
            DeliveryAssignment.delivery_boy_id == current_user.id
        ).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assigned delivery not found for this delivery partner")

        req = db.query(DeliveryConfirmationRequest).filter(
            DeliveryConfirmationRequest.assignment_id == assignment.id
        ).order_by(DeliveryConfirmationRequest.id.desc()).first()

        if not req:
            raise HTTPException(status_code=404, detail="No delivery confirmation request found for this assignment")
        return to_confirmation_out(req)

    @staticmethod
    def get_partner_request(db: Session, current_user: User, request_id: str) -> DeliveryConfirmationRequestOut:
        query = db.query(DeliveryConfirmationRequest)
        if request_id.isdigit():
            req = query.filter((DeliveryConfirmationRequest.id == int(request_id)) | (DeliveryConfirmationRequest.request_id == request_id)).first()
        else:
            req = query.filter(DeliveryConfirmationRequest.request_id == request_id).first()

        if not req:
            raise HTTPException(status_code=404, detail="Delivery confirmation request not found")
        if req.delivery_partner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: request assigned to another delivery partner")
        return to_confirmation_out(req)

    @staticmethod
    def get_transaction_by_reference(db: Session, current_user: User, transaction_reference: str) -> DeliveryTransactionOut:
        tx = db.query(DeliveryTransaction).filter(
            DeliveryTransaction.transaction_reference == transaction_reference
        ).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Role-based authorization: customer or delivery partner involved in the transaction
        if current_user.role == UserRole.CUSTOMER and tx.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: customer does not own this transaction")
        elif current_user.role == UserRole.DELIVERY_BOY and tx.delivery_partner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access: delivery partner is not assigned to this transaction")

        return to_transaction_out(tx)

