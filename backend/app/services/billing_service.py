"""
Billing Service
Generates billing records and integrates with the billing subsystem.
"""
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.slot_history import SlotHistory
from app.services.pricing_service import PricingService

class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.pricing = PricingService()

    def record_booking_charge(self, slot_id: str, customer_id: str,
                               vessel_id: str, price: int, description: str = "") -> SlotHistory:
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="booking",
            price=price,
            fees=0,
            penalties=0,
            total=price,
            description=description or f"Booking fee charged: ${price:,}",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_substitution_charge(self, slot_id: str, customer_id: str,
                                     vessel_id: str, booking_fee: int) -> SlotHistory:
        fee = self.pricing.calculate_substitution_fee(booking_fee)
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="substitution",
            price=booking_fee,
            fees=fee,
            penalties=0,
            total=booking_fee + fee,
            description=f"Substitution fee: ${fee:,} (60% of ${booking_fee:,})",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_swap_charge(self, slot_id: str, customer_id: str,
                            vessel_id: str, booking_fee: int) -> SlotHistory:
        fee = self.pricing.calculate_swap_fee(booking_fee)
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="swap",
            price=booking_fee,
            fees=fee,
            penalties=0,
            total=booking_fee + fee,
            description=f"Swap fee: ${fee:,} (1% of ${booking_fee:,})",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_cancellation_charge(self, slot_id: str, customer_id: str,
                                     vessel_id: str, booking_fee: int,
                                     penalty_rate: float) -> SlotHistory:
        penalty = self.pricing.calculate_cancellation_penalty(booking_fee, penalty_rate)
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="cancellation",
            price=0,
            fees=0,
            penalties=penalty,
            total=penalty,
            description=f"Cancellation penalty: ${penalty:,} ({int(penalty_rate*100)}% of ${booking_fee:,})",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_auction_win(self, slot_id: str, customer_id: str,
                            vessel_id: str, bid_amount: int) -> SlotHistory:
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="auction_win",
            price=bid_amount,
            fees=0,
            penalties=0,
            total=bid_amount,
            description=f"Auction winning bid: ${bid_amount:,}",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_void(self, slot_id: str, customer_id: str,
                     vessel_id: str) -> SlotHistory:
        entry = SlotHistory(
            slot_id=slot_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            event_type="void",
            price=0,
            fees=0,
            penalties=0,
            total=0,
            description="Administrative void — no charges applied",
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_slot_total_revenue(self, slot_id: str) -> int:
        entries = self.db.query(SlotHistory).filter(
            SlotHistory.slot_id == slot_id
        ).all()
        return sum(e.total for e in entries)
