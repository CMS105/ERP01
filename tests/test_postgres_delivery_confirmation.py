import pytest
import psycopg
from sqlalchemy import text
from app.config import settings
from app.database import engine, SessionLocal
from app.models import (
    User, UserRole, CustomerProfile, StaffProfile, Booking, BookingStatus,
    DeliveryAssignment, DeliveryConfirmationRequest, DeliveryTransaction,
    PaymentRecord, PaymentStatus
)
from app.services import DeliveryConfirmationService
from app.schemas import DeliveryConfirmationCreate

def test_postgresql_direct_delivery_confirmation_persistence():
    """
    Verifies actual persistence and constraints directly in PostgreSQL 18 `lpg_erp`.
    Ensures:
      - DeliveryConfirmationRequest is written to PostgreSQL table
      - Unique CSPRNG transaction reference is created on customer accept
      - DeliveryTransaction is written to PostgreSQL table with unique constraint
      - PaymentRecord links with transaction_reference
      - Clean rollback / deletion of test data
    """
    if "postgresql" not in settings.DATABASE_URL:
        pytest.skip("Not connected to PostgreSQL")

    db = SessionLocal()
    try:
        # 1. Fetch or create test customer & driver
        cust = db.query(User).filter(User.role == UserRole.CUSTOMER).first()
        driver = db.query(User).filter(User.role == UserRole.DELIVERY_BOY).first()
        assert cust is not None, "PostgreSQL must have at least one customer"
        assert driver is not None, "PostgreSQL must have at least one delivery boy"

        # 2. Create a test booking
        import uuid
        test_booking_num = f"BK-PG-TEST-{uuid.uuid4().hex[:6].upper()}"
        booking = Booking(
            booking_number=test_booking_num,
            customer_id=cust.id,
            cylinder_type="14.2kg",
            quantity=1,
            unit_price=850.0,
            total_amount=850.0,
            subsidy_amount=200.0,
            net_payable=650.0,
            status=BookingStatus.ASSIGNED,
            scheduled_date="2026-10-29"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        # 3. Create test delivery assignment
        assignment = DeliveryAssignment(
            booking_id=booking.id,
            delivery_boy_id=driver.id,
            status="ASSIGNED"
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        # 4. Delivery Confirmation Request by delivery partner
        req_out = DeliveryConfirmationService.create_confirmation_request(
            db=db,
            current_user=driver,
            assignment_id=assignment.id,
            data=DeliveryConfirmationCreate(cylinder_serial="CYL-PG-99", notes="Postgres persistence test")
        )
        assert req_out.status == "REQUESTED"
        assert req_out.request_id.startswith("REQ-")

        # Verify directly with raw psycopg query on PostgreSQL
        with psycopg.connect("postgresql://postgres:postgres@localhost:5432/lpg_erp") as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT status, amount_due, cylinder_serial FROM delivery_confirmation_requests WHERE request_id = %s",
                    (req_out.request_id,)
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == "REQUESTED"
                assert row[1] == 650.0
                assert row[2] == "CYL-PG-99"

        # 5. Customer accepts request
        accept_out = DeliveryConfirmationService.accept_delivery_request(
            db=db,
            current_user=cust,
            request_id=req_out.request_id
        )
        assert accept_out.status == "ACCEPTED"
        tx_ref = accept_out.transaction_reference
        assert tx_ref.startswith("TXN-")

        # Verify transaction and payment directly in PostgreSQL
        with psycopg.connect("postgresql://postgres:postgres@localhost:5432/lpg_erp") as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT transaction_reference, status, amount FROM delivery_transactions WHERE transaction_reference = %s",
                    (tx_ref,)
                )
                tx_row = cur.fetchone()
                assert tx_row is not None
                assert tx_row[0] == tx_ref
                assert tx_row[1] == "ACCEPTED"
                assert tx_row[2] == 650.0

                cur.execute(
                    "SELECT transaction_reference, payment_status, amount FROM payment_records WHERE booking_id = %s",
                    (booking.id,)
                )
                pay_row = cur.fetchone()
                assert pay_row is not None
                assert pay_row[0] == tx_ref
                assert pay_row[1] == "PENDING"
                assert pay_row[2] == 650.0

        # 6. Verify duplicate acceptance is idempotent in PostgreSQL
        retry_out = DeliveryConfirmationService.accept_delivery_request(
            db=db,
            current_user=cust,
            request_id=req_out.request_id
        )
        assert retry_out.transaction_reference == tx_ref

        with psycopg.connect("postgresql://postgres:postgres@localhost:5432/lpg_erp") as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM delivery_transactions WHERE booking_id = %s",
                    (booking.id,)
                )
                count = cur.fetchone()[0]
                assert count == 1, "There must be exactly 1 transaction record in PostgreSQL"

        # Clean up test records
        db.query(DeliveryTransaction).filter(DeliveryTransaction.booking_id == booking.id).delete()
        db.query(DeliveryConfirmationRequest).filter(DeliveryConfirmationRequest.booking_id == booking.id).delete()
        db.query(PaymentRecord).filter(PaymentRecord.booking_id == booking.id).delete()
        db.query(DeliveryAssignment).filter(DeliveryAssignment.id == assignment.id).delete()
        db.query(Booking).filter(Booking.id == booking.id).delete()
        db.commit()

    finally:
        db.close()
