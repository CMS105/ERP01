import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    DELIVERY_BOY = "DELIVERY_BOY"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"

class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class DeliveryOutcome(str, enum.Enum):
    DELIVERED_SUCCESS = "DELIVERED_SUCCESS"
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    ADDRESS_INCORRECT = "ADDRESS_INCORRECT"
    CYLINDER_DEFECTIVE = "CYLINDER_DEFECTIVE"
    CANCELLED_AT_DOORSTEP = "CANCELLED_AT_DOORSTEP"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    ONLINE = "ONLINE"

class CylinderStatus(str, enum.Enum):
    IN_STOCK = "IN_STOCK"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED_FULL = "DELIVERED_FULL"
    RETURNED_EMPTY = "RETURNED_EMPTY"
    MAINTENANCE = "MAINTENANCE"

class FindingReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class FindingSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False)
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False)
    bookings = relationship("Booking", back_populates="customer", foreign_keys="Booking.customer_id")
    assigned_deliveries = relationship("DeliveryAssignment", back_populates="delivery_boy", foreign_keys="DeliveryAssignment.delivery_boy_id")

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    consumer_number = Column(String, unique=True, index=True, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    cylinder_quota_limit = Column(Integer, default=12)
    quota_used_this_year = Column(Integer, default=0)
    connection_type = Column(String, default="14.2kg Domestic")

    user = relationship("User", back_populates="customer_profile")

class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_code = Column(String, unique=True, index=True, nullable=False)
    vehicle_number = Column(String, nullable=False)
    assigned_hub_zone = Column(String, nullable=False)
    is_on_duty = Column(Boolean, default=True)

    user = relationship("User", back_populates="staff_profile")

class CylinderInventory(Base):
    __tablename__ = "cylinder_inventory"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String, unique=True, index=True, nullable=False)
    cylinder_type = Column(String, default="14.2kg", nullable=False)
    status = Column(Enum(CylinderStatus), default=CylinderStatus.IN_STOCK, nullable=False)
    batch_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cylinder_type = Column(String, default="14.2kg", nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, default=850.0, nullable=False)
    total_amount = Column(Float, default=850.0, nullable=False)
    subsidy_amount = Column(Float, default=200.0, nullable=False)
    net_payable = Column(Float, default=650.0, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    scheduled_date = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer = relationship("User", back_populates="bookings", foreign_keys=[customer_id])
    assignment = relationship("DeliveryAssignment", back_populates="booking", uselist=False)
    payment = relationship("PaymentRecord", back_populates="booking", uselist=False)

class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    delivery_boy_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cylinder_id = Column(Integer, ForeignKey("cylinder_inventory.id"), nullable=True)
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="ASSIGNED", nullable=False)
    notes = Column(String, nullable=True)

    booking = relationship("Booking", back_populates="assignment")
    delivery_boy = relationship("User", back_populates="assigned_deliveries", foreign_keys=[delivery_boy_id])
    cylinder = relationship("CylinderInventory")
    execution = relationship("DeliveryExecution", back_populates="assignment", uselist=False)

class DeliveryExecution(Base):
    __tablename__ = "delivery_executions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("delivery_assignments.id"), unique=True, nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    delivery_boy_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(Enum(DeliveryOutcome), nullable=False)
    outcome_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    offline_sync_id = Column(String, unique=True, nullable=True)
    synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    empty_cylinder_returned_serial = Column(String, nullable=True)
    customer_signature_data = Column(Text, nullable=True)
    failure_reason = Column(String, nullable=True)

    assignment = relationship("DeliveryAssignment", back_populates="execution")

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_boy_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_reference = Column(String, unique=True, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking", back_populates="payment")
    corrections = relationship("FinancialCorrection", back_populates="payment")

class FinancialCorrection(Base):
    __tablename__ = "financial_corrections"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payment_records.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    corrected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_amount = Column(Float, nullable=False)
    corrected_amount = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    audit_notes = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment = relationship("PaymentRecord", back_populates="corrections")
    corrected_by = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    details = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CustomerRecord(Base):
    __tablename__ = "customer_records"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    village = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    aadhaar_token = Column(String, nullable=False)
    subsidy_eligible = Column(Boolean, default=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

class BookingRecord(Base):
    __tablename__ = "booking_records"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    booking_date = Column(String, index=True, nullable=False)

    __table_args__ = (
        Index("idx_booking_cust_date", "customer_id", "booking_date"),
    )

class DeliveryRecord(Base):
    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String, unique=True, index=True, nullable=False)
    booking_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    staff_id = Column(String, nullable=False)
    delivery_date = Column(String, nullable=False)
    amount_due = Column(Float, nullable=False)
    cylinder_serial = Column(String, nullable=False)
    run_id = Column(String, nullable=False)

class PaymentItem(Base):
    __tablename__ = "payment_items"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True, nullable=False)
    delivery_id = Column(String, index=True, nullable=False)
    mode = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    paid_date = Column(String, nullable=False)

class CylinderMovement(Base):
    __tablename__ = "cylinder_movements"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String, index=True, nullable=False)
    cylinder_serial = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    movement_date = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_movement_delivery_dir", "delivery_id", "direction"),
    )

class SubsidyRecord(Base):
    __tablename__ = "subsidy_records"

    id = Column(Integer, primary_key=True, index=True)
    subsidy_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    delivery_id = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)

class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="RUNNING", nullable=False)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    records_examined = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    summary_json = Column(Text, nullable=True)
    error_message = Column(String, nullable=True)

    findings = relationship("ReconciliationFinding", back_populates="run")
    triggered_by = relationship("User")

class ReconciliationFinding(Base):
    __tablename__ = "reconciliation_findings"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(String, unique=True, index=True, nullable=False)
    run_id = Column(String, ForeignKey("reconciliation_runs.run_id"), nullable=False)
    rule_code = Column(String, index=True, nullable=False)
    severity = Column(String, index=True, nullable=False)
    affected_table = Column(String, nullable=False)
    affected_record_id = Column(String, index=True, nullable=False)
    explanation = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    review_status = Column(String, default="PENDING", index=True, nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_reason = Column(Text, nullable=True)

    run = relationship("ReconciliationRun", back_populates="findings")
    reviewed_by = relationship("User")

    __table_args__ = (
        Index("idx_finding_rule_record", "rule_code", "affected_record_id"),
    )
