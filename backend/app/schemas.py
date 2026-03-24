from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

# ───────── Auth Schemas ─────────
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # planner / coordinator / customer
    company_name: Optional[str] = None
    customer_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    company_name: Optional[str] = None
    customer_code: Optional[str] = None
    is_active: bool
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ───────── Vessel Schemas ─────────
class VesselCreate(BaseModel):
    name: str
    imo_number: str
    category: str
    hml_flag: Optional[str] = "none"
    segment: Optional[str] = "other"
    loa: Optional[float] = None
    beam: Optional[float] = None
    draft: Optional[float] = None
    is_lotsa: Optional[bool] = False

class VesselResponse(BaseModel):
    id: str
    name: str
    imo_number: str
    category: str
    hml_flag: str
    segment: str
    loa: Optional[float] = None
    beam: Optional[float] = None
    draft: Optional[float] = None
    customer_id: Optional[str] = None
    is_lotsa: bool
    class Config:
        from_attributes = True

# ───────── Slot Schemas ─────────
class SlotResponse(BaseModel):
    id: str
    transit_date: date
    category: str
    direction: str
    period: str
    status: str
    slot_number: int
    is_conditioned: bool
    is_high_demand: bool
    is_auction_slot: bool
    current_price: int
    reservation_id: Optional[str] = None
    class Config:
        from_attributes = True

class SlotConfigRequest(BaseModel):
    transit_date: date
    is_high_demand: Optional[bool] = False

# ───────── Reservation Schemas ─────────
class ReservationCreate(BaseModel):
    vessel_id: str
    transit_date: date
    direction: str  # northbound / southbound
    category: str   # neopanamax / supers / regular

class ReservationResponse(BaseModel):
    id: str
    slot_id: str
    vessel_id: str
    customer_id: str
    origin: str
    status: str
    transit_date: date
    direction: str
    booking_fee: int
    total_fees: int
    penalties: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    vessel_name: Optional[str] = None
    customer_name: Optional[str] = None
    category: Optional[str] = None
    class Config:
        from_attributes = True

class ChangeDateRequest(BaseModel):
    new_date: date

class SubstitutionRequest(BaseModel):
    new_vessel_id: str

class SwapRequest(BaseModel):
    other_reservation_id: str

class CancellationRequest(BaseModel):
    reason: Optional[str] = None

class VoidRequest(BaseModel):
    new_slot_reservation_id: str  # The new reservation that makes this one redundant
    reason: Optional[str] = None

class DaylightTransitRequest(BaseModel):
    reason: Optional[str] = None

class TIARequest(BaseModel):
    new_date: date

class LastMinuteRequest(BaseModel):
    vessel_id: str
    direction: str
    transit_date: date

class SDTRRequest(BaseModel):
    reason: Optional[str] = None

# ───────── Transaction Schemas ─────────
class TransactionResponse(BaseModel):
    id: str
    reservation_id: str
    type: str
    status: str
    requested_by: str
    reviewed_by: Optional[str] = None
    details: Optional[str] = None
    system_validation: Optional[str] = None
    fees: int
    penalties: int
    notes: Optional[str] = None
    form_generated: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    # Joined fields
    vessel_name: Optional[str] = None
    customer_name: Optional[str] = None
    reservation_status: Optional[str] = None
    class Config:
        from_attributes = True

class TransactionAction(BaseModel):
    notes: Optional[str] = None

# ───────── Competition Schemas ─────────
class CompetitionResponse(BaseModel):
    id: str
    slot_id: str
    trigger_reason: str
    status: str
    tiebreaker_method: str
    category: str
    direction: str
    transit_date: str
    winner_customer_id: Optional[str] = None
    recommended_winner_id: Optional[str] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    application_count: Optional[int] = 0
    winner_name: Optional[str] = None
    class Config:
        from_attributes = True

class CompetitionApplyRequest(BaseModel):
    vessel_id: str

class CompetitionApplicationResponse(BaseModel):
    id: str
    competition_id: str
    customer_id: str
    vessel_id: str
    status: str
    ranking_score: int
    hml_validated: str
    direction_validated: str
    submitted_at: datetime
    customer_name: Optional[str] = None
    vessel_name: Optional[str] = None
    class Config:
        from_attributes = True

class SelectWinnerRequest(BaseModel):
    application_id: str

# ───────── Auction Schemas ─────────
class AuctionResponse(BaseModel):
    id: str
    slot_id: str
    auction_type: str
    status: str
    category: str
    direction: str
    transit_date: date
    min_bid: int
    base_price: int
    total_views: int
    total_bids: int
    winning_bid: Optional[int] = None
    winner_customer_id: Optional[str] = None
    planner_approved_at: Optional[datetime] = None
    coordinator_published_at: Optional[datetime] = None
    bidding_opens_at: Optional[datetime] = None
    bidding_closes_at: Optional[datetime] = None
    created_at: datetime
    winner_name: Optional[str] = None
    class Config:
        from_attributes = True

class BidCreate(BaseModel):
    vessel_id: str
    amount: int
    alternate_date: Optional[date] = None
    notes: Optional[str] = None

class BidResponse(BaseModel):
    id: str
    auction_id: str
    customer_id: str
    vessel_id: str
    amount: int
    alternate_date: Optional[date] = None
    status: str
    submitted_at: datetime
    customer_name: Optional[str] = None
    vessel_name: Optional[str] = None
    class Config:
        from_attributes = True

class AuctionApproveRequest(BaseModel):
    notes: Optional[str] = None

# ───────── Slot History Schemas ─────────
class SlotHistoryResponse(BaseModel):
    id: str
    slot_id: str
    customer_id: Optional[str] = None
    vessel_id: Optional[str] = None
    event_type: str
    price: int
    fees: int
    penalties: int
    total: int
    description: Optional[str] = None
    timestamp: datetime
    customer_name: Optional[str] = None
    vessel_name: Optional[str] = None
    class Config:
        from_attributes = True

# ───────── Notification Schemas ─────────
class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# ───────── Waiting List Schemas ─────────
class WaitingListResponse(BaseModel):
    id: str
    customer_id: str
    category: str
    direction: Optional[str] = None
    preferred_dates: Optional[str] = None
    reason: str
    status: str
    created_at: datetime
    customer_name: Optional[str] = None
    class Config:
        from_attributes = True

# ───────── Dashboard / Stats ─────────
class DashboardStats(BaseModel):
    total_slots: int
    available_slots: int
    booked_slots: int
    active_competitions: int
    active_auctions: int
    pending_transactions: int
    total_reservations: int
    total_revenue: int
    unread_notifications: int
