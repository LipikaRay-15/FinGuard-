from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Alert
from repositories.base_repository import BaseRepository

class AlertRepository(BaseRepository[Alert]):
    """
    Repository class handling persistence and queries for the Alert domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Alert) -> Alert:
        entity.validate()
        query = """
            INSERT INTO alerts (transaction_id, customer_id, risk_score, severity, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.transaction_id,
            entity.customer_id,
            entity.risk_score,
            entity.severity,
            entity.status,
            entity.created_at
        )
        cursor = self.db.execute(query, params)
        entity.alert_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Alert) -> None:
        entity.validate()
        query = """
            UPDATE alerts
            SET transaction_id = %s, customer_id = %s, risk_score = %s, severity = %s, status = %s
            WHERE alert_id = %s
        """
        params = (
            entity.transaction_id,
            entity.customer_id,
            entity.risk_score,
            entity.severity,
            entity.status,
            entity.alert_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM alerts WHERE alert_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Alert]:
        query = "SELECT * FROM alerts WHERE alert_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Alert.from_dict(row) if row else None

    def find_all(self) -> List[Alert]:
        query = "SELECT * FROM alerts"
        rows = self.db.fetch_all(query)
        return [Alert.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Alert]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM alerts WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Alert.from_dict(row) for row in rows]
