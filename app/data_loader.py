import os
import csv
from sqlalchemy.orm import Session
from app.models import (
    CustomerRecord, BookingRecord, DeliveryRecord, PaymentItem,
    CylinderMovement, SubsidyRecord
)

def _read_csv_records(file_path: str):
    records = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                if v is None:
                    parsed[k] = None
                elif v.lower() == "true":
                    parsed[k] = True
                elif v.lower() == "false":
                    parsed[k] = False
                else:
                    try:
                        if "." in v:
                            parsed[k] = float(v)
                        else:
                            parsed[k] = int(v)
                    except ValueError:
                        parsed[k] = v
            records.append(parsed)
    return records

def load_csv_data_to_database(db: Session, data_dir: str = "data", batch_size: int = 5000) -> dict:
    stats = {}

    cust_path = os.path.join(data_dir, "customers.csv")
    if os.path.exists(cust_path):
        existing = db.query(CustomerRecord).first()
        if not existing:
            records = _read_csv_records(cust_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(CustomerRecord, records[i:i + batch_size])
                db.commit()
            stats["customers"] = len(records)
        else:
            stats["customers"] = db.query(CustomerRecord).count()

    book_path = os.path.join(data_dir, "bookings.csv")
    if os.path.exists(book_path):
        existing = db.query(BookingRecord).first()
        if not existing:
            records = _read_csv_records(book_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(BookingRecord, records[i:i + batch_size])
                db.commit()
            stats["bookings"] = len(records)
        else:
            stats["bookings"] = db.query(BookingRecord).count()

    deliv_path = os.path.join(data_dir, "deliveries.csv")
    if os.path.exists(deliv_path):
        existing = db.query(DeliveryRecord).first()
        if not existing:
            records = _read_csv_records(deliv_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(DeliveryRecord, records[i:i + batch_size])
                db.commit()
            stats["deliveries"] = len(records)
        else:
            stats["deliveries"] = db.query(DeliveryRecord).count()

    pay_path = os.path.join(data_dir, "payments.csv")
    if os.path.exists(pay_path):
        existing = db.query(PaymentItem).first()
        if not existing:
            records = _read_csv_records(pay_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(PaymentItem, records[i:i + batch_size])
                db.commit()
            stats["payments"] = len(records)
        else:
            stats["payments"] = db.query(PaymentItem).count()

    cyl_path = os.path.join(data_dir, "cylinder_movements.csv")
    if os.path.exists(cyl_path):
        existing = db.query(CylinderMovement).first()
        if not existing:
            records = _read_csv_records(cyl_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(CylinderMovement, records[i:i + batch_size])
                db.commit()
            stats["cylinder_movements"] = len(records)
        else:
            stats["cylinder_movements"] = db.query(CylinderMovement).count()

    sub_path = os.path.join(data_dir, "subsidy.csv")
    if os.path.exists(sub_path):
        existing = db.query(SubsidyRecord).first()
        if not existing:
            records = _read_csv_records(sub_path)
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(SubsidyRecord, records[i:i + batch_size])
                db.commit()
            stats["subsidy"] = len(records)
        else:
            stats["subsidy"] = db.query(SubsidyRecord).count()

    return stats
