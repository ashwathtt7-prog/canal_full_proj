"""
N-07 Rules Engine
Validates all booking operations against the Notice to Shipping rules.
"""
from datetime import date, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.vessel import Vessel, VesselCategory, HMLFlag, VesselSegment
from app.models.reservation import Reservation, ReservationStatus
from app.models.slot import Slot

# Period 1A segment priority order
PERIOD_1A_PRIORITY = [
    VesselSegment.FULL_CONTAINER,
    VesselSegment.LNG,
    VesselSegment.LPG,
    VesselSegment.VEHICLE_CARRIER,
    VesselSegment.RORO
]

class RulesEngine:
    def __init__(self, db: Session):
        self.db = db

    def validate_change_date(self, reservation: Reservation, new_date: date,
                              vessel: Vessel) -> Dict:
        """Validate a change date request under N-07 rules."""
        result = {"valid": True, "messages": [], "requires_planner": False}

        # HML=M vessels cannot change date
        if vessel.hml_flag == HMLFlag.M:
            result["valid"] = False
            result["messages"].append("HML=M vessels cannot change date per N-07 rules")
            return result

        # Check if LoTSA — requires additional validation
        if vessel.is_lotsa:
            result["requires_planner"] = True
            result["messages"].append("LoTSA vessel: requires Planner and LoTSA Agent validation")

        return result

    def validate_substitution(self, reservation: Reservation,
                               old_vessel: Vessel, new_vessel: Vessel) -> Dict:
        """Validate a vessel substitution request."""
        result = {"valid": True, "messages": [], "requires_planner": False}

        # Must be same category
        if old_vessel.category != new_vessel.category:
            result["valid"] = False
            result["messages"].append(
                f"Vessel category mismatch: {old_vessel.category.value} → {new_vessel.category.value}"
            )
            return result

        # HML=M cannot substitute
        if old_vessel.hml_flag == HMLFlag.M:
            result["valid"] = False
            result["messages"].append("HML=M vessels cannot be substituted")
            return result

        # Different HML levels require planner review
        if old_vessel.hml_flag != new_vessel.hml_flag:
            result["requires_planner"] = True
            result["messages"].append(
                "Different HML restrictions: requires Planner validation"
            )

        # LoTSA requires planner review
        if old_vessel.is_lotsa or new_vessel.is_lotsa:
            result["requires_planner"] = True
            result["messages"].append("LoTSA vessel involved: requires Planner validation")

        return result

    def validate_swap(self, reservation_a: Reservation, reservation_b: Reservation,
                       vessel_a: Vessel, vessel_b: Vessel) -> Dict:
        """Validate a swap request between two reservations."""
        result = {"valid": True, "messages": [], "requires_planner": False}

        # Max 21 days difference
        day_diff = abs((reservation_a.transit_date - reservation_b.transit_date).days)
        if day_diff > 21:
            result["valid"] = False
            result["messages"].append(
                f"Swap exceeds 21-day limit: {day_diff} days difference"
            )
            return result

        # HML=M cannot swap
        if vessel_a.hml_flag == HMLFlag.M or vessel_b.hml_flag == HMLFlag.M:
            result["valid"] = False
            result["messages"].append("HML=M vessels cannot participate in swaps")
            return result

        # LoTSA or restriction differences require planner
        if vessel_a.is_lotsa or vessel_b.is_lotsa:
            result["requires_planner"] = True
            result["messages"].append("LoTSA vessel: requires Planner evaluation")

        if vessel_a.hml_flag != vessel_b.hml_flag:
            result["requires_planner"] = True
            result["messages"].append("Different HML restrictions: requires Planner evaluation")

        return result

    def validate_tia(self, vessel: Vessel, new_date: date,
                      current_date: date) -> Dict:
        """Validate Transit In Advance request."""
        result = {"valid": True, "messages": [], "exempt_from_fee": False}

        # New date must be earlier
        if new_date >= current_date:
            result["valid"] = False
            result["messages"].append("TIA date must be earlier than current transit date")
            return result

        # LoTSA vessels are exempt from TIA charges
        if vessel.is_lotsa:
            result["exempt_from_fee"] = True
            result["messages"].append("LoTSA vessel: exempt from TIA charges")

        return result

    def validate_last_minute(self, vessel: Vessel, customer_id: str,
                              transit_date: date) -> Dict:
        """Validate Last-Minute request eligibility."""
        result = {"valid": True, "messages": []}

        # Passenger vessels excluded
        if vessel.segment == VesselSegment.PASSENGER:
            result["valid"] = False
            result["messages"].append("Passenger vessels are excluded from Last-Minute service")
            return result

        # Check 7-day unsuccessful attempt rule
        seven_days_ago = date.today() - timedelta(days=7)
        recent_bookings = self.db.query(Reservation).filter(
            Reservation.customer_id == customer_id,
            Reservation.status == ReservationStatus.BOOKED,
            Reservation.created_at >= seven_days_ago
        ).count()

        if recent_bookings > 0:
            result["valid"] = False
            result["messages"].append(
                "Customer has a successful reservation in the past 7 days"
            )

        return result

    def validate_daylight_transit(self, vessel: Vessel) -> Dict:
        """Validate daylight transit eligibility."""
        result = {"valid": True, "messages": []}

        # Only vessels with appropriate HML flags
        if vessel.hml_flag == HMLFlag.NONE:
            result["valid"] = False
            result["messages"].append(
                "Vessel does not have HML restrictions requiring daylight transit"
            )

        return result

    def get_cancellation_penalty_rate(self, days_before_transit: int,
                                       origin: str) -> float:
        """Calculate cancellation penalty percentage based on days before transit."""
        if origin == "last_minute":
            return 1.0  # 100% — no cancellations allowed

        if days_before_transit <= 2:
            return 1.0   # 100%
        elif days_before_transit <= 4:
            return 1.0   # 100% in Period 3
        elif days_before_transit <= 7:
            return 0.80  # 80%
        elif days_before_transit <= 14:
            return 0.60  # 60%
        elif days_before_transit <= 30:
            return 0.40  # 40%
        else:
            return 0.20  # 20%

    def validate_conditioned_slot(self, vessel: Vessel, slot: Slot) -> Dict:
        """Validate if a vessel can use a conditioned Period 2 slot."""
        result = {"valid": True, "messages": []}

        if not slot.is_conditioned:
            return result

        # Only HML=C with dimensional limits
        if vessel.hml_flag != HMLFlag.C:
            result["valid"] = False
            result["messages"].append(
                "Conditioned slot only available for HML=C vessels"
            )

        return result
