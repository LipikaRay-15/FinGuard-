from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import RiskProfile
from repositories.base_repository import BaseRepository

class RiskProfileRepository(BaseRepository[RiskProfile]):
    """
    Repository class handling persistence and queries for the RiskProfile domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: RiskProfile) -> RiskProfile:
        entity.validate()
        query = """
            INSERT INTO risk_profiles (customer_id, current_risk_score, risk_tier, last_evaluated_at)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            entity.customer_id,
            entity.current_risk_score,
            entity.risk_tier,
            entity.last_evaluated_at
        )
        cursor = self.db.execute(query, params)
        entity.profile_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: RiskProfile) -> None:
        entity.validate()
        query = """
            UPDATE risk_profiles
            SET customer_id = %s, current_risk_score = %s, risk_tier = %s
            WHERE profile_id = %s
        """
        params = (
            entity.customer_id,
            entity.current_risk_score,
            entity.risk_tier,
            entity.profile_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM risk_profiles WHERE profile_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[RiskProfile]:
        query = "SELECT * FROM risk_profiles WHERE profile_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return RiskProfile.from_dict(row) if row else None

    def find_all(self) -> List[RiskProfile]:
        query = "SELECT * FROM risk_profiles"
        rows = self.db.fetch_all(query)
        return [RiskProfile.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[RiskProfile]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM risk_profiles WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [RiskProfile.from_dict(row) for row in rows]
