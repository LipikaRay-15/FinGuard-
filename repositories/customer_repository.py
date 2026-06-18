from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Customer
from repositories.base_repository import BaseRepository

class CustomerRepository(BaseRepository[Customer]):
    """
    Repository class handling persistence and queries for the Customer domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Customer) -> Customer:
        # Validate entity before persist
        entity.validate()
        
        query = """
            INSERT INTO customers (
                first_name, last_name, date_of_birth, gender, email, phone, status, 
                pan, account_number, pincode, city, state, country, address, risk_level, 
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.first_name,
            entity.last_name,
            entity.date_of_birth,
            entity.gender,
            entity.email,
            entity.phone,
            entity.status,
            entity.pan,
            entity.account_number,
            entity.pincode,
            entity.city,
            entity.state,
            entity.country,
            entity.address,
            entity.risk_level,
            entity.created_at,
            entity.updated_at
        )
        cursor = self.db.execute(query, params)
        entity.customer_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Customer) -> None:
        entity.validate()
        query = """
            UPDATE customers
            SET first_name = %s, last_name = %s, date_of_birth = %s, gender = %s, email = %s, 
                phone = %s, status = %s, pan = %s, account_number = %s, pincode = %s, 
                city = %s, state = %s, country = %s, address = %s, risk_level = %s, 
                updated_at = NOW()
            WHERE customer_id = %s
        """
        params = (
            entity.first_name,
            entity.last_name,
            entity.date_of_birth,
            entity.gender,
            entity.email,
            entity.phone,
            entity.status,
            entity.pan,
            entity.account_number,
            entity.pincode,
            entity.city,
            entity.state,
            entity.country,
            entity.address,
            entity.risk_level,
            entity.customer_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM customers WHERE customer_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Customer]:
        query = "SELECT * FROM customers WHERE customer_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Customer.from_dict(row) if row else None

    def find_all(self) -> List[Customer]:
        query = "SELECT * FROM customers"
        rows = self.db.fetch_all(query)
        return [Customer.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Customer]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM customers WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Customer.from_dict(row) for row in rows]
