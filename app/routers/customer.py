from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_customer
from app.schemas import (
    CustomerProfileOut, CustomerProfileUpdate,
    BookingCreate, BookingOut,
    DeliveryAssignmentOut, PaymentRecordOut
)
from app.services import CustomerService

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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.create_booking(db, current_user, payload)

@router.get("/bookings", response_model=List[BookingOut])
def list_customer_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_bookings(db, current_user)

@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_customer_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_booking_by_id(db, current_user, booking_id)

@router.get("/deliveries", response_model=List[DeliveryAssignmentOut])
def list_customer_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_deliveries(db, current_user)

@router.get("/payments", response_model=List[PaymentRecordOut])
def list_customer_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return CustomerService.get_payments(db, current_user)
