import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from app.database import Base

class SlotHistory(Base):
    __tablename__ = "slot_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String, ForeignKey("slots.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=True)
    vessel_id = Column(String, ForeignKey("vessels.id"), nullable=True)
    event_type = Column(String, nullable=False)  # booking, substitution, swap, cancellation, auction_win, void
    price = Column(Integer, default=0)
    fees = Column(Integer, default=0)
    penalties = Column(Integer, default=0)
    total = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
