import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models import (
    CustomerRecord, BookingRecord, DeliveryRecord, PaymentItem,
    CylinderMovement, SubsidyRecord, ReconciliationRun, ReconciliationFinding,
    AuditLog
)

def rule_duplicate_booking(db: Session) -> List[Dict[str, Any]]:
    sub = (
        db.query(
            BookingRecord.customer_id,
            BookingRecord.booking_date,
            func.min(BookingRecord.id).label("min_id")
        )
        .group_by(BookingRecord.customer_id, BookingRecord.booking_date)
        .having(func.count(BookingRecord.id) > 1)
        .subquery()
    )

    dups = (
        db.query(BookingRecord)
        .join(
            sub,
            (BookingRecord.customer_id == sub.c.customer_id)
            & (BookingRecord.booking_date == sub.c.booking_date)
            & (BookingRecord.id != sub.c.min_id)
        )
        .all()
    )

    findings = []
    for b in dups:
        findings.append({
            "rule_code": "DUPLICATE_BOOKING",
            "severity": "HIGH",
            "affected_table": "bookings",
            "affected_record_id": b.booking_id,
            "explanation": f"Duplicate booking {b.booking_id} for customer {b.customer_id} on {b.booking_date}"
        })
    return findings

def rule_delivery_no_payment(db: Session) -> List[Dict[str, Any]]:
    q = (
        db.query(DeliveryRecord)
        .outerjoin(PaymentItem, DeliveryRecord.delivery_id == PaymentItem.delivery_id)
        .filter(PaymentItem.id.is_(None))
        .all()
    )

    findings = []
    for d in q:
        findings.append({
            "rule_code": "DELIVERY_NO_PAYMENT",
            "severity": "CRITICAL",
            "affected_table": "deliveries",
            "affected_record_id": d.delivery_id,
            "explanation": f"Delivery {d.delivery_id} has no corresponding payment record"
        })
    return findings

def rule_duplicate_payment(db: Session) -> List[Dict[str, Any]]:
    sub = (
        db.query(
            PaymentItem.delivery_id,
            func.min(PaymentItem.id).label("min_id")
        )
        .group_by(PaymentItem.delivery_id)
        .having(func.count(PaymentItem.id) > 1)
        .subquery()
    )

    dups = (
        db.query(PaymentItem)
        .join(
            sub,
            (PaymentItem.delivery_id == sub.c.delivery_id)
            & (PaymentItem.id != sub.c.min_id)
        )
        .all()
    )

    findings = []
    for p in dups:
        findings.append({
            "rule_code": "DUPLICATE_PAYMENT",
            "severity": "HIGH",
            "affected_table": "payments",
            "affected_record_id": p.payment_id,
            "explanation": f"Duplicate payment {p.payment_id} recorded for delivery {p.delivery_id}"
        })
    return findings

def rule_amount_mismatch(db: Session) -> List[Dict[str, Any]]:
    sub = (
        db.query(
            PaymentItem.delivery_id,
            func.min(PaymentItem.id).label("min_id")
        )
        .group_by(PaymentItem.delivery_id)
        .subquery()
    )

    mismatches = (
        db.query(DeliveryRecord, PaymentItem)
        .join(sub, DeliveryRecord.delivery_id == sub.c.delivery_id)
        .join(PaymentItem, PaymentItem.id == sub.c.min_id)
        .filter(PaymentItem.amount != DeliveryRecord.amount_due)
        .all()
    )

    findings = []
    for d, p in mismatches:
        findings.append({
            "rule_code": "AMOUNT_MISMATCH",
            "severity": "HIGH",
            "affected_table": "payments",
            "affected_record_id": d.delivery_id,
            "explanation": f"Delivery {d.delivery_id} expected amount {d.amount_due} but collected {p.amount}"
        })
    return findings

def rule_missing_empty_return(db: Session) -> List[Dict[str, Any]]:
    in_sub = (
        db.query(CylinderMovement.delivery_id)
        .filter(CylinderMovement.direction == "IN")
        .subquery()
    )

    outs = (
        db.query(CylinderMovement.delivery_id)
        .filter(
            CylinderMovement.direction == "OUT",
            ~CylinderMovement.delivery_id.in_(in_sub.select())
        )
        .distinct()
        .all()
    )

    findings = []
    for row in outs:
        did = row[0]
        findings.append({
            "rule_code": "MISSING_EMPTY_RETURN",
            "severity": "MEDIUM",
            "affected_table": "cylinder_movements",
            "affected_record_id": did,
            "explanation": f"Delivery {did} has cylinder dispatched OUT without empty return movement IN"
        })
    return findings

def rule_subsidy_ineligible(db: Session) -> List[Dict[str, Any]]:
    ineligible = (
        db.query(SubsidyRecord)
        .join(CustomerRecord, SubsidyRecord.customer_id == CustomerRecord.customer_id)
        .filter(
            or_(
                CustomerRecord.subsidy_eligible.is_(False),
                CustomerRecord.active.is_(False)
            )
        )
        .all()
    )

    findings = []
    for s in ineligible:
        findings.append({
            "rule_code": "SUBSIDY_INELIGIBLE",
            "severity": "CRITICAL",
            "affected_table": "subsidy",
            "affected_record_id": s.subsidy_id,
            "explanation": f"Subsidy {s.subsidy_id} granted to ineligible or inactive customer {s.customer_id}"
        })
    return findings

