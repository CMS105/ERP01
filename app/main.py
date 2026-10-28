from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal, get_db
from app.models import User, UserRole, CustomerProfile, StaffProfile, Booking, BookingStatus, DeliveryAssignment
from app.auth import hash_password, get_current_user
from app.routers import auth, customer, delivery_boy, admin, auditor, reconciliation, chatbot
from app.schemas import DeliveryTransactionOut
from app.services import DeliveryConfirmationService
from app.cache import cache

Base.metadata.create_all(bind=engine)

def seed_initial_data():
    db = SessionLocal()
    try:
        cust = db.query(User).filter(User.email == "cust_demo@example.com").first()
        if not cust:
            cust = User(
                email="cust_demo@example.com",
                hashed_password=hash_password("Pass123!"),
                full_name="Ramesh Sharma",
                phone="9876543210",
                role=UserRole.CUSTOMER,
                is_active=True
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)

            cp = CustomerProfile(
                user_id=cust.id,
                consumer_number="LPG-889911",
                address="Flat 402, Green Valley Apts",
                city="Bengaluru",
                pincode="560001"
            )
            db.add(cp)
            db.commit()

        driver = db.query(User).filter(User.email == "driver_demo@example.com").first()
        if not driver:
            driver = User(
                email="driver_demo@example.com",
                hashed_password=hash_password("Pass123!"),
                full_name="Vikram Singh",
                phone="9876543211",
                role=UserRole.DELIVERY_BOY,
                is_active=True
            )
            db.add(driver)
            db.commit()
            db.refresh(driver)

            sp = StaffProfile(
                user_id=driver.id,
                employee_code="STAFF-701",
                vehicle_number="KA-01-EQ-1020",
                assigned_hub_zone="Sector 18"
            )
            db.add(sp)
            db.commit()

        bkg = db.query(Booking).filter(Booking.customer_id == cust.id).first()
        if not bkg:
            bkg = Booking(
                booking_number="BK-2025-001",
                customer_id=cust.id,
                cylinder_type="14.2kg",
                quantity=1,
                unit_price=950.0,
                total_amount=950.0,
                subsidy_amount=100.0,
                net_payable=850.0,
                status=BookingStatus.ASSIGNED,
                scheduled_date="2026-10-28"
            )
            db.add(bkg)
            db.commit()
            db.refresh(bkg)

        da = db.query(DeliveryAssignment).filter(DeliveryAssignment.booking_id == bkg.id).first()
        if not da:
            da = DeliveryAssignment(
                booking_id=bkg.id,
                delivery_boy_id=driver.id,
                status="ASSIGNED"
            )
            db.add(da)
            db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

seed_initial_data()

app = FastAPI(
    title="LPG ERP Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(delivery_boy.router)
app.include_router(admin.router)
app.include_router(auditor.router)
app.include_router(reconciliation.router)
app.include_router(chatbot.router)

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "LPG ERP Backend API",
        "supported_roles": ["CUSTOMER", "DELIVERY_BOY", "ADMIN", "AUDITOR"]
    }

@app.get("/health")
def detailed_health_check():
    return {
        "status": "healthy",
        "service": "LPG ERP Backend API",
        "cache_available": cache.is_available(),
        "database": engine.dialect.name
    }

@app.get("/console")
def get_console():
    return FileResponse("index.html")

@app.get("/api/v1/transactions/{transaction_reference}", response_model=DeliveryTransactionOut, tags=["Transactions"])
def get_shared_transaction(
    transaction_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return DeliveryConfirmationService.get_transaction_by_reference(
        db, current_user, transaction_reference=transaction_reference
    )

