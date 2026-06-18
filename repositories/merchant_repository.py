from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import MerchantProfile
from repositories.base_repository import BaseRepository

class MerchantRepository(BaseRepository[MerchantProfile]):
    """
    Repository class handling persistence and queries for the MerchantProfile domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: MerchantProfile) -> MerchantProfile:
        entity.validate()
        query = """
            INSERT INTO merchant_profiles (merchant_name, merchant_category_code, risk_level, trust_score, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            entity.merchant_name,
            entity.merchant_category_code,
            entity.risk_level,
            entity.trust_score,
            entity.created_at
        )
        cursor = self.db.execute(query, params)
        entity.merchant_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: MerchantProfile) -> None:
        entity.validate()
        query = """
            UPDATE merchant_profiles
            SET merchant_name = %s, merchant_category_code = %s, risk_level = %s, trust_score = %s
            WHERE merchant_id = %s
        """
        params = (
            entity.merchant_name,
            entity.merchant_category_code,
            entity.risk_level,
            entity.trust_score,
            entity.merchant_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM merchant_profiles WHERE merchant_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[MerchantProfile]:
        query = "SELECT * FROM merchant_profiles WHERE merchant_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return MerchantProfile.from_dict(row) if row else None

    def find_all(self) -> List[MerchantProfile]:
        query = "SELECT * FROM merchant_profiles"
        rows = self.db.fetch_all(query)
        return [MerchantProfile.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[MerchantProfile]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM merchant_profiles WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [MerchantProfile.from_dict(row) for row in rows]
