import logging
from typing import Any, Dict, List, Optional, Tuple

from database import DatabaseConnection
from exceptions import DatabaseException
from models import FraudRule
from repositories import RuleRepository
from engines.rule_executor import RuleExecutor

class RuleEngine:
    """
    Manager class orchestrating the dynamic database-driven rule engine pipeline.
    Loads active rules, handles runtime execution, and supports enabling/disabling rules dynamically.
    """
    def __init__(self) -> None:
        self.rule_repo = RuleRepository()
        self.executor = RuleExecutor()
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.engines.rule_engine")
        self._rules_cache: List[FraudRule] = []
        
        # Load rules during initialization
        self.load_rules()

    def load_rules(self) -> List[FraudRule]:
        """
        Retrieves active rules from RuleRepository and sorts them by priority order (ascending).
        
        Returns:
            List of sorted FraudRule domain model objects.
        """
        try:
            self.logger.debug("Loading dynamic rules from MySQL...")
            all_rules = self.rule_repo.search({"enabled": True})
            
            # Sort by priority ascending (e.g. priority 1 runs before priority 2)
            all_rules.sort(key=lambda r: r.priority)
            
            self._rules_cache = all_rules
            self.logger.info(f"Successfully loaded {len(self._rules_cache)} active rules into cache.")
            return self._rules_cache
        except Exception as e:
            self.logger.error(f"Failed to load rules from repository: {e}", exc_info=True)
            raise DatabaseException(f"Failed to load rules: {e}")

    def reload_rules(self) -> None:
        """
        Clears cached rules and forces a refresh query from MySQL.
        """
        self._rules_cache.clear()
        self.load_rules()

    def evaluate_rule(self, rule_id: int, transaction_data: Dict[str, Any]) -> bool:
        """
        Loads and evaluates a single rule against transaction data.
        
        Returns:
            True if the rule triggers, False otherwise.
            
        Raises:
            ValueError: If the rule is missing.
        """
        rule = self.rule_repo.find_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found in database.")

        field = rule.field_name
        val = transaction_data.get(field)
        
        from engines.rule_evaluator import RuleEvaluator
        return RuleEvaluator.evaluate(val, rule.operator, rule.threshold)

    def execute_rules(
        self,
        transaction_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], int, str, List[str]]:
        """
        Executes all loaded rules sequentially on transaction data.
        
        Args:
            transaction_data: Dictionary representing transaction fields (amount, device, mcc, etc.).
            
        Returns:
            A tuple of (triggered_rules, risk_points, severity, reasons).
        """
        if not self._rules_cache:
            # Re-attempt load if cache is empty
            self.load_rules()
            
        return self.executor.execute(self._rules_cache, transaction_data)

    def enable_rule(self, rule_id: int) -> None:
        """
        Enables a rule by rule ID in the database and reloads cache.
        """
        rule = self.rule_repo.find_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found in database.")
            
        if not rule.enabled:
            old_values = rule.to_dict()
            rule.enabled = True
            self.rule_repo.update(rule)
            self.db.commit()
            self.logger.info(f"Rule '{rule.rule_name}' (ID: {rule_id}) enabled successfully.")
            self.reload_rules()
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="ENABLE_RULE",
                affected_table="fraud_rules",
                record_id=rule_id,
                old_values=old_values,
                new_values=rule.to_dict(),
                performed_by="SYSTEM"
            )

    def disable_rule(self, rule_id: int) -> None:
        """
        Disables a rule by rule ID in the database and reloads cache.
        """
        rule = self.rule_repo.find_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found in database.")
            
        if rule.enabled:
            old_values = rule.to_dict()
            rule.enabled = False
            self.rule_repo.update(rule)
            self.db.commit()
            self.logger.info(f"Rule '{rule.rule_name}' (ID: {rule_id}) disabled successfully.")
            self.reload_rules()
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="DISABLE_RULE",
                affected_table="fraud_rules",
                record_id=rule_id,
                old_values=old_values,
                new_values=rule.to_dict(),
                performed_by="SYSTEM"
            )
