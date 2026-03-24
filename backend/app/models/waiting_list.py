import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SAEnum
from app.database import Base
import enum

class WaitingListStatus(str, enum.Enum):
    ACTIVE = "active"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REMOVED = "removed"

class WaitingList(Base):
    __tablename__ = "waiting_list"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    vessel_id = Column(String, ForeignKey("vessels.id"), nullable=True)
    category = Column(String, nullable=False)
    direction = Column(String, nullable=True)
    preferred_dates = Column(Text, nullable=True)  # JSON array of dates
    reason = Column(String, default="auction_loss")  # auction_loss / competition_loss / request
    status = Column(SAEnum(WaitingListStatus), default=WaitingListStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
