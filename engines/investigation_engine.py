import logging
from datetime import datetime
from typing import Any, Dict, List, Union
from collections import Counter

logger = logging.getLogger("finguard.engines.investigation_engine")

CITY_COORDINATES = {
    "NEW YORK": (40.7128, -74.0060),
    "LONDON": (51.5074, -0.1278),
    "LAS VEGAS": (36.1716, -115.1398),
    "PARIS": (48.8566, 2.3522),
    "TOKYO": (35.6762, 139.6503),
    "MUMBAI": (19.0760, 72.8777),
}

RULE_TIMELINE_MAP = {
    "High Transaction Amount": "High Amount Rule",
    "Rapid Velocity Limit": "Velocity Fraud",
    "New Device": "New Device",
    "Night Transaction": "Night Transaction",
    "Different City": "Different City",
    "Dormant Account": "Dormant Account",
    "High-Risk Merchant Category": "High-Risk Merchant Category",
    "Failed Attempts": "Failed Attempts",
    "Amount Deviation": "Amount Deviation",
    "Location Jump": "Location Jump",
    "Unusual Frequency": "Unusual Frequency"
}

class InvestigationEngine:
    """
    Pure logical engine that gathers raw customer activity metrics
    and formats analyst-facing timelines and behavioral summaries.
    """
    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def calculate_trust_score(self, risk_score: int) -> int:
        """
        Computes trust score: trust scale drops as risk level increases.
        """
        return max(0, 100 - risk_score)

    def find_most_frequent_city(self, transactions: List[Union[Dict[str, Any], Any]]) -> str:
        """
        Reverse-resolves coordinate points back to city names and gets the mode.
        """
        cities = []
        for tx in transactions:
            lat = self._get_val(tx, "location_latitude")
            lon = self._get_val(tx, "location_longitude")
            if lat is not None and lon is not None:
                lat_f = float(lat)
                lon_f = float(lon)
                matched_city = "Unknown City"
                for city, coords in CITY_COORDINATES.items():
                    if abs(lat_f - coords[0]) < 0.01 and abs(lon_f - coords[1]) < 0.01:
                        matched_city = city
                        break
                cities.append(matched_city)

        if not cities:
            return "Unknown"
        
        return Counter(cities).most_common(1)[0][0]

    def calculate_average_amount(self, transactions: List[Union[Dict[str, Any], Any]]) -> float:
        """
        Calculates average transaction volume amount.
        """
        if not transactions:
            return 0.0
        total = sum(float(self._get_val(tx, "amount") or 0.0) for tx in transactions)
        return round(total / len(transactions), 2)

    def count_fraud_attempts(self, transactions: List[Union[Dict[str, Any], Any]]) -> int:
        """
        Counts transaction declines as indicators of fraud attempts.
        """
        attempts = 0
        for tx in transactions:
            status = str(self._get_val(tx, "status")).upper()
            if status == "DECLINED":
                attempts += 1
        return attempts

    def generate_behaviour_summary(
        self,
        risk_level: str,
        avg_amount: float,
        city: str,
        fraud_attempts: int
    ) -> str:
        """
        Assembles a comprehensive dynamic narrative about the customer's transaction habits.
        """
        level_upper = str(risk_level).upper().strip()
        
        if fraud_attempts > 0:
            return (
                f"Anomalous customer behavior flagged with {fraud_attempts} declined transaction attempt(s). "
                f"Primarily operating in {city} with average transactions of ${avg_amount:,.2f}. "
                f"Subject profile shows CRITICAL risk warnings."
            )
        elif level_upper in ("HIGH", "CRITICAL"):
            return (
                f"Highly suspicious activities flagged. Customer has a {level_upper} risk rating. "
                f"Main location profile matches {city} with average transaction amount of ${avg_amount:,.2f}. "
                f"Immediate manual analyst monitoring requested."
            )
        else:
            return (
                f"Consistent spending profile. Transactions processed primarily in {city} "
                f"with average size of ${avg_amount:,.2f}. Customer risk rating is {level_upper}."
            )

    def format_timeline_event(self, event_type: str, entity_id: str, details: dict, created_at: datetime) -> str:
        """
        Compiles timeline entries dynamically: e.g. "11:00 PM Transaction Created"
        """
        # Format time with replaced leading 0 for single-digit hours to match "11:00 PM" style
        time_str = created_at.strftime("%I:%M %p")
        if time_str.startswith("0"):
            time_str = time_str[1:]

        ev_upper = event_type.upper().strip()

        if ev_upper == "TRANSACTION_CREATED":
            return f"{time_str} Transaction Created"
        elif ev_upper == "TRANSACTION_FAILED":
            return f"{time_str} Transaction Failed"
        elif ev_upper == "RULE_TRIGGERED":
            rule_name = entity_id or (details.get("rule_name") if details else "Unknown Rule")
            display_name = RULE_TIMELINE_MAP.get(rule_name, rule_name)
            if not display_name.endswith("Triggered") and not display_name.endswith("Rule"):
                display_name = f"{display_name} Rule"
            return f"{time_str} {display_name} Triggered"
        elif ev_upper == "ALERT_GENERATED":
            return f"{time_str} Alert Generated"
        elif ev_upper == "CASE_CREATED":
            return f"{time_str} Case Created"
        elif ev_upper == "CASE_UPDATED":
            return f"{time_str} Analyst Updated Case"
        elif ev_upper == "CASE_CLOSED":
            return f"{time_str} Case Closed"
        elif ev_upper == "CUSTOMER_BLACKLISTED":
            return f"{time_str} Customer Blacklisted"
        elif ev_upper == "DEVICE_BLACKLISTED":
            return f"{time_str} Device Blacklisted"
        elif ev_upper == "PAN_BLOCKED":
            return f"{time_str} PAN Blocked"
        elif ev_upper == "ACCOUNT_BLOCKED":
            return f"{time_str} Account Blocked"
        elif ev_upper == "CUSTOMER_WHITELISTED":
            return f"{time_str} Customer Whitelisted"
        elif ev_upper == "DEVICE_WHITELISTED":
            return f"{time_str} Device Whitelisted"
        else:
            # Fallback format if type is custom or unmapped
            action = ev_upper.replace("_", " ").title()
            return f"{time_str} {action}"
