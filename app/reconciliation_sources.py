from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Booking, DeliveryExecution, PaymentRecord, DeliveryOutcome, PaymentStatus

def live_rule_delivery_no_payment(db: Session) -> List[Dict[str, Any]]:
    """
    Identify successful deliveries for which a payment record is genuinely missing.
    We exclude deliveries where payment status is explicitly pending, failed, or refunded,
    unless there is truly no payment record at all.
    """
    q = (
        db.query(DeliveryExecution)
        .outerjoin(PaymentRecord, DeliveryExecution.booking_id == PaymentRecord.booking_id)
        .filter(DeliveryExecution.outcome == DeliveryOutcome.DELIVERED_SUCCESS)
        .filter(PaymentRecord.id.is_(None))
        .all()
    )

    findings = []
    for d in q:
        findings.append({
            "rule_code": "LIVE_DELIVERY_NO_PAYMENT",
            "severity": "CRITICAL",
            "affected_table": "delivery_executions",
            "affected_record_id": f"EXEC-{d.id}", # String ID to avoid collisions
            "explanation": f"Live delivery execution {d.id} for booking {d.booking_id} has no payment record"
        })
    return findings

def live_rule_amount_mismatch(db: Session) -> List[Dict[str, Any]]:
    """
    For successful deliveries with a collected payment, compare Booking.net_payable versus PaymentRecord.amount
    """
    q = (
        db.query(DeliveryExecution, Booking, PaymentRecord)
        .join(Booking, Booking.id == DeliveryExecution.booking_id)
        .join(PaymentRecord, PaymentRecord.booking_id == DeliveryExecution.booking_id)
        .filter(DeliveryExecution.outcome == DeliveryOutcome.DELIVERED_SUCCESS)
        .filter(PaymentRecord.payment_status == PaymentStatus.COLLECTED)
        .all()
    )

    findings = []
    for exec_record, booking, payment in q:
        # Avoid floating point direct comparison by using an epsilon or rounding
        if abs(booking.net_payable - payment.amount) > 0.01:
            findings.append({
                "rule_code": "LIVE_AMOUNT_MISMATCH",
                "severity": "HIGH",
                "affected_table": "payment_records",
                "affected_record_id": f"PAY-{payment.id}",
                "explanation": f"Live delivery {exec_record.id} expected amount {booking.net_payable:.2f} but collected {payment.amount:.2f}"
            })
    return findings
