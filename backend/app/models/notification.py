import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # competition_open, auction_open, bid_update, transaction_update, system
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    extra_data = Column(Text, nullable=True)  # JSON for additional data
    link = Column(String, nullable=True)    # URL to navigate to
    created_at = Column(DateTime, default=datetime.utcnow)
