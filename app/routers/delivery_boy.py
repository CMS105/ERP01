from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import require_delivery_boy
from app.schemas import (
    DeliveryAssignmentOut, DeliveryOutcomeRequest, DeliveryExecutionOut,
    PaymentCollectRequest, PaymentRecordOut,
    OfflineSyncBatchRequest, OfflineSyncBatchResponse
)
from app.services import DeliveryBoyService

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
