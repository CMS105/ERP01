from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.auth import require_admin
from app.schemas import (
    UserCreate, UserOut, UserStatusUpdate,
    CustomerProfileOut,
    CylinderInventoryCreate, CylinderInventoryUpdate, CylinderInventoryOut,
    BookingOut, BookingAssignRequest, DeliveryAssignmentOut,
    FinancialCorrectionRequest, FinancialCorrectionOut,
    VehicleRecommendationRequest, VehicleRecommendationOut
)
from app.services import AdminService
from app.logistics import VehicleAllocationService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Web Dashboard"])

@router.get("/users", response_model=List[UserOut])
def get_all_users(
    role: Optional[UserRole] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_users(db, role, skip=skip, limit=limit)

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff_or_admin_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.create_user(db, current_user, payload)

@router.put("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.update_user_status(db, current_user, user_id, payload.is_active)

@router.get("/customers", response_model=List[CustomerProfileOut])
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_customers(db, skip=skip, limit=limit)

@router.get("/customers/{customer_id}", response_model=CustomerProfileOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_customer_by_id(db, customer_id)

@router.get("/inventory", response_model=List[CylinderInventoryOut])
def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_inventory(db, skip=skip, limit=limit)

@router.post("/inventory", response_model=CylinderInventoryOut, status_code=status.HTTP_201_CREATED)
def add_cylinder(
    payload: CylinderInventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.create_inventory(db, current_user, payload)

@router.put("/inventory/{cylinder_id}", response_model=CylinderInventoryOut)
def update_cylinder(
    cylinder_id: int,
    payload: CylinderInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.update_inventory(db, current_user, cylinder_id, payload)

@router.get("/bookings", response_model=List[BookingOut])
def list_all_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_bookings(db, skip=skip, limit=limit)

@router.post("/bookings/{booking_id}/assign", response_model=DeliveryAssignmentOut)
def assign_booking_to_delivery_boy(
    booking_id: int,
    payload: BookingAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.assign_booking(
        db, current_user, booking_id,
        payload.delivery_boy_id, payload.cylinder_id, payload.notes
    )

@router.post("/financial/correct", response_model=FinancialCorrectionOut, status_code=status.HTTP_201_CREATED)
def apply_financial_correction(
    payload: FinancialCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.apply_financial_correction(db, current_user, payload)

@router.get("/dashboard/overview", response_model=Dict[str, Any])
def get_admin_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AdminService.get_dashboard_overview(db)

@router.post("/logistics/recommend-vehicle", response_model=VehicleRecommendationOut)
def recommend_vehicle_for_route(
    payload: VehicleRecommendationRequest,
    current_user: User = Depends(require_admin)
):
    return VehicleAllocationService.recommend_vehicle(
        zone_or_route=payload.zone_or_route,
        total_cylinders=payload.total_cylinders,
        delivery_count=payload.delivery_count,
        area_sq_km=payload.area_sq_km,
        has_narrow_access=payload.has_narrow_access,
        has_coordinates=payload.has_coordinates
    )

@router.get("/logistics/routes-summary", response_model=List[VehicleRecommendationOut])
def get_logistics_routes_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return VehicleAllocationService.get_route_summaries(db)
