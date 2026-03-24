"""
Dynamic Slot Management System
Manages slot allocation, carryover, availability checks, and restriction enforcement.
"""
from datetime import date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.slot import Slot, SlotStatus, Direction, BookingPeriod
from app.models.reservation import Reservation, ReservationStatus

# Official slot distribution table
SLOT_DISTRIBUTION = {
    "neopanamax": {
        "special": 1, "period_1": 0, "lotsa": 3,
        "period_1a": 3, "period_2": 2, "auction": 1, "total": 10
    },
    "supers": {
        "special": 3, "period_1": 6, "lotsa": 0,
        "period_1a": 0, "period_2": 10, "auction": 1, "total": 20
    },
    "regular": {
        "special": 2, "period_1": 1, "lotsa": 0,
        "period_1a": 0, "period_2": 2, "auction": 1, "total": 6
    }
}

# Restriction limits
RESTRICTIONS = {
    "neopanamax": {
        "max_per_direction": 4,
        "max_hml_per_direction": 1,
        "max_lng_per_day": 2,
        "max_per_customer_per_day": None,
    },
    "supers": {
        "max_per_direction": 10,
        "max_hml_per_direction": 4,
        "max_daylight_restricted_per_day": 8,
        "max_per_customer_per_day": 2,
    },
    "regular": {
        "max_per_direction": 3,
        "max_restricted_per_direction": 1,
        "max_restricted_per_day": 2,
        "max_per_customer_per_day": None,
    }
}

