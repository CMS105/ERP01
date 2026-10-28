from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_delivery_boy
from app.schemas import (
    DeliveryAssignmentOut, DeliveryOutcomeRequest, DeliveryExecutionOut,
    PaymentCollectRequest, PaymentRecordOut,
    OfflineSyncBatchRequest, OfflineSyncBatchResponse,
    DeliveryConfirmationCreate, DeliveryConfirmationRequestOut, DeliveryTransactionOut
)
from app.services import DeliveryBoyService, DeliveryConfirmationService

router = APIRouter(prefix="/api/v1/delivery-boy", tags=["Delivery Boy App"])

@router.get("/deliveries/assigned", response_model=List[DeliveryAssignmentOut])
def get_assigned_deliveries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryBoyService.get_assigned_deliveries(db, current_user, skip=skip, limit=limit)

@router.post("/deliveries/{assignment_id}/outcome", response_model=DeliveryExecutionOut, status_code=status.HTTP_201_CREATED)
def record_delivery_outcome(
    assignment_id: int,
    payload: DeliveryOutcomeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryBoyService.record_delivery_outcome(db, current_user, assignment_id, payload)

@router.post("/deliveries/{assignment_id}/collect-payment", response_model=PaymentRecordOut, status_code=status.HTTP_201_CREATED)
def collect_delivery_payment(
    assignment_id: int,
    payload: PaymentCollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryBoyService.collect_payment(db, current_user, assignment_id, payload)

@router.post("/deliveries/sync-offline", response_model=OfflineSyncBatchResponse)
@router.post("/sync-offline", response_model=OfflineSyncBatchResponse)
def sync_offline_records(
    payload: OfflineSyncBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryBoyService.sync_offline(db, current_user, payload)

@router.post("/deliveries/{assignment_id}/request-confirmation", response_model=DeliveryConfirmationRequestOut, status_code=status.HTTP_201_CREATED)
def request_delivery_confirmation(
    assignment_id: int,
    payload: Optional[DeliveryConfirmationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.create_confirmation_request(
        db, current_user, assignment_id=assignment_id, data=payload
    )

@router.get("/deliveries/{assignment_id}/request-status", response_model=DeliveryConfirmationRequestOut)
def get_delivery_confirmation_status(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.get_partner_request_status(
        db, current_user, assignment_id=assignment_id
    )

@router.post("/delivery-requests", response_model=DeliveryConfirmationRequestOut, status_code=status.HTTP_201_CREATED)
def create_delivery_request(
    payload: DeliveryConfirmationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.create_confirmation_request(
        db, current_user, data=payload
    )

@router.get("/delivery-requests/{request_id}", response_model=DeliveryConfirmationRequestOut)
def get_delivery_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.get_partner_request(
        db, current_user, request_id=request_id
    )

@router.post("/delivery-requests/{request_id}/in-progress", response_model=DeliveryConfirmationRequestOut)
def mark_delivery_in_progress(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.mark_in_progress(
        db, current_user, request_id=request_id
    )

@router.get("/transactions/{transaction_reference}", response_model=DeliveryTransactionOut)
def get_delivery_transaction(
    transaction_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_boy)
):
    return DeliveryConfirmationService.get_transaction_by_reference(
        db, current_user, transaction_reference=transaction_reference
    )

