import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SAEnum, Boolean
from app.database import Base
import enum

class VesselCategory(str, enum.Enum):
    NEOPANAMAX = "neopanamax"
    SUPERS = "supers"
    REGULAR = "regular"

class HMLFlag(str, enum.Enum):
    NONE = "none"
    C = "C"
    D = "D"
    M = "M"

class VesselSegment(str, enum.Enum):
    FULL_CONTAINER = "full_container"
    LNG = "lng"
    LPG = "lpg"
    VEHICLE_CARRIER = "vehicle_carrier"
    RORO = "roro"
    PASSENGER = "passenger"
    TANKER = "tanker"
    BULK = "bulk"
    GENERAL_CARGO = "general_cargo"
    OTHER = "other"

class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    imo_number = Column(String, unique=True, nullable=False, index=True)
    category = Column(SAEnum(VesselCategory), nullable=False)
    hml_flag = Column(SAEnum(HMLFlag), default=HMLFlag.NONE)
    segment = Column(SAEnum(VesselSegment), default=VesselSegment.OTHER)
    loa = Column(Float, nullable=True)  # Length Overall in meters
    beam = Column(Float, nullable=True)  # Beam in meters
    draft = Column(Float, nullable=True)  # Draft in meters
    customer_id = Column(String, ForeignKey("users.id"), nullable=True)
    is_lotsa = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
