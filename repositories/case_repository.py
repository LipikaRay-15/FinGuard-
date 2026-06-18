from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Case
from repositories.base_repository import BaseRepository

class CaseRepository(BaseRepository[Case]):
    """
    Repository class handling persistence and queries for the Case domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Case) -> Case:
        entity.validate()
        query = """
            INSERT INTO cases (alert_id, assigned_to, status, priority, notes, remarks, analyst_notes, resolution, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.alert_id,
            entity.assigned_to,
            entity.status,
            entity.priority,
            entity.notes,
            entity.remarks,
            entity.analyst_notes,
            entity.resolution,
            entity.created_at,
            entity.updated_at
        )
        cursor = self.db.execute(query, params)
        entity.case_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Case) -> None:
        entity.validate()
        query = """
            UPDATE cases
            SET alert_id = %s, assigned_to = %s, status = %s, priority = %s, notes = %s, 
                remarks = %s, analyst_notes = %s, resolution = %s, updated_at = NOW()
            WHERE case_id = %s
        """
        params = (
            entity.alert_id,
            entity.assigned_to,
            entity.status,
            entity.priority,
            entity.notes,
            entity.remarks,
            entity.analyst_notes,
            entity.resolution,
            entity.case_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM cases WHERE case_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Case]:
        query = "SELECT * FROM cases WHERE case_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Case.from_dict(row) if row else None

    def find_all(self) -> List[Case]:
        query = "SELECT * FROM cases"
        rows = self.db.fetch_all(query)
        return [Case.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Case]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM cases WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Case.from_dict(row) for row in rows]
