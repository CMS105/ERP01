import os
import pandas as pd
from sqlalchemy.orm import Session
from app.models import (
    CustomerRecord, BookingRecord, DeliveryRecord, PaymentItem,
    CylinderMovement, SubsidyRecord
)

def load_csv_data_to_database(db: Session, data_dir: str = "data", batch_size: int = 5000) -> dict:
    stats = {}

    if os.path.exists(os.path.join(data_dir, "customers.csv")):
        existing = db.query(CustomerRecord).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "customers.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(CustomerRecord, records[i:i + batch_size])
                db.commit()
            stats["customers"] = len(records)
        else:
            stats["customers"] = db.query(CustomerRecord).count()

    if os.path.exists(os.path.join(data_dir, "bookings.csv")):
        existing = db.query(BookingRecord).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "bookings.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(BookingRecord, records[i:i + batch_size])
                db.commit()
            stats["bookings"] = len(records)
        else:
            stats["bookings"] = db.query(BookingRecord).count()

    if os.path.exists(os.path.join(data_dir, "deliveries.csv")):
        existing = db.query(DeliveryRecord).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "deliveries.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(DeliveryRecord, records[i:i + batch_size])
                db.commit()
            stats["deliveries"] = len(records)
        else:
            stats["deliveries"] = db.query(DeliveryRecord).count()

    if os.path.exists(os.path.join(data_dir, "payments.csv")):
        existing = db.query(PaymentItem).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "payments.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(PaymentItem, records[i:i + batch_size])
                db.commit()
            stats["payments"] = len(records)
        else:
            stats["payments"] = db.query(PaymentItem).count()

    if os.path.exists(os.path.join(data_dir, "cylinder_movements.csv")):
        existing = db.query(CylinderMovement).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "cylinder_movements.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(CylinderMovement, records[i:i + batch_size])
                db.commit()
            stats["cylinder_movements"] = len(records)
        else:
            stats["cylinder_movements"] = db.query(CylinderMovement).count()

    if os.path.exists(os.path.join(data_dir, "subsidy.csv")):
        existing = db.query(SubsidyRecord).first()
        if not existing:
            df = pd.read_csv(os.path.join(data_dir, "subsidy.csv"))
            records = df.to_dict(orient="records")
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(SubsidyRecord, records[i:i + batch_size])
                db.commit()
            stats["subsidy"] = len(records)
        else:
            stats["subsidy"] = db.query(SubsidyRecord).count()

    return stats
