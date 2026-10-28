from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole, CustomerProfile
from app.schemas import Token, LoginRequest, CustomerRegisterRequest, UserOut
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services import log_audit

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_customer(payload: CustomerRegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    existing_consumer = db.query(CustomerProfile).filter(CustomerProfile.consumer_number == payload.consumer_number).first()
    if existing_consumer:
        raise HTTPException(status_code=400, detail="Consumer number is already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = CustomerProfile(
        user_id=user.id,
        consumer_number=payload.consumer_number,
        address=payload.address,
        city=payload.city,
        pincode=payload.pincode,
        cylinder_quota_limit=12,
        quota_used_this_year=0,
        connection_type=payload.connection_type or "14.2kg Domestic"
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    log_audit(db, user, "REGISTER", "CustomerProfile", str(profile.id), f"Customer registered {user.email}")
    return user

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    log_audit(db, user, "LOGIN", "User", str(user.id), f"User {user.email} logged in successfully")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "full_name": user.full_name
    }

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
