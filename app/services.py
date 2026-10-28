import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    User, UserRole, CustomerProfile, StaffProfile, CylinderInventory,
    Booking, BookingStatus, DeliveryAssignment, DeliveryExecution, DeliveryOutcome,
    PaymentRecord, PaymentStatus, PaymentMethod, CylinderStatus,
    FinancialCorrection, AuditLog, SupportTicket, SupportTicketStatus, SupportMessage
)
from app.schemas import (
    BookingCreate, DeliveryOutcomeRequest, PaymentCollectRequest,
    OfflineSyncBatchRequest, OfflineSyncBatchResponse,
    FinancialCorrectionRequest, CylinderInventoryCreate, CylinderInventoryUpdate,
    UserCreate, CustomerProfileUpdate, SupportTicketCreate, SupportTicketEscalate
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
import google.generativeai as genai
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "MOCK_KEY"))

class SupportTicketService:
    @staticmethod
    def create_ticket(db: Session, current_user: User, data: SupportTicketCreate):
        ticket_number = f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        ai_response_text = None
        if os.environ.get("GEMINI_API_KEY"):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = f"""
                You are a helpful customer support assistant for an LPG delivery service in India.
                The customer has raised the following issue:
                Category: {data.category}
                Description: {data.description}
                Transaction ID: {data.transaction_id or 'None provided'}
                Language Preference: {data.language}

                Provide a short, empathetic explanation of what might have happened and clear next steps.
                Do not make promises about refunds or specific delivery times.
                Respond ONLY in {data.language}. If {data.language} is Kannada, use proper Kannada script.
                Keep it under 3 sentences.
                """
                response = model.generate_content(prompt)
                ai_response_text = response.text
            except Exception as e:
                ai_response_text = f"We are currently experiencing high volume, but your issue has been recorded. (System Error: {e})"
        else:
             ai_response_text = "Thank you for reaching out. We have received your issue and our team will look into it shortly."

        ticket = SupportTicket(
            ticket_number=ticket_number,
            customer_id=current_user.id,
            transaction_id=data.transaction_id,
            category=data.category,
            description=data.description,
            language=data.language,
            status=SupportTicketStatus.AI_ASSISTED if ai_response_text else SupportTicketStatus.OPEN,
            ai_response=ai_response_text
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        log_audit(db, current_user, "CREATE_TICKET", "SupportTicket", str(ticket.id), f"Created ticket {ticket_number}")
        return ticket

    @staticmethod
    def get_tickets(db: Session, current_user: User):
        return db.query(SupportTicket).filter(SupportTicket.customer_id == current_user.id).order_by(SupportTicket.id.desc()).all()

    @staticmethod
    def escalate_ticket(db: Session, current_user: User, ticket_id: int, data: SupportTicketEscalate):
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id, SupportTicket.customer_id == current_user.id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        ticket.status = SupportTicketStatus.WAITING_FOR_STAFF
        ticket.escalation_reason = data.escalation_reason
        db.commit()
        db.refresh(ticket)
        log_audit(db, current_user, "ESCALATE_TICKET", "SupportTicket", str(ticket.id), "Escalated to human staff")
        return ticket

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

        existing_execution = db.query(DeliveryExecution).filter(DeliveryExecution.assignment_id == assignment.id).first()
        if existing_execution:
            raise HTTPException(status_code=400, detail="Outcome already recorded for this assignment")

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
            failure_reason=data.failure_reason
        )
        db.add(execution)

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

        payment = db.query(PaymentRecord).filter(PaymentRecord.booking_id == booking.id).first()
        tx_ref = data.transaction_reference or f"TXN-{uuid.uuid4().hex[:8].upper()}"

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