RULES = [
    ("DUPLICATE_BOOKING", rule_duplicate_booking),
    ("DELIVERY_NO_PAYMENT", rule_delivery_no_payment),
    ("DUPLICATE_PAYMENT", rule_duplicate_payment),
    ("AMOUNT_MISMATCH", rule_amount_mismatch),
    ("MISSING_EMPTY_RETURN", rule_missing_empty_return),
    ("SUBSIDY_INELIGIBLE", rule_subsidy_ineligible),
]

def run_reconciliation(db: Session, triggered_by_user_id: Optional[int] = None) -> ReconciliationRun:
    running_job = db.query(ReconciliationRun).filter(ReconciliationRun.status == "RUNNING").first()
    if running_job:
        diff = (datetime.now(timezone.utc) - running_job.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        if diff < 120:
            return running_job
        else:
            running_job.status = "FAILED"
            running_job.error_message = "Timed out"
            db.commit()

    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    run_entry = ReconciliationRun(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        triggered_by_user_id=triggered_by_user_id
    )
    db.add(run_entry)
    db.commit()
    db.refresh(run_entry)

    try:
        total_examined = (
            db.query(BookingRecord).count()
            + db.query(DeliveryRecord).count()
            + db.query(PaymentItem).count()
            + db.query(CylinderMovement).count()
            + db.query(SubsidyRecord).count()
        )

        all_detected = []
        rule_counts = {}

        for code, fn in RULES:
            items = fn(db)
            all_detected.extend(items)
            rule_counts[code] = len(items)

        existing_active = {
            (f.rule_code, f.affected_record_id)
            for f in db.query(ReconciliationFinding.rule_code, ReconciliationFinding.affected_record_id).all()
        }

        new_findings = []
        for d in all_detected:
            key = (d["rule_code"], d["affected_record_id"])
            if key not in existing_active:
                f_id = f"FND-{uuid.uuid4().hex[:10].upper()}"
                finding = ReconciliationFinding(
                    finding_id=f_id,
                    run_id=run_id,
                    rule_code=d["rule_code"],
                    severity=d["severity"],
                    affected_table=d["affected_table"],
                    affected_record_id=d["affected_record_id"],
                    explanation=d["explanation"],
                    detected_at=datetime.now(timezone.utc),
                    review_status="PENDING"
                )
                new_findings.append(finding)
                existing_active.add(key)

        if new_findings:
            db.bulk_save_objects(new_findings)
            db.commit()

        run_entry.status = "COMPLETED"
        run_entry.completed_at = datetime.now(timezone.utc)
        run_entry.records_examined = total_examined
        run_entry.findings_count = len(all_detected)
        run_entry.summary_json = json.dumps({
            "total_detected": len(all_detected),
            "new_stored": len(new_findings),
            "by_rule": rule_counts
        })
        db.commit()
        db.refresh(run_entry)

        audit = AuditLog(
            user_id=triggered_by_user_id,
            user_role="ADMIN" if triggered_by_user_id else "SYSTEM",
            action="RUN_RECONCILIATION",
            resource_type="ReconciliationRun",
            resource_id=run_id,
            details=f"Examined {total_examined} records. Detected {len(all_detected)} findings.",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()

        return run_entry

    except Exception as e:
        db.rollback()
        run_entry.status = "FAILED"
        run_entry.completed_at = datetime.now(timezone.utc)
        run_entry.error_message = str(e)
        db.commit()
        raise e

def evaluate_against_ground_truth(db: Session, ground_truth_path: str = "data/ground_truth.csv") -> Dict[str, Any]:
    truth_df = pd.read_csv(ground_truth_path)
    all_findings = []
    for code, fn in RULES:
        for item in fn(db):
            all_findings.append((item["rule_code"], item["affected_record_id"]))

    found_df = pd.DataFrame(all_findings, columns=["error_type", "record_id"])
    t = truth_df[["error_type", "record_id"]]

    hit = t.merge(found_df, on=["error_type", "record_id"])
    planted = len(t)
    detected = len(found_df)
    tp = len(hit)
    fp = detected - tp
    fn_count = planted - tp

    precision = tp / detected if detected > 0 else 1.0
    recall = tp / planted if planted > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    breakdown = {}
    for rule in truth_df["error_type"].unique():
        t_sub = t[t.error_type == rule]
        f_sub = found_df[found_df.error_type == rule]
        h_sub = t_sub.merge(f_sub, on=["error_type", "record_id"])
        rule_planted = len(t_sub)
        rule_tp = len(h_sub)
        rule_fp = len(f_sub) - rule_tp
        rule_fn = rule_planted - rule_tp
        breakdown[rule] = {
            "planted": rule_planted,
            "detected": len(f_sub),
            "true_positives": rule_tp,
            "false_positives": rule_fp,
            "false_negatives": rule_fn
        }

    return {
        "planted_total": planted,
        "detected_total": detected,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn_count,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "rules_breakdown": breakdown
    }
