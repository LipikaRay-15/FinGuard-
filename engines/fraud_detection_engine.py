import logging
from typing import Any, Dict, List, Tuple

from database import DatabaseConnection
from exceptions import FraudDetectionException, TransactionNotFoundException
from models import Transaction, FraudRule, RuleExecutionLog
from repositories import TransactionRepository, RuleRepository, RuleExecutionLogRepository
from services.event_service import EventService
from engines.fraud_detector import FraudDetector

logger = logging.getLogger("finguard.engines.fraud_detection_engine")


class FraudDetectionEngine:
    """
    Main coordinator for the Fraud Detection scanning workflow.
    Validates transactions, computes parameters, coordinates strategies,
    records execution outcomes, and notifies the Event Store.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.tx_repo = TransactionRepository()
        self.rule_repo = RuleRepository()
        self.rule_log_repo = RuleExecutionLogRepository()
        self.event_service = EventService()
        self.detector = FraudDetector()
        
        # Self-healing check: seed defaults if missing
        self._seed_default_rules()

    def _seed_default_rules(self) -> None:
        """
        Validates that all required fraud rule entities are present in MySQL.
        Auto-seeds missing rules to enable fully database-driven operations.
        """
        defaults = [
            {
                "rule_name": "High Transaction Amount",
                "description": "Flags single transactions exceeding the max amount threshold.",
                "field_name": "amount",
                "operator": ">",
                "threshold": "10000.00",
                "risk_points": 75,
                "priority": 20,
                "severity": "HIGH",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Rapid Velocity Limit",
                "description": "Flags frequent transaction volumes over brief durations.",
                "field_name": "velocity",
                "operator": ">",
                "threshold": "3",
                "risk_points": 80,
                "priority": 10,
                "severity": "CRITICAL",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "High-Risk Merchant Category",
                "description": "Flags activities at merchants flagged with high-risk MCC codes.",
                "field_name": "mcc",
                "operator": "in",
                "threshold": "7995,5933,5967",
                "risk_points": 60,
                "priority": 30,
                "severity": "MEDIUM",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Night Transaction",
                "description": "Flags transactions processed during late night hours.",
                "field_name": "hour",
                "operator": "between",
                "threshold": "22,6",
                "risk_points": 40,
                "priority": 50,
                "severity": "MEDIUM",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "New Device",
                "description": "Flags transactions originating from a device fingerprint never used by the customer.",
                "field_name": "device_id",
                "operator": "=",
                "threshold": "1",
                "risk_points": 50,
                "priority": 40,
                "severity": "MEDIUM",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Different City",
                "description": "Flags transactions processed in locations outside customer's recent history.",
                "field_name": "location",
                "operator": "=",
                "threshold": "1",
                "risk_points": 45,
                "priority": 45,
                "severity": "MEDIUM",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Dormant Account",
                "description": "Flags sudden transactions on accounts with no activity for 90+ days.",
                "field_name": "days_inactive",
                "operator": ">",
                "threshold": "90",
                "risk_points": 60,
                "priority": 35,
                "severity": "HIGH",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Failed Attempts",
                "description": "Flags customers incurring multiple successive declined transactions.",
                "field_name": "failed_attempts",
                "operator": ">",
                "threshold": "2",
                "risk_points": 70,
                "priority": 15,
                "severity": "HIGH",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Amount Deviation",
                "description": "Flags transaction amounts exceeding normal historical standard deviations.",
                "field_name": "std_devs",
                "operator": ">",
                "threshold": "3.0",
                "risk_points": 65,
                "priority": 25,
                "severity": "HIGH",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Location Jump",
                "description": "Flags geographically impossible travel speed calculations.",
                "field_name": "speed_kmh",
                "operator": ">",
                "threshold": "500.0",
                "risk_points": 85,
                "priority": 5,
                "severity": "CRITICAL",
                "enabled": True,
                "stop_execution": False
            },
            {
                "rule_name": "Unusual Frequency",
                "description": "Flags volume multipliers exceeding normal daily averages.",
                "field_name": "frequency_ratio",
                "operator": ">",
                "threshold": "3.0",
                "risk_points": 55,
                "priority": 60,
                "severity": "MEDIUM",
                "enabled": True,
                "stop_execution": False
            }
        ]
        
        try:
            # Query existing rule names
            existing_rules = self.rule_repo.find_all()
            existing_names = {r.rule_name for r in existing_rules}
            
            for rule_dict in defaults:
                if rule_dict["rule_name"] not in existing_names:
                    logger.info(f"Self-Healing: Seeding missing rule '{rule_dict['rule_name']}' in MySQL database...")
                    new_rule = FraudRule(
                        rule_id=None,
                        rule_name=rule_dict["rule_name"],
                        description=rule_dict["description"],
                        field_name=rule_dict["field_name"],
                        operator=rule_dict["operator"],
                        threshold=rule_dict["threshold"],
                        risk_points=rule_dict["risk_points"],
                        priority=rule_dict["priority"],
                        severity=rule_dict["severity"],
                        enabled=rule_dict["enabled"],
                        stop_execution=rule_dict["stop_execution"]
                    )
                    self.rule_repo.create(new_rule)
                    
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed during self-healing database seeding: {e}", exc_info=True)

    def detect_fraud(self, transaction_id: int) -> Dict[str, Any]:
        """
        Scans a transaction, executes logic strategies, records outcomes,
        commits changes, and publishes notifications.
        
        Args:
            transaction_id: The ID of the transaction to evaluate.
            
        Returns:
            A structured dictionary containing:
            - transaction_id
            - risk_score
            - severity
            - triggered_rules
            - reasons
        """
        logger.info(f"Initiating fraud scan for Transaction ID {transaction_id}")
        
        try:
            # 1. Fetch transaction record
            transaction = self.tx_repo.find_by_id(transaction_id)
            if not transaction:
                raise TransactionNotFoundException(f"Transaction with ID {transaction_id} not found.")
                
            # 2. Get active fraud rules
            active_rules = self.rule_repo.search({"enabled": True})
            
            # 3. Evaluate strategies using detector
            triggered_rules, risk_score, severity, reasons = self.detector.evaluate_transaction(
                transaction, active_rules
            )
            
            # Create a lookup for triggered rules mapping rule_id -> points
            triggered_map = {r["rule_id"]: r["risk_points"] for r in triggered_rules}
            
            # 4. Log executions for all evaluated rules in database & notify events
            for rule in active_rules:
                is_triggered = rule.rule_id in triggered_map
                points_awarded = triggered_map[rule.rule_id] if is_triggered else 0
                
                # Persist to rule_execution_logs
                self.log_rule_execution(transaction_id, rule.rule_id, is_triggered, points_awarded)
                
                # Publish event if triggered
                if is_triggered:
                    matching_reason = next((r["reason"] for r in triggered_rules if r["rule_id"] == rule.rule_id), "")
                    self.event_service.create_event(
                        event_type="RULE_TRIGGERED",
                        entity_type="RULE",
                        entity_id=rule.rule_name,
                        details={
                            "transaction_id": transaction_id,
                            "risk_score_awarded": points_awarded,
                            "reason": matching_reason
                        }
                    )
            
            # 5. Update transaction decision status based on score
            old_status = transaction.status
            new_status = "DECLINED" if risk_score >= 80 else ("FLAGGED" if risk_score >= 50 else "APPROVED")
            
            if old_status != new_status:
                transaction.status = new_status
                self.tx_repo.update(transaction)
                logger.info(f"Updated Transaction {transaction_id} status from {old_status} to {new_status} (Score: {risk_score})")
                
            self.db.commit()
            
            # 6. Format return dictionary
            return {
                "transaction_id": transaction_id,
                "risk_score": risk_score,
                "severity": severity,
                "triggered_rules": triggered_rules,
                "reasons": reasons
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during fraud evaluation on tx {transaction_id}: {e}", exc_info=True)
            if isinstance(e, TransactionNotFoundException):
                raise
            raise FraudDetectionException(f"Fraud check failed: {e}")

    def log_rule_execution(
        self,
        transaction_id: int,
        rule_id: int,
        triggered: bool,
        risk_points: int
    ) -> None:
        """
        Creates and persists a RuleExecutionLog audit record.
        """
        try:
            log = RuleExecutionLog(
                execution_id=None,
                transaction_id=transaction_id,
                rule_id=rule_id,
                triggered=triggered,
                risk_score_awarded=risk_points
            )
            self.rule_log_repo.create(log)
            # Commit is managed by caller transaction context
        except Exception as e:
            logger.error(f"Failed to log rule {rule_id} execution for tx {transaction_id}: {e}", exc_info=True)
