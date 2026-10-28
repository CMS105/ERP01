from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_auditor
from app.schemas import (
    ReconciliationReportItem, DiscrepancyReportItem,
    FinancialSummaryOut, FinancialCorrectionOut, AuditLogOut
)
from app.services import AuditorService

router = APIRouter(prefix="/api/v1/auditor", tags=["Auditor Web Dashboard"])

@router.get("/reconciliation-reports", response_model=List[ReconciliationReportItem])
def get_reconciliation_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor)
):
    return AuditorService.get_reconciliation_reports(db, skip=skip, limit=limit)

@router.get("/discrepancy-evidence", response_model=List[DiscrepancyReportItem])
def get_discrepancy_evidence(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor)
):
    return AuditorService.get_discrepancy_evidence(db, limit=limit)

@router.get("/financial-summaries", response_model=FinancialSummaryOut)
def get_financial_summaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor)
):
    return AuditorService.get_financial_summaries(db)

@router.get("/financial-corrections", response_model=List[FinancialCorrectionOut])
def get_financial_corrections_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor)
):
    return AuditorService.get_financial_corrections(db, skip=skip, limit=limit)

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor)
):
    return AuditorService.get_audit_logs(db, skip=skip, limit=limit)
