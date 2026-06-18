import logging
from datetime import datetime
from typing import Any, Dict, Optional

from database import DatabaseConnection
from exceptions import DatabaseException, TransactionNotFoundException
from models import RiskProfile, Transaction
from repositories import (
    TransactionRepository,
    RuleExecutionLogRepository,
    RiskProfileRepository,
    CustomerRepository
)
from engines.risk_calculator import RiskCalculator

logger = logging.getLogger("finguard.services.risk_score_service")


class RiskScoreService:
    """
    Orchestrating service coordinating transaction logs fetches, risk score calculations,
    and updates to customer risk profiles in MySQL.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.tx_repo = TransactionRepository()
        self.rule_log_repo = RuleExecutionLogRepository()
        self.risk_profile_repo = RiskProfileRepository()
        self.customer_repo = CustomerRepository()

    def calculate_transaction_risk(
        self,
        transaction_id: int,
        method: str = "SUM"
    ) -> Dict[str, Any]:
        """
        Retrieves rules execution logs, aggregates risk score, calculates data confidence,
        determines risk level tier, and saves customer profile update in MySQL.
        
        Args:
            transaction_id: The ID of the transaction to calculate risk for.
            method: Score aggregation method ("SUM", "MAX", or "WEIGHTED").
            
        Returns:
            A dictionary containing:
            - risk_score
            - risk_level
            - confidence_percentage
            
        Raises:
            TransactionNotFoundException: If transaction is missing.
            DatabaseException: On SQL operation failures.
        """
        logger.info(f"Initiating risk calculation orchestration for transaction ID {transaction_id} using {method} method")

        try:
            # 1. Fetch transaction details
            transaction = self.tx_repo.find_by_id(transaction_id)
            if not transaction:
                raise TransactionNotFoundException(f"Transaction with ID {transaction_id} not found.")

            # 2. Query rule execution logs for triggered rules
            triggered_logs = self.rule_log_repo.search({
                "transaction_id": transaction_id,
                "triggered": True
            })

            # Map logs to standard rule dictionary format for RiskCalculator
            triggered_rules_data = []
            for log in triggered_logs:
                # Query the rule details (for severity) using rule_id
                rule_row = self.db.fetch_one("SELECT rule_name, severity FROM fraud_rules WHERE rule_id = %s", (log.rule_id,))
                severity = rule_row["severity"] if rule_row else "MEDIUM"
                triggered_rules_data.append({
                    "rule_id": log.rule_id,
                    "risk_points": log.risk_score_awarded,
                    "severity": severity
                })

            # 3. Query historical count of APPROVED transactions for the customer to establish baseline volume
            history_query = "SELECT COUNT(*) as cnt FROM transactions WHERE customer_id = %s AND transaction_id != %s AND status = 'APPROVED'"
            history_row = self.db.fetch_one(history_query, (transaction.customer_id, transaction_id))
            history_count = history_row["cnt"] if history_row else 0

            # 4. Perform calculations using RiskCalculator
            risk_score = RiskCalculator.calculate_score(triggered_rules_data, method=method)
            risk_level = RiskCalculator.determine_risk_level(risk_score)
            confidence = RiskCalculator.calculate_confidence(transaction, history_count)

            # 5. Persist/update customer risk profile in database
            # Search if risk profile already exists for this customer
            existing_profiles = self.risk_profile_repo.search({"customer_id": transaction.customer_id})
            
            # Since the database chk_risk_profile_score constraint caps score between 0 and 100,
            # we must cap the persisted score at 100, while still returning the uncapped score to the caller.
            persisted_score = min(risk_score, 100)

            if existing_profiles:
                profile = existing_profiles[0]
                profile.current_risk_score = persisted_score
                profile.risk_tier = risk_level
                profile.last_evaluated_at = datetime.now()
                self.risk_profile_repo.update(profile)
                logger.info(f"Updated existing risk profile ID {profile.profile_id} for customer {transaction.customer_id}")
            else:
                profile = RiskProfile(
                    profile_id=None,
                    customer_id=transaction.customer_id,
                    current_risk_score=persisted_score,
                    risk_tier=risk_level,
                    last_evaluated_at=datetime.now()
                )
                self.risk_profile_repo.create(profile)
                logger.info(f"Created new risk profile for customer {transaction.customer_id}")

            self.db.commit()

            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "confidence_percentage": confidence
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to calculate and update risk for transaction ID {transaction_id}: {e}", exc_info=True)
            if isinstance(e, TransactionNotFoundException):
                raise
            raise DatabaseException(f"Failed to calculate transaction risk: {e}")
