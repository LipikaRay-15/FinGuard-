from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import RuleExecutionLog
from repositories.base_repository import BaseRepository

class RuleExecutionLogRepository(BaseRepository[RuleExecutionLog]):
    """
    Repository class handling persistence and queries for the RuleExecutionLog domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: RuleExecutionLog) -> RuleExecutionLog:
        entity.validate()
        query = """
            INSERT INTO rule_execution_logs (transaction_id, rule_id, rule_name, triggered, risk_score_awarded, severity, reason, execution_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Convert bool triggered to 1 or 0 for MySQL
        triggered_val = 1 if entity.triggered else 0
        params = (
            entity.transaction_id,
            entity.rule_id,
            entity.rule_name,
            triggered_val,
            entity.risk_score_awarded,
            entity.severity,
            entity.reason,
            entity.execution_time
        )
        cursor = self.db.execute(query, params)
        entity.execution_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: RuleExecutionLog) -> None:
        entity.validate()
        query = """
            UPDATE rule_execution_logs
            SET transaction_id = %s, rule_id = %s, rule_name = %s, triggered = %s, risk_score_awarded = %s, severity = %s, reason = %s, execution_time = %s
            WHERE execution_id = %s
        """
        triggered_val = 1 if entity.triggered else 0
        params = (
            entity.transaction_id,
            entity.rule_id,
            entity.rule_name,
            triggered_val,
            entity.risk_score_awarded,
            entity.severity,
            entity.reason,
            entity.execution_time,
            entity.execution_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM rule_execution_logs WHERE execution_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[RuleExecutionLog]:
        query = "SELECT * FROM rule_execution_logs WHERE execution_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return RuleExecutionLog.from_dict(row) if row else None

    def find_all(self) -> List[RuleExecutionLog]:
        query = "SELECT * FROM rule_execution_logs"
        rows = self.db.fetch_all(query)
        return [RuleExecutionLog.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[RuleExecutionLog]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM rule_execution_logs WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [RuleExecutionLog.from_dict(row) for row in rows]
