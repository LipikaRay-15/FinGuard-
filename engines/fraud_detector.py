import math
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from database import DatabaseConnection
from models import Transaction, FraudRule
from engines.rule_evaluator import RuleEvaluator

logger = logging.getLogger("finguard.engines.fraud_detector")


class FraudDetectionStrategy(ABC):
    """
    Abstract Base Class for all fraud detection strategies.
    Conforms to the Strategy Pattern.
    """
    @abstractmethod
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        """
        Evaluates the transaction against the specific fraud logic.
        
        Returns:
            A tuple of (triggered, risk_points, severity, reason)
        """
        pass


class HighAmountStrategy(FraudDetectionStrategy):
    """
    Flags transactions exceeding the high amount threshold.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        amount = float(transaction.amount)
        triggered = RuleEvaluator.evaluate(amount, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: transaction amount (${amount:,.2f}) {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class VelocityFraudStrategy(FraudDetectionStrategy):
    """
    Flags high frequency/volume of transactions in a brief window.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_time = transaction.transaction_time or datetime.now()
        tx_id = transaction.transaction_id or 0
        
        # Count transactions for the customer in the last 1 hour
        query = """
            SELECT COUNT(*) as cnt 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_time >= DATE_SUB(%s, INTERVAL 1 HOUR) 
              AND transaction_id != %s 
              AND status != 'DECLINED'
        """
        row = db.fetch_one(query, (transaction.customer_id, tx_time, tx_id))
        count = row["cnt"] if row else 0
        
        triggered = RuleEvaluator.evaluate(count, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: customer velocity ({count} transactions in last hour) {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class NightTransactionStrategy(FraudDetectionStrategy):
    """
    Flags transactions occurring during unusual late-night hours.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_time = transaction.transaction_time or datetime.now()
        hour = tx_time.hour
        
        # If threshold specifies night hours using in/between, check it
        triggered = False
        try:
            # Special case for "between" with night wrap-around e.g., "22,6"
            if rule_config.operator.strip().lower() == "between":
                parts = rule_config.threshold.split(",")
                if len(parts) == 2:
                    low = int(parts[0])
                    high = int(parts[1])
                    if low > high:  # wrap-around night hours
                        triggered = (hour >= low or hour <= high)
                    else:
                        triggered = (low <= hour <= high)
            else:
                triggered = RuleEvaluator.evaluate(hour, rule_config.operator, rule_config.threshold)
        except Exception as e:
            logger.warning(f"Error parsing threshold '{rule_config.threshold}' in NightTransactionStrategy: {e}")
            
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: transaction time ({hour:02d}:00) matches night hours {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class NewDeviceStrategy(FraudDetectionStrategy):
    """
    Flags transactions originating from a device fingerprint never used by the customer.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        if not transaction.device_id:
            return False, 0, rule_config.severity, ""
            
        tx_id = transaction.transaction_id or 0
        
        # Check if there are past successful transactions with this device
        query = """
            SELECT COUNT(*) as cnt 
            FROM transactions 
            WHERE customer_id = %s 
              AND device_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED'
        """
        row = db.fetch_one(query, (transaction.customer_id, transaction.device_id, tx_id))
        count = row["cnt"] if row else 0
        
        # If device has never been seen in past transactions for this customer
        triggered = (count == 0)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: device ID {transaction.device_id} is new for this customer [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class DifferentCityStrategy(FraudDetectionStrategy):
    """
    Flags transactions originating from a city different from previous transactions.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        if transaction.location_latitude is None or transaction.location_longitude is None:
            return False, 0, rule_config.severity, ""
            
        tx_id = transaction.transaction_id or 0
        curr_lat = float(transaction.location_latitude)
        curr_lon = float(transaction.location_longitude)
        
        # Fetch coordinates of last 10 successful transactions
        query = """
            SELECT location_latitude, location_longitude 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED' 
              AND location_latitude IS NOT NULL 
              AND location_longitude IS NOT NULL
            ORDER BY transaction_time DESC 
            LIMIT 10
        """
        rows = db.fetch_all(query, (transaction.customer_id, tx_id))
        
        if not rows:
            # First successful transaction, cannot be "different"
            return False, 0, rule_config.severity, ""
            
        # Match against past locations (tolerance of 0.01 degrees ~ 1km)
        match_found = False
        for r in rows:
            past_lat = float(r["location_latitude"])
            past_lon = float(r["location_longitude"])
            if abs(curr_lat - past_lat) < 0.01 and abs(curr_lon - past_lon) < 0.01:
                match_found = True
                break
                
        triggered = not match_found
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: location coordinates ({curr_lat:.4f}, {curr_lon:.4f}) have not been used in recent transactions [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class DormantAccountStrategy(FraudDetectionStrategy):
    """
    Flags transactions on accounts that have been inactive for an extended period.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_time = transaction.transaction_time or datetime.now()
        tx_id = transaction.transaction_id or 0
        
        query = """
            SELECT MAX(transaction_time) as last_time 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED'
        """
        row = db.fetch_one(query, (transaction.customer_id, tx_id))
        
        if not row or row["last_time"] is None:
            # New account or no successful transaction yet
            return False, 0, rule_config.severity, ""
            
        last_time = row["last_time"]
        
        # If the last transaction is returned as string, parse it
        if isinstance(last_time, str):
            try:
                last_time = datetime.fromisoformat(last_time)
            except ValueError:
                pass
                
        days_inactive = (tx_time - last_time).days
        
        triggered = RuleEvaluator.evaluate(days_inactive, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: account was inactive for {days_inactive} days (dormancy threshold: {rule_config.threshold}) [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class MerchantRiskStrategy(FraudDetectionStrategy):
    """
    Flags transactions processed at high-risk merchants or categories.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        if not transaction.merchant_id:
            return False, 0, rule_config.severity, ""
            
        query = """
            SELECT trust_score, risk_level, merchant_category_code 
            FROM merchant_profiles 
            WHERE merchant_id = %s
        """
        row = db.fetch_one(query, (transaction.merchant_id,))
        if not row:
            return False, 0, rule_config.severity, ""
            
        trust_score = row["trust_score"]
        risk_level = row["risk_level"]
        mcc = row["merchant_category_code"]
        
        # Evaluate based on database rule configuration
        triggered = False
        val_to_check = None
        
        if rule_config.field_name == "mcc":
            val_to_check = mcc
        elif rule_config.field_name == "merchant_risk" or rule_config.field_name == "trust_score":
            val_to_check = trust_score
        else:
            # Default to trust score
            val_to_check = trust_score
            
        triggered = RuleEvaluator.evaluate(val_to_check, rule_config.operator, rule_config.threshold)
        
        # Also auto-trigger if explicitly high-risk tier
        if risk_level == "HIGH" and not triggered:
            triggered = True
            
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: high-risk merchant Category Code (mcc: {mcc}, risk level: {risk_level}, trust score: {trust_score}) [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class FailedAttemptsStrategy(FraudDetectionStrategy):
    """
    Flags multiple declined transactions in quick succession.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_time = transaction.transaction_time or datetime.now()
        tx_id = transaction.transaction_id or 0
        
        # Count DECLINED transactions in the last hour
        query = """
            SELECT COUNT(*) as cnt 
            FROM transactions 
            WHERE customer_id = %s 
              AND status = 'DECLINED' 
              AND transaction_time >= DATE_SUB(%s, INTERVAL 1 HOUR) 
              AND transaction_id != %s
        """
        row = db.fetch_one(query, (transaction.customer_id, tx_time, tx_id))
        count = row["cnt"] if row else 0
        
        triggered = RuleEvaluator.evaluate(count, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: customer had {count} declined transactions in last hour {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class AmountDeviationStrategy(FraudDetectionStrategy):
    """
    Flags transactions significantly larger than historical average transaction amounts.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_id = transaction.transaction_id or 0
        amount = float(transaction.amount)
        
        # Calculate historical stats for approved transactions
        query = """
            SELECT AVG(amount) as avg_amt, STDDEV(amount) as std_amt 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED'
        """
        row = db.fetch_one(query, (transaction.customer_id, tx_id))
        
        if not row or row["avg_amt"] is None:
            # Not enough history
            return False, 0, rule_config.severity, ""
            
        avg_amt = float(row["avg_amt"])
        std_amt = float(row["std_amt"]) if row["std_amt"] is not None else 0.0
        
        if avg_amt == 0:
            return False, 0, rule_config.severity, ""
            
        # Standard deviation fallback if too small
        if std_amt == 0:
            std_amt = avg_amt * 0.2
            
        deviation = (amount - avg_amt) / std_amt
        
        # Check standard deviation threshold
        triggered = RuleEvaluator.evaluate(deviation, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: transaction amount (${amount:,.2f}) deviates from historical average (${avg_amt:,.2f}) by {deviation:.2f} standard deviations {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class LocationJumpStrategy(FraudDetectionStrategy):
    """
    Flags velocity anomalies where sequential transactions are physically too far apart to be travel-realistic.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        if transaction.location_latitude is None or transaction.location_longitude is None:
            return False, 0, rule_config.severity, ""
            
        tx_time = transaction.transaction_time or datetime.now()
        tx_id = transaction.transaction_id or 0
        curr_lat = float(transaction.location_latitude)
        curr_lon = float(transaction.location_longitude)
        
        # Fetch the most recent successful transaction
        query = """
            SELECT location_latitude, location_longitude, transaction_time 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND location_latitude IS NOT NULL 
              AND location_longitude IS NOT NULL
              AND status = 'APPROVED'
            ORDER BY transaction_time DESC 
            LIMIT 1
        """
        row = db.fetch_one(query, (transaction.customer_id, tx_id))
        
        if not row:
            return False, 0, rule_config.severity, ""
            
        past_lat = float(row["location_latitude"])
        past_lon = float(row["location_longitude"])
        past_time = row["transaction_time"]
        
        if isinstance(past_time, str):
            try:
                past_time = datetime.fromisoformat(past_time)
            except ValueError:
                pass
                
        # Haversine distance
        d_lat = math.radians(past_lat - curr_lat)
        d_lon = math.radians(past_lon - curr_lon)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(curr_lat)) * math.cos(math.radians(past_lat)) *
             math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = 6371.0 * c
        
        # Time difference in hours
        time_diff_hours = (tx_time - past_time).total_seconds() / 3600.0
        
        if time_diff_hours <= 0:
            time_diff_hours = 0.01  # Prevent division by zero
            
        speed_kmh = distance_km / time_diff_hours
        
        triggered = RuleEvaluator.evaluate(speed_kmh, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: impossible travel speed between sequential transactions ({speed_kmh:.1f} km/h over {distance_km:.1f} km) {rule_config.operator} {rule_config.threshold} km/h [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class UnusualFrequencyStrategy(FraudDetectionStrategy):
    """
    Flags anomalous activity compared to customer's historical daily transaction frequency.
    """
    def evaluate(
        self,
        transaction: Transaction,
        db: DatabaseConnection,
        rule_config: FraudRule
    ) -> Tuple[bool, int, str, str]:
        tx_time = transaction.transaction_time or datetime.now()
        tx_id = transaction.transaction_id or 0
        
        # 1. Count transactions in the last 24 hours
        query_24h = """
            SELECT COUNT(*) as cnt_24h 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_time >= DATE_SUB(%s, INTERVAL 24 HOUR) 
              AND transaction_id != %s
              AND status != 'DECLINED'
        """
        row_24h = db.fetch_one(query_24h, (transaction.customer_id, tx_time, tx_id))
        count_24h = row_24h["cnt_24h"] if row_24h else 0
        
        # 2. Get customer transaction timeline history
        query_hist = """
            SELECT COUNT(*) as total_count, MIN(transaction_time) as first_time, MAX(transaction_time) as last_time 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED'
        """
        row_hist = db.fetch_one(query_hist, (transaction.customer_id, tx_id))
        
        if not row_hist or row_hist["total_count"] < 5:
            # Insufficient history to establish baseline frequency
            return False, 0, rule_config.severity, ""
            
        total_count = row_hist["total_count"]
        first_time = row_hist["first_time"]
        last_time = row_hist["last_time"]
        
        if isinstance(first_time, str):
            first_time = datetime.fromisoformat(first_time)
        if isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)
            
        days_span = (last_time - first_time).days
        if days_span < 1:
            days_span = 1
            
        historic_daily_freq = total_count / days_span
        if historic_daily_freq <= 0:
            historic_daily_freq = 1.0
            
        # Frequency ratio: 24h count compared to historic daily frequency
        ratio = count_24h / historic_daily_freq
        
        triggered = RuleEvaluator.evaluate(ratio, rule_config.operator, rule_config.threshold)
        
        reason = ""
        if triggered:
            reason = f"Rule '{rule_config.rule_name}' triggered: transaction frequency in last 24 hours ({count_24h}) is {ratio:.1f}x higher than historical daily average ({historic_daily_freq:.2f}) {rule_config.operator} {rule_config.threshold} [Points: {rule_config.risk_points}]"
            
        return triggered, rule_config.risk_points, rule_config.severity, reason


class FraudDetector:
    """
    Orchestrates the Strategy Pattern execution for active fraud rules.
    Compiles scores, severities, matching rules, and diagnostics.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.severity_ranks = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4
        }
        
        # Register strategies mapped to database rule names
        self._strategies: Dict[str, FraudDetectionStrategy] = {
            "High Transaction Amount": HighAmountStrategy(),
            "Rapid Velocity Limit": VelocityFraudStrategy(),
            "Night Transaction": NightTransactionStrategy(),
            "New Device": NewDeviceStrategy(),
            "Different City": DifferentCityStrategy(),
            "Dormant Account": DormantAccountStrategy(),
            "High-Risk Merchant Category": MerchantRiskStrategy(),
            "Failed Attempts": FailedAttemptsStrategy(),
            "Amount Deviation": AmountDeviationStrategy(),
            "Location Jump": LocationJumpStrategy(),
            "Unusual Frequency": UnusualFrequencyStrategy(),
        }

    def evaluate_transaction(
        self,
        transaction: Transaction,
        rules: List[FraudRule]
    ) -> Tuple[List[Dict[str, Any]], int, str, List[str]]:
        """
        Runs registered strategies against the transaction.
        
        Args:
            transaction: Transaction domain model.
            rules: List of active FraudRule objects fetched from the database.
            
        Returns:
            A tuple of (triggered_rules, risk_score, severity, reasons)
        """
        triggered_rules = []
        reasons = []
        
        # Sort rules by priority order (ascending) to maintain stop execution constraints
        sorted_rules = sorted(rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
                
            strategy = self._strategies.get(rule.rule_name)
            if not strategy:
                logger.warning(f"No concrete strategy registered for rule name '{rule.rule_name}'. Skipping evaluation.")
                continue
                
            try:
                matched, points, severity, reason = strategy.evaluate(transaction, self.db, rule)
                if matched:
                    triggered_rules.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.rule_name,
                        "risk_points": points,
                        "severity": severity,
                        "reason": reason
                    })
                    reasons.append(reason)
                    
                    if rule.stop_execution:
                        logger.info(f"Stop execution marker hit on rule '{rule.rule_name}'. Halting further strategies.")
                        reasons.append(f"Scan halted by rule '{rule.rule_name}' (stop_execution=True).")
                        break
            except Exception as e:
                logger.error(f"Error executing strategy for rule '{rule.rule_name}': {e}", exc_info=True)
                
        # Aggregate score, calculate severity, and compile triggered list
        risk_score = self.calculate_risk_score(triggered_rules)
        severity = self.calculate_severity(triggered_rules)
        triggered_list = self.get_triggered_rules(triggered_rules)
        reasons_list = self.generate_reasons(triggered_rules)
        
        return triggered_list, risk_score, severity, reasons_list

    def calculate_risk_score(self, triggered_rules: List[Dict[str, Any]]) -> int:
        """
        Sums up the risk points of triggered rules. Risk score is capped at 100.
        """
        total = sum(r["risk_points"] for r in triggered_rules)
        return min(total, 100)

    def calculate_severity(self, triggered_rules: List[Dict[str, Any]]) -> str:
        """
        Finds the highest severity among all triggered rules. Defaults to LOW.
        """
        highest_sev = "LOW"
        for r in triggered_rules:
            sev = r["severity"].upper() if r.get("severity") else "LOW"
            if self.severity_ranks.get(sev, 1) > self.severity_ranks.get(highest_sev, 1):
                highest_sev = sev
        return highest_sev

    def get_triggered_rules(self, all_evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extracts structural definitions of triggered rules.
        """
        return [{
            "rule_id": r["rule_id"],
            "rule_name": r["rule_name"],
            "risk_points": r["risk_points"],
            "severity": r["severity"],
            "reason": r.get("reason", "")
        } for r in all_evaluations]

    def generate_reasons(self, all_evaluations: List[Dict[str, Any]]) -> List[str]:
        """
        Compiles the descriptive reasons explaining fraud triggers.
        """
        return [r["reason"] for r in all_evaluations if r.get("reason")]
