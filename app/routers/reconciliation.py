from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    User, UserRole, ReconciliationRun, ReconciliationFinding,
    AuditLog, FindingReviewStatus
)
from app.auth import require_roles
from app.schemas import (
    ReconciliationRunOut, ReconciliationFindingOut,
    PaginatedFindingsOut, ReconciliationSummaryOut, FindingReviewRequest
)
from app.reconciliation import run_reconciliation

router = APIRouter(prefix="/api/v1/reconciliation", tags=["Reconciliation Engine"])

require_admin_or_auditor = require_roles(UserRole.ADMIN, UserRole.AUDITOR)
require_admin_only = require_roles(UserRole.ADMIN)

@router.post("/run", response_model=ReconciliationRunOut, status_code=status.HTTP_201_CREATED)
def trigger_reconciliation(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_only)
):
    return run_reconciliation(db, triggered_by_user_id=current_user.id)

@router.get("/runs", response_model=List[ReconciliationRunOut])
def get_reconciliation_runs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_auditor)
):
    return db.query(ReconciliationRun).order_by(ReconciliationRun.id.desc()).limit(limit).all()

@router.get("/summary", response_model=ReconciliationSummaryOut)
def get_reconciliation_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_auditor)
):
    total_runs = db.query(ReconciliationRun).count()
    last_run = db.query(ReconciliationRun).order_by(ReconciliationRun.id.desc()).first()

    total_findings = db.query(ReconciliationFinding).count()
    pending = db.query(ReconciliationFinding).filter(ReconciliationFinding.review_status == "PENDING").count()
    reviewed = db.query(ReconciliationFinding).filter(ReconciliationFinding.review_status == "REVIEWED").count()
    resolved = db.query(ReconciliationFinding).filter(ReconciliationFinding.review_status == "RESOLVED").count()
    dismissed = db.query(ReconciliationFinding).filter(ReconciliationFinding.review_status == "DISMISSED").count()

    by_rule_query = db.query(
        ReconciliationFinding.rule_code,
        func.count(ReconciliationFinding.id)
    ).group_by(ReconciliationFinding.rule_code).all()
    by_rule = {r[0]: r[1] for r in by_rule_query}

    by_sev_query = db.query(
        ReconciliationFinding.severity,
        func.count(ReconciliationFinding.id)
    ).group_by(ReconciliationFinding.severity).all()
    by_sev = {r[0]: r[1] for r in by_sev_query}

    return {
        "total_runs": total_runs,
        "last_run_at": last_run.started_at if last_run else None,
        "last_run_status": last_run.status if last_run else None,
        "total_findings": total_findings,
        "pending_findings": pending,
        "reviewed_findings": reviewed,
        "resolved_findings": resolved,
        "dismissed_findings": dismissed,
        "by_rule": by_rule,
        "by_severity": by_sev
    }

@router.get("/findings", response_model=PaginatedFindingsOut)
def get_reconciliation_findings(
    rule_code: Optional[str] = None,
    severity: Optional[str] = None,
    review_status: Optional[str] = None,
    run_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_auditor)
):
    q = db.query(ReconciliationFinding)

    if rule_code:
        q = q.filter(ReconciliationFinding.rule_code == rule_code)
    if severity:
        q = q.filter(ReconciliationFinding.severity == severity)
    if review_status:
        q = q.filter(ReconciliationFinding.review_status == review_status)
    if run_id:
        q = q.filter(ReconciliationFinding.run_id == run_id)
    if search:
        search_filter = f"%{search}%"
        q = q.filter(
            (ReconciliationFinding.affected_record_id.ilike(search_filter))
            | (ReconciliationFinding.explanation.ilike(search_filter))
            | (ReconciliationFinding.finding_id.ilike(search_filter))
        )

    total = q.count()
    items = q.order_by(ReconciliationFinding.id.asc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items
    }

@router.put("/findings/{finding_id}/review", response_model=ReconciliationFindingOut)
def review_reconciliation_finding(
    finding_id: str,
    payload: FindingReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_only)
):
    finding = db.query(ReconciliationFinding).filter(
        ReconciliationFinding.finding_id == finding_id
    ).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.review_status
    finding.review_status = payload.review_status.value
    finding.reviewed_by_user_id = current_user.id
    finding.reviewed_at = datetime.now(timezone.utc)
    finding.review_reason = payload.reason

    audit = AuditLog(
        user_id=current_user.id,
        user_role=current_user.role.value,
        action="REVIEW_FINDING",
        resource_type="ReconciliationFinding",
        resource_id=finding.finding_id,
        details=f"Status changed from {old_status} to {payload.review_status.value}. Reason: {payload.reason}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()
    db.refresh(finding)

    return finding
