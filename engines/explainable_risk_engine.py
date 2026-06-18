import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger("finguard.engines.explainable_risk_engine")

RULE_DISPLAY_MAP = {
    "High Transaction Amount": "High Amount detected",
    "Rapid Velocity Limit": "Velocity Fraud detected",
    "New Device": "New Device detected",
    "Night Transaction": "Night Transaction detected",
    "Different City": "Different City detected",
    "Dormant Account": "Dormant Account detected",
    "High-Risk Merchant Category": "High-Risk Merchant Category detected",
    "Failed Attempts": "Failed Attempts detected",
    "Amount Deviation": "Amount Deviation detected",
    "Location Jump": "Location Jump detected",
    "Unusual Frequency": "Unusual Frequency detected"
}

class ExplainableRiskEngine:
    """
    Decoupled pure logic engine responsible for formatting human-readable risk explanations
    and actions for fraud analysts. Follows SOLID principles and is database-independent.
    """

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        """Helper to get a value from either a dictionary or an object."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def generate_explanation(
        self,
        transaction_code: str,
        risk_score: int,
        risk_level: str,
        triggered_rules: List[Union[Dict[str, Any], Any]],
        severity: str,
        confidence: float
    ) -> str:
        """
        Assembles a complete, multi-line human-readable explanation string suitable for fraud analysts.
        
        Args:
            transaction_code: Formatted transaction reference code (e.g. TXN48291).
            risk_score: Aggregated risk points score.
            risk_level: Overall risk tier (LOW, MEDIUM, HIGH, CRITICAL).
            triggered_rules: List of dictionaries or log entities of triggered rules.
            severity: Highest rule severity.
            confidence: Data evaluation confidence percentage.
            
        Returns:
            A formatted multi-line string.
        """
        logger.debug(f"Generating risk explanation for transaction: {transaction_code}")
        
        if triggered_rules:
            rules_str = "\n".join(self.generate_reason_list(triggered_rules))
        else:
            rules_str = "No rules triggered"

        action = self.generate_recommended_action(risk_level)
        conf_rounded = int(round(confidence)) if abs(confidence - round(confidence)) < 0.001 else confidence

        explanation = (
            f"Transaction {transaction_code}\n"
            f"Risk Score: {risk_score}\n"
            f"Risk Level: {risk_level}\n"
            f"Triggered Rules:\n"
            f"{rules_str}\n"
            f"Severity:\n"
            f"{severity}\n"
            f"Confidence:\n"
            f"{conf_rounded}%\n"
            f"Recommended Action:\n"
            f"{action}"
        )
        return explanation

    def generate_recommended_action(self, risk_level: str) -> str:
        """
        Maps risk tiers to recommended analyst remediation actions.
        Supports: Low, Medium, High, Critical
        """
        level_upper = str(risk_level).strip().upper()
        if level_upper == "CRITICAL":
            return "Auto-Decline & Suspend Account"
        elif level_upper == "HIGH":
            return "Manual Review Required"
        elif level_upper == "MEDIUM":
            return "Manual Review Required"
        elif level_upper == "LOW":
            return "Auto-Approve"
        else:
            return "Manual Review Required"

    def generate_summary(
        self,
        transaction_code: str,
        risk_score: int,
        risk_level: str,
        severity: str,
        confidence: float
    ) -> str:
        """
        Generates a concise narrative overview summary of the risk status.
        """
        conf_rounded = int(round(confidence)) if abs(confidence - round(confidence)) < 0.001 else confidence
        return (
            f"Transaction {transaction_code} evaluated with a {risk_level} risk level "
            f"(Score: {risk_score}, Severity: {severity}, Confidence: {conf_rounded}%)."
        )

    def generate_reason_list(self, triggered_rules: List[Union[Dict[str, Any], Any]]) -> List[str]:
        """
        Formats rule execution lists with their custom descriptive names and points.
        """
        reasons = []
        for r in triggered_rules:
            rule_name = self._get_val(r, "rule_name") or "Unknown Rule"
            points = self._get_val(r, "risk_points") or self._get_val(r, "risk_score_awarded") or 0
            
            # Map standard rule names to display names, fallback to rule name with "detected" suffix
            display_name = RULE_DISPLAY_MAP.get(rule_name)
            if not display_name:
                display_name = rule_name
                if not display_name.lower().endswith("detected"):
                    display_name = f"{display_name} detected"

            reasons.append(f"✓ {display_name} (+{points})")
        return reasons
