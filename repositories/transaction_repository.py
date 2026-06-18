from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Transaction
from repositories.base_repository import BaseRepository

class TransactionRepository(BaseRepository[Transaction]):
    """
    Repository class handling persistence and queries for the Transaction domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Transaction) -> Transaction:
        entity.validate()
        query = """
            INSERT INTO transactions (customer_id, merchant_id, device_id, amount, currency, transaction_type, status, location_latitude, location_longitude, transaction_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.customer_id,
            entity.merchant_id,
            entity.device_id,
            entity.amount,
            entity.currency,
            entity.transaction_type,
            entity.status,
            entity.location_latitude,
            entity.location_longitude,
            entity.transaction_time
        )
        cursor = self.db.execute(query, params)
        entity.transaction_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Transaction) -> None:
        entity.validate()
        query = """
            UPDATE transactions
            SET customer_id = %s, merchant_id = %s, device_id = %s, amount = %s, currency = %s, transaction_type = %s, status = %s, location_latitude = %s, location_longitude = %s
            WHERE transaction_id = %s
        """
        params = (
            entity.customer_id,
            entity.merchant_id,
            entity.device_id,
            entity.amount,
            entity.currency,
            entity.transaction_type,
            entity.status,
            entity.location_latitude,
            entity.location_longitude,
            entity.transaction_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM transactions WHERE transaction_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Transaction]:
        query = "SELECT * FROM transactions WHERE transaction_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Transaction.from_dict(row) if row else None

    def find_all(self) -> List[Transaction]:
        query = "SELECT * FROM transactions"
        rows = self.db.fetch_all(query)
        return [Transaction.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Transaction]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM transactions WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Transaction.from_dict(row) for row in rows]
