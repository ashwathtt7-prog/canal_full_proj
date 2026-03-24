import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from app.database import Base
import enum

class CompetitionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    OPEN = "open"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"

class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    WINNER = "winner"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class Competition(Base):
    __tablename__ = "competitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String, ForeignKey("slots.id"), nullable=False)
    trigger_reason = Column(String, default="cancellation")
    status = Column(SAEnum(CompetitionStatus), default=CompetitionStatus.PENDING)
    tiebreaker_method = Column(String, default="customer_ranking")
    category = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    transit_date = Column(String, nullable=False)
    winner_customer_id = Column(String, ForeignKey("users.id"), nullable=True)
    recommended_winner_id = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    validated_by = Column(String, ForeignKey("users.id"), nullable=True)
    opened_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

class CompetitionApplication(Base):
    __tablename__ = "competition_applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    competition_id = Column(String, ForeignKey("competitions.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    vessel_id = Column(String, ForeignKey("vessels.id"), nullable=False)
    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED)
    ranking_score = Column(Integer, default=0)
    hml_validated = Column(String, default="pending")  # pending / passed / failed
    direction_validated = Column(String, default="pending")
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
