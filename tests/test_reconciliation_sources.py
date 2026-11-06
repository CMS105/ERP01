import pytest
from app.models import Booking, DeliveryExecution, PaymentRecord, DeliveryOutcome, PaymentStatus, BookingStatus
from app.reconciliation_sources import live_rule_delivery_no_payment, live_rule_amount_mismatch
import uuid
from datetime import datetime, timezone

def test_live_rule_delivery_no_payment(db_session, seed_data):
    test_user = seed_data["customer"]

    # Create successful delivery with NO payment
    b1 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        cylinder_type="14.2kg",
        quantity=1,
        unit_price=850.0,
        total_amount=850.0,
        subsidy_amount=200.0,
        net_payable=650.0,
        status=BookingStatus.DELIVERED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b1)
    db_session.commit()

    de1 = DeliveryExecution(
        assignment_id=9991,
        booking_id=b1.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.DELIVERED_SUCCESS,
        outcome_timestamp=datetime.now(timezone.utc)
    )
    db_session.add(de1)
    db_session.commit()

    # Create failed delivery with no payment (should NOT be flagged)
    b2 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        status=BookingStatus.CANCELLED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b2)
    db_session.commit()

    de2 = DeliveryExecution(
        assignment_id=9992,
        booking_id=b2.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.CUSTOMER_UNAVAILABLE,
        outcome_timestamp=datetime.now(timezone.utc)
    )
    db_session.add(de2)
    db_session.commit()

    # Create successful delivery WITH payment (should NOT be flagged)
    b3 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        status=BookingStatus.DELIVERED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b3)
    db_session.commit()

    de3 = DeliveryExecution(
        assignment_id=9993,
        booking_id=b3.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.DELIVERED_SUCCESS,
        outcome_timestamp=datetime.now(timezone.utc)
    )
    db_session.add(de3)

    pr3 = PaymentRecord(
        booking_id=b3.id,
        customer_id=test_user.id,
        amount=650.0,
        payment_method="CASH",
        payment_status=PaymentStatus.COLLECTED
    )
    db_session.add(pr3)
    db_session.commit()

    findings = live_rule_delivery_no_payment(db_session)

    # We should only find de1
    exec_ids = [f["affected_record_id"] for f in findings]
    assert f"EXEC-{de1.id}" in exec_ids
    assert f"EXEC-{de2.id}" not in exec_ids
    assert f"EXEC-{de3.id}" not in exec_ids

def test_live_rule_amount_mismatch(db_session, seed_data):
    test_user = seed_data["customer"]

    # Match amount
    b1 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        net_payable=650.0,
        status=BookingStatus.DELIVERED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b1)
    db_session.commit()

    de1 = DeliveryExecution(
        assignment_id=8881,
        booking_id=b1.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.DELIVERED_SUCCESS,
    )
    db_session.add(de1)

    pr1 = PaymentRecord(
        booking_id=b1.id,
        customer_id=test_user.id,
        amount=650.0,
        payment_method="CASH",
        payment_status=PaymentStatus.COLLECTED
    )
    db_session.add(pr1)
    db_session.commit()

    # Mismatch amount
    b2 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        net_payable=950.0,
        status=BookingStatus.DELIVERED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b2)
    db_session.commit()

    de2 = DeliveryExecution(
        assignment_id=8882,
        booking_id=b2.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.DELIVERED_SUCCESS,
    )
    db_session.add(de2)

    pr2 = PaymentRecord(
        booking_id=b2.id,
        customer_id=test_user.id,
        amount=650.0,
        payment_method="UPI",
        payment_status=PaymentStatus.COLLECTED
    )
    db_session.add(pr2)
    db_session.commit()

    # Pending payment (should NOT be flagged even if amount differs)
    b3 = Booking(
        booking_number=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=test_user.id,
        net_payable=950.0,
        status=BookingStatus.DELIVERED,
        scheduled_date="2026-10-10"
    )
    db_session.add(b3)
    db_session.commit()

    de3 = DeliveryExecution(
        assignment_id=8883,
        booking_id=b3.id,
        delivery_boy_id=test_user.id,
        outcome=DeliveryOutcome.DELIVERED_SUCCESS,
    )
    db_session.add(de3)

    pr3 = PaymentRecord(
        booking_id=b3.id,
        customer_id=test_user.id,
        amount=650.0,
        payment_method="UPI",
        payment_status=PaymentStatus.PENDING
    )
    db_session.add(pr3)
    db_session.commit()

    findings = live_rule_amount_mismatch(db_session)

    pay_ids = [f["affected_record_id"] for f in findings]
    assert f"PAY-{pr1.id}" not in pay_ids
    assert f"PAY-{pr2.id}" in pay_ids
    assert f"PAY-{pr3.id}" not in pay_ids
