import os
from tests.conftest import get_auth_headers
from app.models import (
    CustomerRecord, BookingRecord, DeliveryRecord, PaymentItem,
    CylinderMovement, SubsidyRecord, ReconciliationFinding, AuditLog
)
from app.reconciliation import (
    rule_duplicate_booking, rule_delivery_no_payment,
    rule_duplicate_payment, rule_amount_mismatch,
    rule_missing_empty_return, rule_subsidy_ineligible,
    run_reconciliation, evaluate_against_ground_truth
)
from app.data_loader import load_csv_data_to_database

def test_rule_duplicate_booking_logic(db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B003", customer_id="C002", booking_date="2026-09-01")
    ])
    db_session.commit()

    findings = rule_duplicate_booking(db_session)
    assert len(findings) == 1
    assert findings[0]["affected_record_id"] == "B002"
    assert findings[0]["rule_code"] == "DUPLICATE_BOOKING"

def test_rule_delivery_no_payment_logic(db_session):
    db_session.add_all([
        DeliveryRecord(delivery_id="D001", booking_id="B001", customer_id="C001", staff_id="S01", delivery_date="2026-09-02", amount_due=905.0, cylinder_serial="CYL1", run_id="RUN1"),
        DeliveryRecord(delivery_id="D002", booking_id="B002", customer_id="C002", staff_id="S01", delivery_date="2026-09-02", amount_due=905.0, cylinder_serial="CYL2", run_id="RUN1"),
        PaymentItem(payment_id="P001", delivery_id="D001", mode="CASH", amount=905.0, paid_date="2026-09-02")
    ])
    db_session.commit()

    findings = rule_delivery_no_payment(db_session)
    assert len(findings) == 1
    assert findings[0]["affected_record_id"] == "D002"
    assert findings[0]["rule_code"] == "DELIVERY_NO_PAYMENT"

def test_rule_duplicate_payment_logic(db_session):
    db_session.add_all([
        PaymentItem(payment_id="P001", delivery_id="D001", mode="CASH", amount=905.0, paid_date="2026-09-02"),
        PaymentItem(payment_id="P002", delivery_id="D001", mode="UPI", amount=905.0, paid_date="2026-09-02"),
        PaymentItem(payment_id="P003", delivery_id="D002", mode="CASH", amount=905.0, paid_date="2026-09-02")
    ])
    db_session.commit()

    findings = rule_duplicate_payment(db_session)
    assert len(findings) == 1
    assert findings[0]["affected_record_id"] == "P002"
    assert findings[0]["rule_code"] == "DUPLICATE_PAYMENT"

def test_rule_amount_mismatch_logic(db_session):
    db_session.add_all([
        DeliveryRecord(delivery_id="D001", booking_id="B001", customer_id="C001", staff_id="S01", delivery_date="2026-09-02", amount_due=905.0, cylinder_serial="CYL1", run_id="RUN1"),
        DeliveryRecord(delivery_id="D002", booking_id="B002", customer_id="C002", staff_id="S01", delivery_date="2026-09-02", amount_due=905.0, cylinder_serial="CYL2", run_id="RUN1"),
        PaymentItem(payment_id="P001", delivery_id="D001", mode="CASH", amount=905.0, paid_date="2026-09-02"),
        PaymentItem(payment_id="P002", delivery_id="D002", mode="CASH", amount=850.0, paid_date="2026-09-02")
    ])
    db_session.commit()

    findings = rule_amount_mismatch(db_session)
    assert len(findings) == 1
    assert findings[0]["affected_record_id"] == "D002"
    assert findings[0]["rule_code"] == "AMOUNT_MISMATCH"

def test_rule_missing_empty_return_logic(db_session):
    db_session.add_all([
        CylinderMovement(delivery_id="D001", cylinder_serial="CYL1", direction="OUT", movement_date="2026-09-02"),
        CylinderMovement(delivery_id="D001", cylinder_serial="CYL9", direction="IN", movement_date="2026-09-02"),
        CylinderMovement(delivery_id="D002", cylinder_serial="CYL2", direction="OUT", movement_date="2026-09-02")
    ])
    db_session.commit()

    findings = rule_missing_empty_return(db_session)
    assert len(findings) == 1
    assert findings[0]["affected_record_id"] == "D002"
    assert findings[0]["rule_code"] == "MISSING_EMPTY_RETURN"

def test_rule_subsidy_ineligible_logic(db_session):
    db_session.add_all([
        CustomerRecord(customer_id="C001", name="Alice", village="V1", phone="9111", aadhaar_token="T1", subsidy_eligible=True, active=True),
        CustomerRecord(customer_id="C002", name="Bob", village="V2", phone="9222", aadhaar_token="T2", subsidy_eligible=False, active=True),
        CustomerRecord(customer_id="C003", name="Charlie", village="V3", phone="9333", aadhaar_token="T3", subsidy_eligible=True, active=False),
        SubsidyRecord(subsidy_id="SB001", customer_id="C001", delivery_id="D001", amount=300.0),
        SubsidyRecord(subsidy_id="SB002", customer_id="C002", delivery_id="D002", amount=300.0),
        SubsidyRecord(subsidy_id="SB003", customer_id="C003", delivery_id="D003", amount=300.0)
    ])
    db_session.commit()

    findings = rule_subsidy_ineligible(db_session)
    assert len(findings) == 2
    ids = {f["affected_record_id"] for f in findings}
    assert ids == {"SB002", "SB003"}

