from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User, UserRole
from app.models.slot import Slot, SlotStatus
from app.models.reservation import Reservation
from app.models.competition import Competition, CompetitionStatus
from app.models.auction import Auction, AuctionStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.notification import Notification
from app.models.slot_history import SlotHistory
from app.models.vessel import Vessel
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_slots = db.query(Slot).count()
    available_slots = db.query(Slot).filter(Slot.status == SlotStatus.AVAILABLE).count()
    booked_slots = db.query(Slot).filter(Slot.status == SlotStatus.BOOKED).count()
    active_competitions = db.query(Competition).filter(
        Competition.status.in_([CompetitionStatus.PENDING, CompetitionStatus.VALIDATED, CompetitionStatus.OPEN])
    ).count()
    active_auctions = db.query(Auction).filter(
        Auction.status.in_([AuctionStatus.PROPOSED, AuctionStatus.APPROVED, AuctionStatus.PUBLISHED, AuctionStatus.BIDDING])
    ).count()
    pending_transactions = db.query(Transaction).filter(
        Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.UNDER_REVIEW,
                                TransactionStatus.PLANNER_REVIEW, TransactionStatus.LOTSA_REVIEW])
    ).count()
    if current_user.role == UserRole.CUSTOMER:
        total_reservations = db.query(Reservation).filter(Reservation.customer_id == current_user.id).count()
    else:
        total_reservations = db.query(Reservation).count()
    total_revenue = db.query(func.coalesce(func.sum(SlotHistory.total), 0)).scalar()
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).count()
    return DashboardStats(
        total_slots=total_slots, available_slots=available_slots, booked_slots=booked_slots,
        active_competitions=active_competitions, active_auctions=active_auctions,
        pending_transactions=pending_transactions, total_reservations=total_reservations,
        total_revenue=total_revenue, unread_notifications=unread_notifications,
    )

@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    recent_txs = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()
    activities = []
    for tx in recent_txs:
        customer = db.query(User).filter(User.id == tx.requested_by).first()
        activities.append({
            "type": "transaction",
            "subtype": tx.type.value if hasattr(tx.type, 'value') else tx.type,
            "status": tx.status.value if hasattr(tx.status, 'value') else tx.status,
            "customer_name": customer.full_name if customer else "Unknown",
            "timestamp": str(tx.created_at), "id": tx.id,
        })
    recent_history = db.query(SlotHistory).order_by(SlotHistory.timestamp.desc()).limit(10).all()
    for sh in recent_history:
        customer = db.query(User).filter(User.id == sh.customer_id).first()
        activities.append({
            "type": "billing", "subtype": sh.event_type,
            "description": sh.description, "total": sh.total,
            "customer_name": customer.full_name if customer else "Unknown",
            "timestamp": str(sh.timestamp), "id": sh.id,
        })
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:20]
