"""
Pricing Service
Handles all price calculations for slots, fees, penalties, and charges.
"""
from typing import Dict

# Base prices by category and period
BASE_PRICES = {
    "neopanamax": {"standard": 100000, "period_3": 100000, "high_demand": 110000},
    "supers": {"standard": 50000, "period_3": 55000},
    "regular": {"standard": 12000, "period_3": 15000},
}

# Fee rates
SUBSTITUTION_RATE = 0.60  # 60% of booking fee
SWAP_RATE = 0.01          # 1% of booking fee

class PricingService:
    def get_base_price(self, category: str, period: str = "standard",
                       is_high_demand: bool = False) -> int:
        prices = BASE_PRICES.get(category, BASE_PRICES["regular"])

        if period == "period_3":
            if is_high_demand and category == "neopanamax":
                return prices.get("high_demand", prices["period_3"])
            return prices["period_3"]

        return prices["standard"]

    def calculate_substitution_fee(self, booking_fee: int) -> int:
        return int(booking_fee * SUBSTITUTION_RATE)

    def calculate_swap_fee(self, booking_fee: int) -> int:
        return int(booking_fee * SWAP_RATE)

    def calculate_cancellation_penalty(self, booking_fee: int, penalty_rate: float) -> int:
        return int(booking_fee * penalty_rate)

    def calculate_tia_fee(self, category: str, is_lotsa: bool = False) -> int:
        if is_lotsa:
            return 0  # LoTSA vessels exempt
        fees = {"neopanamax": 25000, "supers": 15000, "regular": 5000}
        return fees.get(category, 5000)

    def calculate_last_minute_fee(self, category: str) -> int:
        fees = {"neopanamax": 50000, "supers": 30000, "regular": 10000}
        return fees.get(category, 10000)

    def calculate_sdtr_penalty(self, category: str) -> int:
        penalties = {"neopanamax": 30000, "supers": 20000, "regular": 8000}
        return penalties.get(category, 8000)

    def calculate_daylight_transit_fee(self, category: str) -> int:
        fees = {"neopanamax": 15000, "supers": 10000, "regular": 3000}
        return fees.get(category, 3000)

    def get_price_breakdown(self, category: str, period: str,
                            is_high_demand: bool = False) -> Dict:
        base = self.get_base_price(category, period, is_high_demand)
        return {
            "base_price": base,
            "substitution_fee": self.calculate_substitution_fee(base),
            "swap_fee": self.calculate_swap_fee(base),
            "tia_fee": self.calculate_tia_fee(category),
            "last_minute_fee": self.calculate_last_minute_fee(category),
            "sdtr_penalty": self.calculate_sdtr_penalty(category),
            "daylight_fee": self.calculate_daylight_transit_fee(category),
        }
