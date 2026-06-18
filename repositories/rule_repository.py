from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import FraudRule
from repositories.base_repository import BaseRepository

class RuleRepository(BaseRepository[FraudRule]):
    """
    Repository class handling persistence and queries for the FraudRule domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: FraudRule) -> FraudRule:
        entity.validate()
        query = """
            INSERT INTO fraud_rules (
                rule_name, description, field_name, operator, threshold, 
                risk_points, priority, severity, enabled, stop_execution, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.rule_name,
            entity.description,
            entity.field_name,
            entity.operator,
            entity.threshold,
            entity.risk_points,
            entity.priority,
            entity.severity,
            entity.enabled,
            entity.stop_execution,
            entity.created_at
        )
        cursor = self.db.execute(query, params)
        entity.rule_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: FraudRule) -> None:
        entity.validate()
        query = """
            UPDATE fraud_rules
            SET rule_name = %s, description = %s, field_name = %s, operator = %s, threshold = %s, 
                risk_points = %s, priority = %s, severity = %s, enabled = %s, stop_execution = %s
            WHERE rule_id = %s
        """
        params = (
            entity.rule_name,
            entity.description,
            entity.field_name,
            entity.operator,
            entity.threshold,
            entity.risk_points,
            entity.priority,
            entity.severity,
            entity.enabled,
            entity.stop_execution,
            entity.rule_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM fraud_rules WHERE rule_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[FraudRule]:
        query = "SELECT * FROM fraud_rules WHERE rule_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return FraudRule.from_dict(row) if row else None

    def find_all(self) -> List[FraudRule]:
        query = "SELECT * FROM fraud_rules"
        rows = self.db.fetch_all(query)
        return [FraudRule.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[FraudRule]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM fraud_rules WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [FraudRule.from_dict(row) for row in rows]