class SlotEngine:
    def __init__(self, db: Session):
        self.db = db

    def determine_period(self, transit_date: date) -> BookingPeriod:
        """Determine the current booking period based on days until transit."""
        days_until = (transit_date - date.today()).days

        if days_until >= 366:
            return BookingPeriod.SPECIAL
        elif days_until >= 90:
            return BookingPeriod.PERIOD_1
        elif days_until >= 50:
            return BookingPeriod.LOTSA
        elif days_until >= 15:
            return BookingPeriod.PERIOD_1A
        elif days_until >= 8:
            return BookingPeriod.PERIOD_2
        elif days_until >= 2:
            return BookingPeriod.PERIOD_3
        else:
            return BookingPeriod.FCFS

    def generate_daily_slots(self, transit_date: date):
        """Generate the full 36-slot configuration for a given transit date."""
        existing = self.db.query(Slot).filter(Slot.transit_date == transit_date).first()
        if existing:
            return  # Already generated

        slot_number = 1
        for category, periods in SLOT_DISTRIBUTION.items():
            for direction in [Direction.NORTHBOUND, Direction.SOUTHBOUND]:
                for period_key, count in periods.items():
                    if period_key in ("auction", "total"):
                        continue
                    if count == 0:
                        continue

                    for i in range(count):
                        is_conditioned = (
                            category == "neopanamax" and
                            period_key == "period_2" and
                            i == count - 1  # Last slot in period 2 for NEO
                        )
                        slot = Slot(
                            transit_date=transit_date,
                            category=category,
                            direction=direction,
                            period=BookingPeriod(period_key),
                            status=SlotStatus.AVAILABLE,
                            slot_number=slot_number,
                            is_conditioned=is_conditioned,
                            is_auction_slot=False,
                        )
                        self.db.add(slot)
                        slot_number += 1

                # Add auction slot per category per direction
                auction_count = periods.get("auction", 0)
                for i in range(auction_count):
                    slot = Slot(
                        transit_date=transit_date,
                        category=category,
                        direction=direction,
                        period=BookingPeriod.PERIOD_3,
                        status=SlotStatus.AVAILABLE,
                        slot_number=slot_number,
                        is_auction_slot=True,
                    )
                    self.db.add(slot)
                    slot_number += 1

        self.db.commit()

    def get_availability(self, transit_date: date, category: Optional[str] = None,
                         direction: Optional[str] = None) -> List[Slot]:
        """Get available slots for a given date, optionally filtered."""
        query = self.db.query(Slot).filter(
            Slot.transit_date == transit_date,
            Slot.status == SlotStatus.AVAILABLE
        )
        if category:
            query = query.filter(Slot.category == category)
        if direction:
            query = query.filter(Slot.direction == direction)
        return query.all()

    def get_slot_summary(self, transit_date: date) -> Dict:
        """Get a summary of slot allocation for a date."""
        all_slots = self.db.query(Slot).filter(Slot.transit_date == transit_date).all()

        summary = {
            "transit_date": str(transit_date),
            "total": len(all_slots),
            "available": len([s for s in all_slots if s.status == SlotStatus.AVAILABLE]),
            "booked": len([s for s in all_slots if s.status == SlotStatus.BOOKED]),
            "auction": len([s for s in all_slots if s.status == SlotStatus.AUCTION]),
            "competition": len([s for s in all_slots if s.status == SlotStatus.COMPETITION]),
            "by_category": {}
        }

        for cat in ["neopanamax", "supers", "regular"]:
            cat_slots = [s for s in all_slots if s.category == cat]
            summary["by_category"][cat] = {
                "total": len(cat_slots),
                "available": len([s for s in cat_slots if s.status == SlotStatus.AVAILABLE]),
                "booked": len([s for s in cat_slots if s.status == SlotStatus.BOOKED]),
                "by_direction": {}
            }
            for dir_val in ["northbound", "southbound"]:
                dir_slots = [s for s in cat_slots if s.direction.value == dir_val]
                summary["by_category"][cat]["by_direction"][dir_val] = {
                    "total": len(dir_slots),
                    "available": len([s for s in dir_slots if s.status == SlotStatus.AVAILABLE]),
                    "booked": len([s for s in dir_slots if s.status == SlotStatus.BOOKED]),
                }

        return summary

    def check_restrictions(self, category: str, direction: str,
                           transit_date: date, vessel=None, customer_id=None) -> Dict:
        """Check if booking restrictions are satisfied."""
        result = {"allowed": True, "violations": []}
        limits = RESTRICTIONS.get(category, {})

        # Count existing booked slots for the date/category/direction
        booked_in_dir = self.db.query(Slot).filter(
            Slot.transit_date == transit_date,
            Slot.category == category,
            Slot.direction == direction,
            Slot.status == SlotStatus.BOOKED
        ).count()

        max_dir = limits.get("max_per_direction")
        if max_dir and booked_in_dir >= max_dir:
            result["allowed"] = False
            result["violations"].append(
                f"Maximum {max_dir} {category} vessels per direction reached"
            )

        # Check customer per-day limit for Supers
        if customer_id and limits.get("max_per_customer_per_day"):
            customer_bookings = self.db.query(Slot).join(
                Reservation, Slot.reservation_id == Reservation.id
            ).filter(
                Slot.transit_date == transit_date,
                Slot.category == category,
                Reservation.customer_id == customer_id,
                Slot.status == SlotStatus.BOOKED
            ).count()

            max_cust = limits["max_per_customer_per_day"]
            if customer_bookings >= max_cust:
                result["allowed"] = False
                result["violations"].append(
                    f"Maximum {max_cust} slots per customer per day for {category}"
                )

        # HML checks
        if vessel and vessel.hml_flag and vessel.hml_flag.value != "none":
            hml_count = self.db.query(Slot).filter(
                Slot.transit_date == transit_date,
                Slot.category == category,
                Slot.direction == direction,
                Slot.status == SlotStatus.BOOKED
            ).count()  # Simplified — in production would join vessel HML

            max_hml = limits.get("max_hml_per_direction")
            if max_hml and hml_count >= max_hml:
                result["allowed"] = False
                result["violations"].append(
                    f"Maximum HML-restricted vessels per direction reached"
                )

            # HML=M cannot swap/substitute/change date
            if vessel.hml_flag.value == "M":
                result["hml_m_restricted"] = True

        return result

    def release_slot(self, slot_id: str) -> Optional[str]:
        """Release a slot back to inventory and determine routing.
        Returns: 'competition', 'auction', 'fcfs', or None"""
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return None

        slot.status = SlotStatus.AVAILABLE
        slot.reservation_id = None

        period = self.determine_period(slot.transit_date)

        if period == BookingPeriod.PERIOD_3:
            slot.status = SlotStatus.AUCTION
            self.db.commit()
            return "auction"
        elif period in (BookingPeriod.PERIOD_1, BookingPeriod.PERIOD_1A, BookingPeriod.PERIOD_2):
            slot.status = SlotStatus.COMPETITION
            self.db.commit()
            return "competition"
        else:
            self.db.commit()
            return "fcfs"

    def allocate_slot(self, slot_id: str, reservation_id: str, price: int = 0) -> bool:
        """Allocate a slot to a reservation."""
        slot = self.db.query(Slot).filter(
            Slot.id == slot_id,
            Slot.status.in_([SlotStatus.AVAILABLE, SlotStatus.COMPETITION, SlotStatus.AUCTION])
        ).first()
        if not slot:
            return False

        slot.status = SlotStatus.BOOKED
        slot.reservation_id = reservation_id
        slot.current_price = price
        self.db.commit()
        return True
