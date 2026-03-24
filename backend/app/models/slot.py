import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Date, Boolean, DateTime, Integer, Enum as SAEnum
from app.database import Base
import enum

class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    AUCTION = "auction"
    COMPETITION = "competition"
    RESERVED = "reserved"
    BLOCKED = "blocked"

class Direction(str, enum.Enum):
    NORTHBOUND = "northbound"
    SOUTHBOUND = "southbound"

class BookingPeriod(str, enum.Enum):
    SPECIAL = "special"           # 730-366 days
    PERIOD_1 = "period_1"         # 90 days
    LOTSA = "lotsa"               # ≤50 days
    PERIOD_1A = "period_1a"       # 30-15 days
    PERIOD_2 = "period_2"         # 14-8 days
    PERIOD_3 = "period_3"         # 7-2 days (auction window)
    FCFS = "fcfs"                 # First Come First Serve

class Slot(Base):
    __tablename__ = "slots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transit_date = Column(Date, nullable=False, index=True)
    category = Column(String, nullable=False)  # neopanamax / supers / regular
    direction = Column(SAEnum(Direction), nullable=False)
    period = Column(SAEnum(BookingPeriod), nullable=False)
    status = Column(SAEnum(SlotStatus), default=SlotStatus.AVAILABLE)
    slot_number = Column(Integer, nullable=False)  # Slot position within category
    is_conditioned = Column(Boolean, default=False)  # Period 2 conditioned NEO slot
    is_high_demand = Column(Boolean, default=False)
    is_auction_slot = Column(Boolean, default=False)
    current_price = Column(Integer, default=0)
    reservation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
