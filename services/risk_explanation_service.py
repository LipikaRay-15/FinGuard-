import logging
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import TransactionNotFoundException
from repositories import TransactionRepository
from services.rule_execution_service import RuleExecutionService
from engines.risk_calculator import RiskCalculator
from engines.explainable_risk_engine import ExplainableRiskEngine

logger = logging.getLogger("finguard.services.risk_explanation_service")

class RiskExplanationService:
    """
    Orchestration service that reads transaction audits and rules execution logs
    to produce human-readable explanation summaries and recommendations.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.tx_repo = TransactionRepository()
        self.rule_exec_service = RuleExecutionService()
        self.explain_engine = ExplainableRiskEngine()

    def _get_transaction_details(self, transaction_id: int) -> Dict[str, Any]:
        """
        Helper method to fetch transaction, execution logs, and calculate risk metrics.
        """
        transaction = self.tx_repo.find_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundException(f"Transaction with ID {transaction_id} not found.")

        # Get rule execution history logs
        history = self.rule_exec_service.get_transaction_rule_history(transaction_id)
        
        # Filter for triggered rules
        triggered_rules = [log for log in history if log.triggered]
        
        # Map logs to standard format for RiskCalculator
        triggered_rules_data = []
        for log in triggered_rules:
            triggered_rules_data.append({
                "rule_id": log.rule_id,
                "rule_name": log.rule_name,
                "risk_points": log.risk_score_awarded,
                "severity": log.severity
            })

        # Calculate risk score
        risk_score = RiskCalculator.calculate_score(triggered_rules_data, method="SUM")
        risk_level = RiskCalculator.determine_risk_level(risk_score)
        
        # Determine highest severity
        severity = "LOW"
        severity_ranks = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        for r in triggered_rules_data:
            sev = r["severity"].upper()
            if severity_ranks.get(sev, 1) > severity_ranks.get(severity, 1):
                severity = sev

        # Calculate confidence
        history_query = """
            SELECT COUNT(*) as cnt 
            FROM transactions 
            WHERE customer_id = %s 
              AND transaction_id != %s 
              AND status = 'APPROVED'
        """
        history_row = self.db.fetch_one(history_query, (transaction.customer_id, transaction_id))
        history_count = history_row["cnt"] if history_row else 0
        confidence = RiskCalculator.calculate_confidence(transaction, history_count)

        return {
            "transaction_code": f"TXN{transaction_id}",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "triggered_rules": triggered_rules,
            "severity": severity,
            "confidence": confidence
        }

    def generate_explanation(self, transaction_id: int) -> str:
        """
        Retrieves the transaction, fetches logs, computes metrics, and generates a formatted explanation.
        """
        details = self._get_transaction_details(transaction_id)
        return self.explain_engine.generate_explanation(
            transaction_code=details["transaction_code"],
            risk_score=details["risk_score"],
            risk_level=details["risk_level"],
            triggered_rules=details["triggered_rules"],
            severity=details["severity"],
            confidence=details["confidence"]
        )

    def generate_recommended_action(self, risk_level: str) -> str:
        """
        Delegates recommendation matching to ExplainableRiskEngine.
        """
        return self.explain_engine.generate_recommended_action(risk_level)

    def generate_summary(self, transaction_id: int) -> str:
        """
        Fetches details and generates a concise overview narrative.
        """
        details = self._get_transaction_details(transaction_id)
        return self.explain_engine.generate_summary(
            transaction_code=details["transaction_code"],
            risk_score=details["risk_score"],
            risk_level=details["risk_level"],
            severity=details["severity"],
            confidence=details["confidence"]
        )

    def generate_reason_list(self, transaction_id: int) -> List[str]:
        """
        Fetches triggered rules logs and returns formatted reason string list.
        """
        details = self._get_transaction_details(transaction_id)
        return self.explain_engine.generate_reason_list(details["triggered_rules"])
