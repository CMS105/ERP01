import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    User, UserRole, CustomerProfile, StaffProfile, CylinderInventory,
    Booking, BookingStatus, DeliveryAssignment, CylinderStatus
)
from app.auth import hash_password, create_access_token
from app.cache import cache

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    cache.clear()
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        cache.clear()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def seed_data(db_session):
    customer = User(
        email="customer1@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Rajesh Kumar",
        phone="9876543210",
        role=UserRole.CUSTOMER,
        is_active=True
    )
    customer2 = User(
        email="customer2@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Pooja Sharma",
        phone="9876543211",
        role=UserRole.CUSTOMER,
        is_active=True
    )
    delivery_boy = User(
        email="driver1@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Amit Singh",
        phone="9876543212",
        role=UserRole.DELIVERY_BOY,
        is_active=True
    )
    delivery_boy2 = User(
        email="driver2@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Suresh Verma",
        phone="9876543213",
        role=UserRole.DELIVERY_BOY,
        is_active=True
    )
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Sanjay Gupta",
        phone="9876543214",
        role=UserRole.ADMIN,
        is_active=True
    )
    auditor = User(
        email="auditor@example.com",
        hashed_password=hash_password("AuditorPass123!"),
        full_name="Meera Iyer",
        phone="9876543215",
        role=UserRole.AUDITOR,
        is_active=True
    )

    db_session.add_all([customer, customer2, delivery_boy, delivery_boy2, admin, auditor])
    db_session.commit()

    cust_profile = CustomerProfile(
        user_id=customer.id,
        consumer_number="CN-10001",
        address="12 MG Road",
        city="Bengaluru",
        pincode="560001",
        cylinder_quota_limit=12,
        quota_used_this_year=1,
        connection_type="14.2kg Domestic"
    )
    cust_profile2 = CustomerProfile(
        user_id=customer2.id,
        consumer_number="CN-10002",
        address="44 Brigade Road",
        city="Bengaluru",
        pincode="560025",
        cylinder_quota_limit=12,
        quota_used_this_year=0,
        connection_type="14.2kg Domestic"
    )
    staff_profile = StaffProfile(
        user_id=delivery_boy.id,
        employee_code="EMP-001",
        vehicle_number="KA-01-AB-1234",
        assigned_hub_zone="Central Hub",
        is_on_duty=True
    )
    staff_profile2 = StaffProfile(
        user_id=delivery_boy2.id,
        employee_code="EMP-002",
        vehicle_number="KA-01-CD-5678",
        assigned_hub_zone="South Hub",
        is_on_duty=True
    )
    db_session.add_all([cust_profile, cust_profile2, staff_profile, staff_profile2])

    cylinder = CylinderInventory(
        serial_number="CYL-9001",
        cylinder_type="14.2kg",
        status=CylinderStatus.IN_STOCK,
        batch_code="BATCH-2026-A"
    )
    cylinder2 = CylinderInventory(
        serial_number="CYL-9002",
        cylinder_type="14.2kg",
        status=CylinderStatus.IN_STOCK,
        batch_code="BATCH-2026-A"
    )
    db_session.add_all([cylinder, cylinder2])
    db_session.commit()

    booking = Booking(
        booking_number="BK-TEST-1001",
        customer_id=customer.id,
        cylinder_type="14.2kg",
        quantity=1,
        unit_price=850.0,
        total_amount=850.0,
        subsidy_amount=200.0,
        net_payable=650.0,
        status=BookingStatus.ASSIGNED,
        scheduled_date="2026-11-01"
    )
    db_session.add(booking)
    db_session.commit()

    assignment = DeliveryAssignment(
        booking_id=booking.id,
        delivery_boy_id=delivery_boy.id,
        cylinder_id=cylinder.id,
        status="ASSIGNED",
        notes="Standard delivery"
    )
    cylinder.status = CylinderStatus.ASSIGNED
    db_session.add(assignment)
    db_session.commit()

    return {
        "customer": customer,
        "customer2": customer2,
        "delivery_boy": delivery_boy,
        "delivery_boy2": delivery_boy2,
        "admin": admin,
        "auditor": auditor,
        "booking": booking,
        "assignment": assignment,
        "cylinder": cylinder
    }

def get_auth_headers(user: User):
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}
