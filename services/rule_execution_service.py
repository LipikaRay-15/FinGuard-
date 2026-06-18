import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import DatabaseException
from models import RuleExecutionLog
from repositories import RuleExecutionLogRepository
from services.event_service import EventService

logger = logging.getLogger("finguard.services.rule_execution_service")


class RuleExecutionService:
    """
    Service class responsible for coordinating rule execution logging,
    history auditing, statistics aggregation, and Event Store dispatching.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.rule_log_repo = RuleExecutionLogRepository()
        self.event_service = EventService()

    def log_rule_execution(
        self,
        transaction_id: int,
        rule_id: int,
        triggered: bool,
        risk_points: int,
        rule_name: str,
        severity: str,
        reason: str,
        execution_time: Optional[datetime] = None
    ) -> RuleExecutionLog:
        """
        Creates, validates, and persists a RuleExecutionLog entry in MySQL.
        Dispatches a 'RULE_TRIGGERED' event to the Event Store if triggered is True.
        
        Returns:
            The saved RuleExecutionLog entity.
            
        Raises:
            DatabaseException: If MySQL execution fails.
        """
        logger.debug(f"Logging rule execution: rule={rule_name} (ID: {rule_id}), tx={transaction_id}, triggered={triggered}")
        
        try:
            log = RuleExecutionLog(
                execution_id=None,
                transaction_id=transaction_id,
                rule_id=rule_id,
                rule_name=rule_name,
                triggered=triggered,
                risk_score_awarded=risk_points,
                severity=severity,
                reason=reason,
                execution_time=execution_time or datetime.now()
            )
            
            saved = self.rule_log_repo.create(log)
            # Commit is handled at the transaction orchestrator level,
            # but we commit here if we run inside service context
            self.db.commit()
            
            # Dispatch Event if triggered is True
            if triggered:
                try:
                    self.event_service.create_event(
                        event_type="RULE_TRIGGERED",
                        entity_type="RULE",
                        entity_id=rule_name,
                        details={
                            "transaction_id": transaction_id,
                            "risk_score_awarded": risk_points,
                            "severity": severity,
                            "reason": reason
                        }
                    )
                except Exception as event_err:
                    logger.error(f"Failed to dispatch trigger event for rule '{rule_name}': {event_err}", exc_info=True)
            
            return saved
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save rule execution log: {e}", exc_info=True)
            raise DatabaseException(f"Failed to log rule execution: {e}")

    def get_transaction_rule_history(self, transaction_id: int) -> List[RuleExecutionLog]:
        """
        Retrieves all rule execution records associated with a specific transaction,
        sorted chronologically by execution time.
        """
        logs = self.rule_log_repo.search({"transaction_id": transaction_id})
        # Sort by execution time/id ascending
        logs.sort(key=lambda x: x.execution_id or 0)
        return logs

    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Aggregates system-wide statistics from the rule_execution_logs table.
        
        Returns:
            A dictionary containing:
            - total_executions
            - total_triggers
            - trigger_rate
            - triggers_by_severity: Dict mapping severity bands to trigger counts.
        """
        try:
            # 1. Total Executions
            row_total = self.db.fetch_one("SELECT COUNT(*) as cnt FROM rule_execution_logs")
            total_executions = row_total["cnt"] if row_total else 0
            
            # 2. Total Triggers
            row_triggers = self.db.fetch_one("SELECT COUNT(*) as cnt FROM rule_execution_logs WHERE triggered = TRUE")
            total_triggers = row_triggers["cnt"] if row_triggers else 0
            
            # 3. Trigger Rate
            trigger_rate = (total_triggers / total_executions * 100.0) if total_executions > 0 else 0.0
            
            # 4. Segments by severity
            severity_query = """
                SELECT severity, COUNT(*) as cnt 
                FROM rule_execution_logs 
                WHERE triggered = TRUE 
                GROUP BY severity
            """
            severity_rows = self.db.fetch_all(severity_query)
            
            triggers_by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            for row in severity_rows:
                sev_upper = str(row["severity"]).upper()
                if sev_upper in triggers_by_severity:
                    triggers_by_severity[sev_upper] = row["cnt"]
                    
            return {
                "total_executions": total_executions,
                "total_triggers": total_triggers,
                "trigger_rate": trigger_rate,
                "triggers_by_severity": triggers_by_severity
            }
        except Exception as e:
            logger.error(f"Failed to aggregate rule execution statistics: {e}", exc_info=True)
            raise DatabaseException(f"Failed to aggregate statistics: {e}")

    def get_rule_trigger_frequency(self) -> List[Dict[str, Any]]:
        """
        Aggregates trigger frequency grouped by rule name, sorted descending.
        
        Returns:
            A list of dicts: [{"rule_name", "rule_id", "trigger_count"}]
        """
        query = """
            SELECT rule_name, rule_id, COUNT(*) as trigger_count 
            FROM rule_execution_logs 
            WHERE triggered = TRUE 
            GROUP BY rule_name, rule_id 
            ORDER BY trigger_count DESC
        """
        try:
            rows = self.db.fetch_all(query)
            return [{
                "rule_name": r["rule_name"],
                "rule_id": r["rule_id"],
                "trigger_count": r["trigger_count"]
            } for r in rows]
        except Exception as e:
            logger.error(f"Failed to aggregate rule trigger frequency: {e}", exc_info=True)
            raise DatabaseException(f"Failed to aggregate trigger frequency: {e}")
