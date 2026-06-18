import json
from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import AuditLog
from repositories.base_repository import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):
    """
    Repository class handling persistence and queries for the AuditLog domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: AuditLog) -> AuditLog:
        entity.validate()
        query = """
            INSERT INTO audit_logs (user_action, affected_table, record_id, old_values, new_values, performed_by, performed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        old_val_str = json.dumps(entity.old_values) if entity.old_values is not None else None
        new_val_str = json.dumps(entity.new_values) if entity.new_values is not None else None
        params = (
            entity.user_action,
            entity.affected_table,
            entity.record_id,
            old_val_str,
            new_val_str,
            entity.performed_by,
            entity.performed_at
        )
        cursor = self.db.execute(query, params)
        entity.audit_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: AuditLog) -> None:
        entity.validate()
        query = """
            UPDATE audit_logs
            SET user_action = %s, affected_table = %s, record_id = %s, old_values = %s, new_values = %s, performed_by = %s
            WHERE audit_id = %s
        """
        old_val_str = json.dumps(entity.old_values) if entity.old_values is not None else None
        new_val_str = json.dumps(entity.new_values) if entity.new_values is not None else None
        params = (
            entity.user_action,
            entity.affected_table,
            entity.record_id,
            old_val_str,
            new_val_str,
            entity.performed_by,
            entity.audit_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM audit_logs WHERE audit_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[AuditLog]:
        query = "SELECT * FROM audit_logs WHERE audit_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return AuditLog.from_dict(row) if row else None

    def find_all(self) -> List[AuditLog]:
        query = "SELECT * FROM audit_logs"
        rows = self.db.fetch_all(query)
        return [AuditLog.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[AuditLog]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM audit_logs WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [AuditLog.from_dict(row) for row in rows]
