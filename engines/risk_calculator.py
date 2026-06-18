import logging
from typing import Any, Dict, List
from models import Transaction

logger = logging.getLogger("finguard.engines.risk_calculator")


class RiskCalculator:
    """
    Computes transactional risk scores, maps score bands to risk levels,
    and calculates data confidence percentages based on historical transaction profiles.
    """

    @staticmethod
    def calculate_score(triggered_rules: List[Dict[str, Any]], method: str = "SUM") -> int:
        """
        Aggregates risk points from multiple triggered rules.
        
        Args:
            triggered_rules: List of dictionaries of triggered rules containing 'risk_points' and 'severity'.
            method: The aggregation method ("SUM", "MAX", or "WEIGHTED").
            
        Returns:
            The aggregated risk score (integer).
        """
        if not triggered_rules:
            return 0

        method_upper = method.strip().upper()
        
        if method_upper == "MAX":
            score = max(int(r.get("risk_points", 0)) for r in triggered_rules)
            logger.debug(f"Risk calculation using MAX: {score}")
            return score
            
        elif method_upper == "WEIGHTED":
            # Weight multiplier based on severity of rules
            severity_weights = {
                "CRITICAL": 1.0,
                "HIGH": 0.8,
                "MEDIUM": 0.5,
                "LOW": 0.2
            }
            weighted_sum = 0.0
            for r in triggered_rules:
                points = float(r.get("risk_points", 0))
                sev = str(r.get("severity", "MEDIUM")).upper()
                weight = severity_weights.get(sev, 0.5)
                weighted_sum += points * weight
                
            score = int(round(weighted_sum))
            logger.debug(f"Risk calculation using WEIGHTED: {score} (weighted sum: {weighted_sum:.2f})")
            return score
            
        else:  # Default to "SUM"
            # Uncapped sum of risk points, allowing representation of critical triggers (100+)
            score = sum(int(r.get("risk_points", 0)) for r in triggered_rules)
            logger.debug(f"Risk calculation using SUM: {score}")
            return score

    @staticmethod
    def calculate_confidence(transaction: Transaction, history_count: int) -> float:
        """
        Calculates the data confidence percentage of the risk evaluation.
        
        Args:
            transaction: Current transaction domain model.
            history_count: Number of historical transactions processed for this customer.
            
        Returns:
            A confidence percentage between 30.0% and 100.0%.
        """
        confidence = 100.0

        # 1. Profile completeness checks (missing crucial descriptors reduce confidence)
        if not transaction.device_id:
            confidence -= 15.0
            logger.debug("Confidence penalty: Missing device profile metadata (-15%)")
            
        if transaction.location_latitude is None or transaction.location_longitude is None:
            confidence -= 15.0
            logger.debug("Confidence penalty: Missing location coordinates (-15%)")
            
        if not transaction.merchant_id:
            confidence -= 10.0
            logger.debug("Confidence penalty: Missing merchant profile metadata (-10%)")

        # 2. Historical profile volume checks (smaller baselines reduce confidence)
        if history_count == 0:
            confidence -= 30.0
            logger.debug("Confidence penalty: Customer has no transaction history baseline (-30%)")
        elif history_count < 3:
            confidence -= 20.0
            logger.debug(f"Confidence penalty: Low volume customer profile (count: {history_count}) (-20%)")
        elif history_count < 10:
            confidence -= 10.0
            logger.debug(f"Confidence penalty: Moderate volume customer profile (count: {history_count}) (-10%)")

        # Ensure confidence fits between 30.0% (minimum floor) and 100.0% (maximum cap)
        final_confidence = max(30.0, min(confidence, 100.0))
        logger.debug(f"Final calculated confidence: {final_confidence}%")
        return final_confidence

    @staticmethod
    def determine_risk_level(score: int) -> str:
        """
        Maps the aggregated score to a categorical risk tier.
        
        Risk Levels:
            0-30     LOW
            31-60    MEDIUM
            61-99    HIGH
            100+     CRITICAL
        """
        if score >= 100:
            return "CRITICAL"
        elif score >= 61:
            return "HIGH"
        elif score >= 31:
            return "MEDIUM"
        else:
            return "LOW"
