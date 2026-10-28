from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text

from app.database import Base


class OcrScan(Base):
    __tablename__ = "ocr_scans"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255))
    uploaded_by = Column(Integer, nullable=False)   # user id
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    avg_confidence = Column(Float)
    raw_text = Column(Text)
    parsed_rows = Column(JSON)                      # list of row dicts
    status = Column(String(20), default="PENDING_REVIEW", nullable=False)
    reviewed_by = Column(Integer)
    reviewed_at = Column(DateTime)
    review_note = Column(Text)
