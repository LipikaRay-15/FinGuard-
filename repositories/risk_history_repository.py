from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import RiskHistory
from repositories.base_repository import BaseRepository

class RiskHistoryRepository(BaseRepository[RiskHistory]):
    """
    Repository class handling persistence and queries for the RiskHistory domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: RiskHistory) -> RiskHistory:
        entity.validate()
        query = """
            INSERT INTO risk_history (customer_id, previous_risk_score, new_risk_score, reason, recorded_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            entity.customer_id,
            entity.previous_risk_score,
            entity.new_risk_score,
            entity.reason,
            entity.recorded_at
        )
        cursor = self.db.execute(query, params)
        entity.history_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: RiskHistory) -> None:
        entity.validate()
        query = """
            UPDATE risk_history
            SET customer_id = %s, previous_risk_score = %s, new_risk_score = %s, reason = %s
            WHERE history_id = %s
        """
        params = (
            entity.customer_id,
            entity.previous_risk_score,
            entity.new_risk_score,
            entity.reason,
            entity.history_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM risk_history WHERE history_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[RiskHistory]:
        query = "SELECT * FROM risk_history WHERE history_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return RiskHistory.from_dict(row) if row else None

    def find_all(self) -> List[RiskHistory]:
        query = "SELECT * FROM risk_history"
        rows = self.db.fetch_all(query)
        return [RiskHistory.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[RiskHistory]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM risk_history WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [RiskHistory.from_dict(row) for row in rows]
