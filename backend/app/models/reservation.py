import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from app.database import Base
import enum

class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CHANGED = "changed"
    CANCELLED = "cancelled"
    FORFEITED = "forfeited"
    FORFEIT_REQUEST = "forfeit_request"
    VOIDED = "voided"
    VOID_REQUEST = "void_request"

class ReservationOrigin(str, enum.Enum):
    REGULAR = "regular"
    LOTSA = "lotsa"
    AUCTION = "auction"
    COMPETITION = "competition"
    LAST_MINUTE = "last_minute"
    TIA = "tia"
    FCFS = "fcfs"

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String, ForeignKey("slots.id"), nullable=False)
    vessel_id = Column(String, ForeignKey("vessels.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    origin = Column(SAEnum(ReservationOrigin), default=ReservationOrigin.REGULAR)
    status = Column(SAEnum(ReservationStatus), default=ReservationStatus.PENDING)
    transit_date = Column(Date, nullable=False)
    direction = Column(String, nullable=False)
    booking_fee = Column(Integer, default=0)
    total_fees = Column(Integer, default=0)
    penalties = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
