from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import UserRole
from app.ocr_models import OcrScan
from app.ocr_service import extract_lines, parse_lines

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ReviewIn(BaseModel):
    status: str                                       # CONFIRMED or REJECTED
    note: Optional[str] = None
    corrected_rows: Optional[List[dict]] = None


def _scan_out(s: OcrScan, include_text: bool = False):
    out = {
        "id": s.id,
        "filename": s.filename,
        "uploaded_at": s.uploaded_at,
        "avg_confidence": s.avg_confidence,
        "status": s.status,
        "rows": s.parsed_rows,
        "reviewed_by": s.reviewed_by,
        "reviewed_at": s.reviewed_at,
        "review_note": s.review_note,
    }
    if include_text:
        out["raw_text"] = s.raw_text
    return out


@router.post("/scan")
async def scan_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.DELIVERY_BOY)),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a JPEG, PNG or WebP image")

    content = await file.read()
    try:
        lines, avg_conf = extract_lines(content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(500, "OCR failed. Is Tesseract installed on the server?")

    rows = parse_lines(lines)
    scan = OcrScan(
        filename=file.filename,
        uploaded_by=user.id,
        avg_confidence=avg_conf,
        raw_text="\n".join(l["text"] for l in lines),
        parsed_rows=rows,
        status="PENDING_REVIEW",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return _scan_out(scan, include_text=True)


@router.get("/scans")
def list_scans(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.AUDITOR)),
):
    q = db.query(OcrScan).order_by(OcrScan.uploaded_at.desc())
    if status:
        q = q.filter(OcrScan.status == status)
    return [_scan_out(s) for s in q.limit(200).all()]


@router.get("/scans/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.AUDITOR)),
):
    scan = db.get(OcrScan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return _scan_out(scan, include_text=True)


@router.put("/scans/{scan_id}/review")
def review_scan(
    scan_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN)),
):
    if body.status not in {"CONFIRMED", "REJECTED"}:
        raise HTTPException(400, "status must be CONFIRMED or REJECTED")
    scan = db.get(OcrScan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.status != "PENDING_REVIEW":
        raise HTTPException(409, "Scan already reviewed")

    if body.corrected_rows is not None:
        scan.parsed_rows = body.corrected_rows
    scan.status = body.status
    scan.review_note = body.note
    scan.reviewed_by = user.id
    scan.reviewed_at = datetime.utcnow()
    db.commit()
    # NOTE: confirming does NOT post anything to the ledger.
    return _scan_out(scan)
