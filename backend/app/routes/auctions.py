from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.auction import Auction, Bid, AuctionStatus
from app.models.vessel import Vessel
from app.schemas import (
    AuctionResponse, BidCreate, BidResponse, AuctionApproveRequest
)
from app.services.auction_service import AuctionService

router = APIRouter(prefix="/api/auctions", tags=["Auctions"])

@router.get("/", response_model=list[AuctionResponse])
def list_auctions(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Auction)
    if status:
        query = query.filter(Auction.status == status)
    auctions = query.order_by(Auction.created_at.desc()).all()

    result = []
    for a in auctions:
        data = AuctionResponse.model_validate(a)
        if a.winner_customer_id:
            winner = db.query(User).filter(User.id == a.winner_customer_id).first()
            data.winner_name = winner.full_name if winner else None
        result.append(data)
    return result

@router.get("/{auction_id}")
def get_auction(auction_id: str, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    service = AuctionService(db)
    service.increment_views(auction_id)

    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    data = AuctionResponse.model_validate(auction)
    return data

@router.post("/{auction_id}/approve")
def planner_approve(
    auction_id: str,
    data: AuctionApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLANNER))
):
    service = AuctionService(db)
    auction = service.planner_approve(auction_id, current_user.id, data.notes)
    return {"message": "Auction approved by planner", "status": auction.status.value}

@router.post("/{auction_id}/publish")
def coordinator_publish(
    auction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = AuctionService(db)
    auction = service.coordinator_publish(auction_id, current_user.id)
    return {"message": "Auction published", "status": auction.status.value,
            "bidding_closes_at": str(auction.bidding_closes_at)}

@router.post("/{auction_id}/bid")
def submit_bid(
    auction_id: str,
    data: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER))
):
    try:
        service = AuctionService(db)
        bid = service.submit_bid(
            auction_id, current_user.id,
            data.vessel_id, data.amount,
            data.alternate_date, data.notes
        )
        return {"message": "Bid submitted", "bid_id": bid.id, "amount": bid.amount}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{auction_id}/monitor")
def monitor_auction(
    auction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AuctionService(db)
    reveal = current_user.role in (UserRole.PLANNER, UserRole.COORDINATOR) and \
             db.query(Auction).filter(Auction.id == auction_id).first().status in (
                 AuctionStatus.CLOSED, AuctionStatus.AWARDED
             )
    return service.get_monitor_data(auction_id, reveal)

@router.get("/{auction_id}/bids", response_model=list[BidResponse])
def list_bids(
    auction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    # Only reveal after close
    bids = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.amount.desc()).all()
    result = []
    for b in bids:
        data = BidResponse.model_validate(b)
        if auction.status in (AuctionStatus.CLOSED, AuctionStatus.AWARDED):
            customer = db.query(User).filter(User.id == b.customer_id).first()
            vessel = db.query(Vessel).filter(Vessel.id == b.vessel_id).first()
            data.customer_name = customer.full_name if customer else None
            data.vessel_name = vessel.name if vessel else None
        else:
            data.customer_name = "Hidden"
            data.vessel_name = "Hidden"
        result.append(data)
    return result

@router.post("/{auction_id}/close")
def close_auction(
    auction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    service = AuctionService(db)
    auction = service.close_auction(auction_id)
    if auction.status == AuctionStatus.CANCELLED:
        return {"message": "Auction cancelled — no bids received"}
    return {
        "message": "Auction closed",
        "winner_customer_id": auction.winner_customer_id,
        "winning_bid": auction.winning_bid
    }

@router.post("/{auction_id}/award")
def award_auction(
    auction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = AuctionService(db)
    auction = service.award_auction(auction_id)
    return {"message": "Auction awarded", "status": auction.status.value}
