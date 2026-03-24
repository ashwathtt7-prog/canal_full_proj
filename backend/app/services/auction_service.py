"""
Auction Service
Manages the Auction lifecycle from slot detection to award.
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.auction import Auction, Bid, AuctionType, AuctionStatus, BidStatus
from app.models.slot import Slot, SlotStatus
from app.models.vessel import Vessel
from app.models.user import User, UserRole
from app.models.waiting_list import WaitingList, WaitingListStatus
from app.models.notification import Notification
from app.services.pricing_service import PricingService

class AuctionService:
    def __init__(self, db: Session):
        self.db = db
        self.pricing = PricingService()

    def create_auction(self, slot_id: str, auction_type: str = "regular") -> Auction:
        """Create an auction for an available slot in Period 3."""
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            raise ValueError("Slot not found")

        slot.status = SlotStatus.AUCTION
        base_price = self.pricing.get_base_price(
            slot.category, "period_3", slot.is_high_demand
        )

        # Generate proposed parameters
        params = {
            "category": slot.category,
            "direction": slot.direction.value if hasattr(slot.direction, 'value') else slot.direction,
            "transit_date": str(slot.transit_date),
            "base_price": base_price,
            "min_bid": base_price,
            "auction_type": auction_type,
            "is_high_demand": slot.is_high_demand,
            "bidding_duration_hours": 24,
        }

        auction = Auction(
            slot_id=slot_id,
            auction_type=AuctionType(auction_type),
            status=AuctionStatus.PROPOSED,
            category=slot.category,
            direction=slot.direction.value if hasattr(slot.direction, 'value') else slot.direction,
            transit_date=slot.transit_date,
            min_bid=base_price,
            base_price=base_price,
            proposed_params=json.dumps(params),
        )
        self.db.add(auction)
        self.db.commit()

        # Notify planners
        self._notify_planners(auction, "New auction proposal requires your review")
        return auction

    def planner_approve(self, auction_id: str, planner_id: str,
                         notes: Optional[str] = None) -> Auction:
        """Planner reviews and approves auction parameters."""
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise ValueError("Auction not found")

        auction.status = AuctionStatus.APPROVED
        auction.planner_approved_at = datetime.utcnow()
        auction.planner_id = planner_id
        self.db.commit()

        # Notify coordinators
        self._notify_coordinators(auction, "Auction approved — ready for publication")
        return auction

    def coordinator_publish(self, auction_id: str, coordinator_id: str) -> Auction:
        """Coordinator publishes the auction and opens bidding."""
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise ValueError("Auction not found")

        now = datetime.utcnow()
        auction.status = AuctionStatus.BIDDING
        auction.coordinator_published_at = now
        auction.coordinator_id = coordinator_id
        auction.bidding_opens_at = now
        auction.bidding_closes_at = now + timedelta(hours=24)
        self.db.commit()

        # Notify subscribed customers
        self._notify_customers(auction, "New auction open — place your bids")
        return auction

    def submit_bid(self, auction_id: str, customer_id: str,
                    vessel_id: str, amount: int,
                    alternate_date=None, notes=None) -> Bid:
        """Customer submits a bid."""
        auction = self.db.query(Auction).filter(
            Auction.id == auction_id,
            Auction.status == AuctionStatus.BIDDING
        ).first()
        if not auction:
            raise ValueError("Auction not found or not in bidding phase")

        # Validate minimum bid
        if amount < auction.min_bid:
            raise ValueError(f"Bid must be at least ${auction.min_bid:,}")

        # Validate vessel
        vessel = self.db.query(Vessel).filter(Vessel.id == vessel_id).first()
        if not vessel:
            raise ValueError("Vessel not found")
        if vessel.category != auction.category:
            raise ValueError(f"Vessel category must be {auction.category}")

        # Check for existing bid from this customer
        existing = self.db.query(Bid).filter(
            Bid.auction_id == auction_id,
            Bid.customer_id == customer_id
        ).first()
        if existing:
            # Update existing bid
            existing.amount = amount
            existing.vessel_id = vessel_id
            existing.alternate_date = alternate_date
            existing.notes = notes
            existing.submitted_at = datetime.utcnow()
            self.db.commit()
            bid = existing
        else:
            bid = Bid(
                auction_id=auction_id,
                customer_id=customer_id,
                vessel_id=vessel_id,
                amount=amount,
                alternate_date=alternate_date,
                status=BidStatus.VALIDATED,
                notes=notes,
            )
            self.db.add(bid)
            auction.total_bids += 1
            self.db.commit()

        return bid

    def get_monitor_data(self, auction_id: str, reveal_identities: bool = False) -> Dict:
        """Get auction monitoring dashboard data. Identities hidden until close."""
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise ValueError("Auction not found")

        bids = self.db.query(Bid).filter(Bid.auction_id == auction_id).all()

        bid_data = []
        for bid in bids:
            entry = {
                "id": bid.id,
                "amount": bid.amount,
                "status": bid.status.value if hasattr(bid.status, 'value') else bid.status,
                "submitted_at": str(bid.submitted_at),
                "has_alternate_date": bid.alternate_date is not None,
            }
            if reveal_identities or auction.status in (AuctionStatus.CLOSED, AuctionStatus.AWARDED):
                customer = self.db.query(User).filter(User.id == bid.customer_id).first()
                vessel = self.db.query(Vessel).filter(Vessel.id == bid.vessel_id).first()
                entry["customer_name"] = customer.full_name if customer else "Unknown"
                entry["vessel_name"] = vessel.name if vessel else "Unknown"
                entry["customer_id"] = bid.customer_id
            else:
                entry["customer_name"] = f"Bidder #{bids.index(bid) + 1}"
                entry["vessel_name"] = "Hidden"
            bid_data.append(entry)

        amounts = [b.amount for b in bids] if bids else [0]
        return {
            "auction_id": auction_id,
            "status": auction.status.value if hasattr(auction.status, 'value') else auction.status,
            "total_bids": len(bids),
            "total_views": auction.total_views,
            "highest_bid": max(amounts),
            "lowest_bid": min(amounts),
            "average_bid": sum(amounts) // len(amounts) if amounts else 0,
            "bids": sorted(bid_data, key=lambda x: x["amount"], reverse=True),
            "time_remaining": str(auction.bidding_closes_at - datetime.utcnow()) if auction.bidding_closes_at else None,
        }

    def close_auction(self, auction_id: str) -> Auction:
        """Close auction and determine winner."""
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise ValueError("Auction not found")

        bids = self.db.query(Bid).filter(
            Bid.auction_id == auction_id,
            Bid.status == BidStatus.VALIDATED
        ).order_by(Bid.amount.desc()).all()

        if not bids:
            auction.status = AuctionStatus.CANCELLED
            self.db.commit()
            return auction

        # Winner is highest bid
        winner = bids[0]
        winner.status = BidStatus.WINNER
        auction.winning_bid = winner.amount
        auction.winner_customer_id = winner.customer_id
        auction.status = AuctionStatus.CLOSED

        # Mark others as outbid
        for bid in bids[1:]:
            bid.status = BidStatus.OUTBID

        self.db.commit()

        # Add non-winners to waiting list
        for bid in bids[1:]:
            wl = WaitingList(
                customer_id=bid.customer_id,
                vessel_id=bid.vessel_id,
                category=auction.category,
                direction=auction.direction,
                reason="auction_loss",
                status=WaitingListStatus.ACTIVE,
            )
            self.db.add(wl)

        self.db.commit()

        # Notify winner
        self._notify_user(winner.customer_id, "Auction Won!",
                          f"Your bid of ${winner.amount:,} won the auction for {auction.category} slot on {auction.transit_date}",
                          "auction_won")

        return auction

    def award_auction(self, auction_id: str) -> Auction:
        """Finalize the auction award."""
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise ValueError("Auction not found")

        auction.status = AuctionStatus.AWARDED
        self.db.commit()
        return auction

    def increment_views(self, auction_id: str):
        auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
        if auction:
            auction.total_views += 1
            self.db.commit()

    def _notify_planners(self, auction: Auction, message: str):
        planners = self.db.query(User).filter(User.role == UserRole.PLANNER).all()
        for p in planners:
            self.db.add(Notification(
                user_id=p.id, type="auction_proposed",
                title="Auction Proposal", message=message,
                link=f"/auctions/{auction.id}"
            ))
        self.db.commit()

    def _notify_coordinators(self, auction: Auction, message: str):
        coords = self.db.query(User).filter(User.role == UserRole.COORDINATOR).all()
        for c in coords:
            self.db.add(Notification(
                user_id=c.id, type="auction_approved",
                title="Auction Ready", message=message,
                link=f"/auctions/{auction.id}"
            ))
        self.db.commit()

    def _notify_customers(self, auction: Auction, message: str):
        customers = self.db.query(User).filter(User.role == UserRole.CUSTOMER).all()
        for c in customers:
            self.db.add(Notification(
                user_id=c.id, type="auction_open",
                title="Auction Open for Bidding",
                message=f"{message} — {auction.category.upper()} {auction.direction} on {auction.transit_date}",
                link=f"/auctions/{auction.id}"
            ))
        self.db.commit()

    def _notify_user(self, user_id: str, title: str, message: str, notif_type: str):
        self.db.add(Notification(
            user_id=user_id, type=notif_type,
            title=title, message=message,
        ))
        self.db.commit()
