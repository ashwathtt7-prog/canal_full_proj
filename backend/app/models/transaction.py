import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from app.database import Base
import enum

class TransactionType(str, enum.Enum):
    CHANGE_DATE = "change_date"
    SUBSTITUTION = "substitution"
    SWAP = "swap"
    TIA = "tia"
    LAST_MINUTE = "last_minute"
    SDTR = "sdtr"
    CANCELLATION = "cancellation"
    VOID = "void"
    DAYLIGHT_TRANSIT = "daylight_transit"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    PLANNER_REVIEW = "planner_review"
    LOTSA_REVIEW = "lotsa_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_id = Column(String, ForeignKey("reservations.id"), nullable=False)
    type = Column(SAEnum(TransactionType), nullable=False)
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING)
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    # JSON-encoded detail fields
    details = Column(Text, nullable=True)          # {"new_date": "...", "new_vessel_id": "...", etc.}
    system_validation = Column(Text, nullable=True)  # {"availability": true, "direction_ok": true, ...}
    fees = Column(Integer, default=0)
    penalties = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    form_generated = Column(String, default="no")  # no / yes
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
