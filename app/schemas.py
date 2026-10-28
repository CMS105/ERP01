from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models import UserRole, BookingStatus, DeliveryOutcome, PaymentStatus, PaymentMethod, CylinderStatus

class Token(BaseModel):
    access_token: str
    token_type: str
    role: UserRole
    user_id: int
    full_name: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[UserRole] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    consumer_number: str
    address: str
    city: str
    pincode: str
    connection_type: Optional[str] = "14.2kg Domestic"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    role: UserRole
    employee_code: Optional[str] = None
    vehicle_number: Optional[str] = None
    assigned_hub_zone: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_active: bool

class CustomerProfileUpdate(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None

class CustomerProfileOut(BaseModel):
    id: int
    user_id: int
    consumer_number: str
    address: str
    city: str
    pincode: str
    cylinder_quota_limit: int
    quota_used_this_year: int
    connection_type: str

    model_config = ConfigDict(from_attributes=True)

class StaffProfileOut(BaseModel):
    id: int
    user_id: int
    employee_code: str
    vehicle_number: str
    assigned_hub_zone: str
    is_on_duty: bool

    model_config = ConfigDict(from_attributes=True)

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime
    customer_profile: Optional[CustomerProfileOut] = None
    staff_profile: Optional[StaffProfileOut] = None

    model_config = ConfigDict(from_attributes=True)

class CylinderInventoryCreate(BaseModel):
    serial_number: str
    cylinder_type: str = "14.2kg"
    status: CylinderStatus = CylinderStatus.IN_STOCK
    batch_code: str

class CylinderInventoryUpdate(BaseModel):
    status: Optional[CylinderStatus] = None
    batch_code: Optional[str] = None

class CylinderInventoryOut(BaseModel):
    id: int
    serial_number: str
    cylinder_type: str
    status: CylinderStatus
    batch_code: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BookingCreate(BaseModel):
    cylinder_type: str = "14.2kg"
    quantity: int = 1
    scheduled_date: str

class PaymentRecordOut(BaseModel):
    id: int
    booking_id: int
    customer_id: int
    delivery_boy_id: Optional[int] = None
    amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_reference: Optional[str] = None
    collected_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DeliveryExecutionOut(BaseModel):
    id: int
    assignment_id: int
    booking_id: int
    delivery_boy_id: int
    outcome: DeliveryOutcome
    outcome_timestamp: datetime
    offline_sync_id: Optional[str] = None
    synced_at: datetime
    empty_cylinder_returned_serial: Optional[str] = None
    failure_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DeliveryAssignmentOut(BaseModel):
    id: int
    booking_id: int
    delivery_boy_id: int
    cylinder_id: Optional[int] = None
    assigned_at: datetime
    status: str
    notes: Optional[str] = None
    execution: Optional[DeliveryExecutionOut] = None

    model_config = ConfigDict(from_attributes=True)

class BookingOut(BaseModel):
    id: int
    booking_number: str
    customer_id: int
    cylinder_type: str
    quantity: int
    unit_price: float
    total_amount: float
    subsidy_amount: float
    net_payable: float
    status: BookingStatus
    scheduled_date: str
    created_at: datetime
    assignment: Optional[DeliveryAssignmentOut] = None
    payment: Optional[PaymentRecordOut] = None

    model_config = ConfigDict(from_attributes=True)

class BookingAssignRequest(BaseModel):
    delivery_boy_id: int
    cylinder_id: Optional[int] = None
    notes: Optional[str] = None

class DeliveryOutcomeRequest(BaseModel):
    outcome: DeliveryOutcome
    empty_cylinder_returned_serial: Optional[str] = None
    customer_signature_data: Optional[str] = None
    failure_reason: Optional[str] = None
    offline_sync_id: Optional[str] = None

class PaymentCollectRequest(BaseModel):
    amount: float
    payment_method: PaymentMethod
    transaction_reference: Optional[str] = None

class OfflineSyncOutcomeItem(BaseModel):
    offline_sync_id: str
    assignment_id: int
    outcome: DeliveryOutcome
    outcome_timestamp: datetime
    empty_cylinder_returned_serial: Optional[str] = None
    failure_reason: Optional[str] = None
    customer_signature_data: Optional[str] = None

class OfflineSyncPaymentItem(BaseModel):
    booking_id: int
    amount: float
    payment_method: PaymentMethod
    transaction_reference: Optional[str] = None
    collected_at: datetime

class OfflineSyncBatchRequest(BaseModel):
    outcomes: List[OfflineSyncOutcomeItem] = []
    payments: List[OfflineSyncPaymentItem] = []

class OfflineSyncBatchResponse(BaseModel):
    synced_outcomes_count: int
    synced_payments_count: int
    errors: List[str] = []

class FinancialCorrectionRequest(BaseModel):
    payment_id: int
    corrected_amount: float
    reason: str
    audit_notes: str

class FinancialCorrectionOut(BaseModel):
    id: int
    payment_id: int
    booking_id: int
    corrected_by_user_id: int
    original_amount: float
    corrected_amount: float
    reason: str
    audit_notes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_role: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ReconciliationReportItem(BaseModel):
    booking_id: int
    booking_number: str
    customer_id: int
    booking_status: str
    delivery_status: Optional[str] = None
    delivery_outcome: Optional[str] = None
    payment_status: Optional[str] = None
    expected_amount: float
    collected_amount: Optional[float] = None
    is_reconciled: bool
    notes: str

class DiscrepancyReportItem(BaseModel):
    issue_type: str
    booking_id: Optional[int] = None
    customer_id: Optional[int] = None
    delivery_boy_id: Optional[int] = None
    details: str
    severity: str

class FinancialSummaryOut(BaseModel):
    total_bookings: int
    total_sales_value: float
    total_collected_amount: float
    total_pending_amount: float
    collections_by_method: dict
    total_corrections_count: int
    net_correction_variance: float
