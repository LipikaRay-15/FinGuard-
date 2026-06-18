from typing import Any, Dict, List, Tuple
import logging

from models import FraudRule
from engines.rule_evaluator import RuleEvaluator

class RuleExecutor:
    """
    Executes a sorted list of FraudRules against transaction data.
    Aggregates points, checks maximum severities, and respects stop_execution flags.
    """
    def __init__(self) -> None:
        self.logger = logging.getLogger("finguard.engines.rule_executor")
        # Priority mapping for severity ranks
        self.severity_ranks = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4
        }

    def execute(
        self,
        rules: List[FraudRule],
        transaction_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], int, str, List[str]]:
        """
        Executes active rules in priority order.
        
        Args:
            rules: Sorted list of FraudRule objects (sorted by priority).
            transaction_data: Dictionary representing transaction fields (amount, device, mcc, etc.).
            
        Returns:
            A tuple of:
                - triggered_rules: List of dictionaries of matching rules.
                - risk_points: Sum of risk points awarded by matched rules.
                - severity: Highest severity triggered (LOW, MEDIUM, HIGH, or CRITICAL).
                - reasons: Diagnostic list of strings indicating matching rules.
        """
        triggered_rules = []
        total_risk_points = 0
        highest_severity = "LOW"
        reasons = []

        for rule in rules:
            if not rule.enabled:
                continue

            field = rule.field_name
            val = transaction_data.get(field)
            
            self.logger.debug(f"Evaluating rule '{rule.rule_name}': {field} ({val}) {rule.operator} {rule.threshold}")
            
            try:
                matched = RuleEvaluator.evaluate(val, rule.operator, rule.threshold)
            except Exception as e:
                self.logger.warning(
                    f"Error evaluating rule '{rule.rule_name}' on transaction field '{field}' ({val}): {e}"
                )
                matched = False

            if matched:
                self.logger.info(f"Rule '{rule.rule_name}' triggered (Points: {rule.risk_points})")
                triggered_rules.append(rule.to_dict())
                total_risk_points += rule.risk_points
                reasons.append(
                    f"Rule '{rule.rule_name}' triggered: {field} ({val}) {rule.operator} {rule.threshold} "
                    f"[Points: {rule.risk_points}]"
                )

                # Track highest severity triggered
                sev = rule.severity.upper() if rule.severity else "LOW"
                if self.severity_ranks.get(sev, 1) > self.severity_ranks.get(highest_severity, 1):
                    highest_severity = sev

                # Check if stop_execution flag is raised
                if rule.stop_execution:
                    self.logger.info(f"Stop execution marker triggered by rule '{rule.rule_name}'. Halting further checks.")
                    reasons.append(f"Execution halted by rule '{rule.rule_name}' (stop_execution=True).")
                    break

        return triggered_rules, total_risk_points, highest_severity, reasons
