from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import Base, engine
from app.routers import auth, customer, delivery_boy, admin, auditor, reconciliation

Base.metadata.create_all(bind=engine)

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

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "LPG ERP Backend API",
        "supported_roles": ["CUSTOMER", "DELIVERY_BOY", "ADMIN", "AUDITOR"]
    }

@app.get("/console")
def get_console():
    return FileResponse("index.html")
