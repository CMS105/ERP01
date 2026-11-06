import pytest
import json
from app.models import BookingRecord, ReconciliationFinding, ReconciliationRun
from app.reconciliation import run_reconciliation

def test_auto_resolve_finding(db_session):
    # Setup initial error condition
    b1 = BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01")
    b2 = BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    db_session.add_all([b1, b2])
    db_session.commit()

    run1 = run_reconciliation(db_session)
    assert run1.findings_count == 1

    finding = db_session.query(ReconciliationFinding).first()
    assert finding.review_status == "PENDING"
    assert finding.rule_code == "DUPLICATE_BOOKING"

    # Fix the issue by deleting the duplicate booking
    db_session.delete(b2)
    db_session.commit()

    run2 = run_reconciliation(db_session)
    # Finding shouldn't be detected anymore
    assert run2.findings_count == 0

    # Check if finding got auto-resolved
    updated_finding = db_session.query(ReconciliationFinding).filter_by(finding_id=finding.finding_id).first()
    assert updated_finding.review_status == "RESOLVED"
    assert "Auto-resolved" in updated_finding.review_reason

    summary = json.loads(run2.summary_json)
    assert summary["auto_resolved"] == 1

def test_dismissed_finding_recurrence(db_session):
    # Setup initial error condition
    b1 = BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01")
    b2 = BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    db_session.add_all([b1, b2])
    db_session.commit()

    run1 = run_reconciliation(db_session)

    finding = db_session.query(ReconciliationFinding).first()

    # Manually dismiss it
    finding.review_status = "DISMISSED"
    db_session.commit()

    # Issue still exists, run again
    run2 = run_reconciliation(db_session)
    assert run2.findings_count == 1

    # A NEW finding should be created since the old one is DISMISSED (not existing_active)
    findings = db_session.query(ReconciliationFinding).filter_by(rule_code="DUPLICATE_BOOKING").all()
    assert len(findings) == 2

    assert findings[0].review_status == "DISMISSED"
    assert findings[1].review_status == "PENDING"
