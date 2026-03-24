import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum, Date
from app.database import Base
import enum

class AuctionType(str, enum.Enum):
    REGULAR = "regular"
    SEALED = "sealed"

class AuctionStatus(str, enum.Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    PUBLISHED = "published"
    BIDDING = "bidding"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"

class BidStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    WINNER = "winner"
    REJECTED = "rejected"
    OUTBID = "outbid"

class Auction(Base):
    __tablename__ = "auctions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String, ForeignKey("slots.id"), nullable=False)
    auction_type = Column(SAEnum(AuctionType), default=AuctionType.REGULAR)
    status = Column(SAEnum(AuctionStatus), default=AuctionStatus.DRAFT)
    category = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    transit_date = Column(Date, nullable=False)
    min_bid = Column(Integer, default=0)
    base_price = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_bids = Column(Integer, default=0)
    winning_bid = Column(Integer, nullable=True)
    winner_customer_id = Column(String, ForeignKey("users.id"), nullable=True)
    proposed_params = Column(Text, nullable=True)  # JSON string of proposed config
    planner_approved_at = Column(DateTime, nullable=True)
    planner_id = Column(String, ForeignKey("users.id"), nullable=True)
    coordinator_published_at = Column(DateTime, nullable=True)
    coordinator_id = Column(String, ForeignKey("users.id"), nullable=True)
    bidding_opens_at = Column(DateTime, nullable=True)
    bidding_closes_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Bid(Base):
    __tablename__ = "bids"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id = Column(String, ForeignKey("auctions.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    vessel_id = Column(String, ForeignKey("vessels.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    alternate_date = Column(Date, nullable=True)
    status = Column(SAEnum(BidStatus), default=BidStatus.SUBMITTED)
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)