def test_empty_database_reconciliation_safe(db_session):
    run = run_reconciliation(db_session)
    assert run.status == "COMPLETED"
    assert run.records_examined == 0
    assert run.findings_count == 0

def test_reconciliation_runner_and_idempotency(db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    ])
    db_session.commit()

    run1 = run_reconciliation(db_session)
    assert run1.status == "COMPLETED"
    assert run1.findings_count == 1
    total_findings_1 = db_session.query(ReconciliationFinding).count()
    assert total_findings_1 == 1

    run2 = run_reconciliation(db_session)
    assert run2.status == "COMPLETED"
    assert run2.findings_count == 1
    total_findings_2 = db_session.query(ReconciliationFinding).count()
    assert total_findings_2 == 1

def test_reconciliation_api_admin_trigger(client, seed_data, db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    ])
    db_session.commit()

    headers = get_auth_headers(seed_data["admin"])
    res = client.post("/api/v1/reconciliation/run", headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["findings_count"] == 1

def test_reconciliation_api_auditor_denied_trigger(client, seed_data):
    headers = get_auth_headers(seed_data["auditor"])
    res = client.post("/api/v1/reconciliation/run", headers=headers)
    assert res.status_code == 403

def test_reconciliation_api_customer_delivery_denied(client, seed_data):
    headers_cust = get_auth_headers(seed_data["customer"])
    headers_driver = get_auth_headers(seed_data["delivery_boy"])

    assert client.get("/api/v1/reconciliation/findings", headers=headers_cust).status_code == 403
    assert client.get("/api/v1/reconciliation/findings", headers=headers_driver).status_code == 403
    assert client.get("/api/v1/reconciliation/summary", headers=headers_cust).status_code == 403
    assert client.get("/api/v1/reconciliation/runs", headers=headers_driver).status_code == 403

def test_reconciliation_findings_pagination_and_filters(client, seed_data, db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01"),
        DeliveryRecord(delivery_id="D001", booking_id="B001", customer_id="C001", staff_id="S01", delivery_date="2026-09-02", amount_due=905.0, cylinder_serial="CYL1", run_id="RUN1")
    ])
    db_session.commit()
    run_reconciliation(db_session)

    headers = get_auth_headers(seed_data["auditor"])
    res = client.get("/api/v1/reconciliation/findings?page=1&limit=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    res_filter = client.get("/api/v1/reconciliation/findings?rule_code=DUPLICATE_BOOKING", headers=headers)
    assert res_filter.status_code == 200
    assert res_filter.json()["total"] == 1

def test_reconciliation_summary_api(client, seed_data, db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    ])
    db_session.commit()
    run_reconciliation(db_session)

    headers = get_auth_headers(seed_data["admin"])
    res = client.get("/api/v1/reconciliation/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_findings"] == 1
    assert data["pending_findings"] == 1
    assert "DUPLICATE_BOOKING" in data["by_rule"]

def test_finding_review_admin_and_audit(client, seed_data, db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    ])
    db_session.commit()
    run_reconciliation(db_session)

    finding = db_session.query(ReconciliationFinding).first()
    assert finding.review_status == "PENDING"

    headers_admin = get_auth_headers(seed_data["admin"])
    review_payload = {
        "review_status": "RESOLVED",
        "reason": "Duplicate cancelled manually in system"
    }
    res = client.put(f"/api/v1/reconciliation/findings/{finding.finding_id}/review", json=review_payload, headers=headers_admin)
    assert res.status_code == 200
    assert res.json()["review_status"] == "RESOLVED"

    audit = db_session.query(AuditLog).filter(AuditLog.action == "REVIEW_FINDING").first()
    assert audit is not None
    assert finding.finding_id in audit.resource_id

def test_finding_review_auditor_denied(client, seed_data, db_session):
    db_session.add_all([
        BookingRecord(booking_id="B001", customer_id="C001", booking_date="2026-09-01"),
        BookingRecord(booking_id="B002", customer_id="C001", booking_date="2026-09-01")
    ])
    db_session.commit()
    run_reconciliation(db_session)

    finding = db_session.query(ReconciliationFinding).first()
    headers_auditor = get_auth_headers(seed_data["auditor"])
    review_payload = {
        "review_status": "RESOLVED",
        "reason": "Auditor trial edit"
    }
    res = client.put(f"/api/v1/reconciliation/findings/{finding.finding_id}/review", json=review_payload, headers=headers_auditor)
    assert res.status_code == 403

def test_ground_truth_evaluation_against_synthetic_data(db_session):
    if not os.path.exists("data/ground_truth.csv"):
        return

    load_csv_data_to_database(db_session, data_dir="data", batch_size=5000)
    metrics = evaluate_against_ground_truth(db_session, ground_truth_path="data/ground_truth.csv")

    assert metrics["planted_total"] == 830
    assert metrics["detected_total"] == 830
    assert metrics["true_positives"] == 830
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
