from typing import List, Optional
from fastapi import APIRouter, Depends, status, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_customer
from app.schemas import (
    CustomerProfileOut, CustomerProfileUpdate,
    BookingCreate, BookingOut,
    DeliveryAssignmentOut, PaymentRecordOut,
    SupportTicketOut, SupportTicketCreate, SupportTicketEscalate,
    DeliveryConfirmationRequestOut, DeliveryRejectRequest, DeliveryTransactionOut
)
from app.services import CustomerService, SupportTicketService, DeliveryConfirmationService

router = APIRouter(prefix="/api/v1/customer", tags=["Customer App"])

@router.get("/profile", response_model=CustomerProfileOut)
def get_customer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_profile(db, current_user)

@router.put("/profile", response_model=CustomerProfileOut)
def update_customer_profile(
    payload: CustomerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.update_profile(db, current_user, payload)

@router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_cylinder_booking(
    payload: BookingCreate,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    if x_idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = x_idempotency_key
    return CustomerService.create_booking(db, current_user, payload)

@router.get("/bookings", response_model=List[BookingOut])
def list_customer_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_bookings(db, current_user, skip=skip, limit=limit)

@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_customer_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_booking_by_id(db, current_user, booking_id)

@router.get("/deliveries", response_model=List[DeliveryAssignmentOut])
def list_customer_deliveries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_deliveries(db, current_user, skip=skip, limit=limit)

@router.get("/payments", response_model=List[PaymentRecordOut])
def list_customer_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_payments(db, current_user, skip=skip, limit=limit)

@router.post("/support/tickets", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED)
@router.post("/tickets", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED)
def raise_support_ticket(
    payload: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return SupportTicketService.create_ticket(db, current_user, payload)

@router.get("/support/tickets", response_model=List[SupportTicketOut])
@router.get("/tickets", response_model=List[SupportTicketOut])
def get_support_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return SupportTicketService.get_tickets(db, current_user, skip=skip, limit=limit)

@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketOut)
@router.get("/tickets/{ticket_id}", response_model=SupportTicketOut)
def get_support_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return SupportTicketService.get_ticket_by_id(db, current_user, ticket_id)

@router.post("/support/tickets/{ticket_id}/escalate", response_model=SupportTicketOut)
@router.post("/tickets/{ticket_id}/escalate", response_model=SupportTicketOut)
def escalate_support_ticket(
    ticket_id: int,
    payload: SupportTicketEscalate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return SupportTicketService.escalate_ticket(db, current_user, ticket_id, payload)

@router.get("/delivery-requests/pending", response_model=List[DeliveryConfirmationRequestOut])
def list_pending_delivery_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.list_customer_pending_requests(
        db, current_user, skip=skip, limit=limit
    )

@router.get("/delivery-requests", response_model=List[DeliveryConfirmationRequestOut])
def list_customer_delivery_requests(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.list_customer_requests(
        db, current_user, status_filter=status, skip=skip, limit=limit
    )

@router.get("/delivery-requests/{request_id}", response_model=DeliveryConfirmationRequestOut)
def get_customer_delivery_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.get_customer_request(
        db, current_user, request_id=request_id
    )

@router.post("/delivery-requests/{request_id}/accept", response_model=DeliveryConfirmationRequestOut)
def accept_customer_delivery_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.accept_delivery_request(
        db, current_user, request_id=request_id
    )

@router.post("/delivery-requests/{request_id}/reject", response_model=DeliveryConfirmationRequestOut)
def reject_customer_delivery_request(
    request_id: str,
    payload: Optional[DeliveryRejectRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.reject_delivery_request(
        db, current_user, request_id=request_id, data=payload
    )

@router.get("/transactions/{transaction_reference}", response_model=DeliveryTransactionOut)
def get_customer_delivery_transaction(
    transaction_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return DeliveryConfirmationService.get_transaction_by_reference(
        db, current_user, transaction_reference=transaction_reference
    )

