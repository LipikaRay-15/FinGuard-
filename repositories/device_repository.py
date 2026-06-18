from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Device
from repositories.base_repository import BaseRepository

class DeviceRepository(BaseRepository[Device]):
    """
    Repository class handling persistence and queries for the Device domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Device) -> Device:
        entity.validate()
        query = """
            INSERT INTO devices (device_fingerprint, ip_address, operating_system, user_agent, created_at, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            entity.device_fingerprint,
            entity.ip_address,
            entity.operating_system,
            entity.user_agent,
            entity.created_at,
            entity.last_seen
        )
        cursor = self.db.execute(query, params)
        entity.device_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Device) -> None:
        entity.validate()
        query = """
            UPDATE devices
            SET device_fingerprint = %s, ip_address = %s, operating_system = %s, user_agent = %s, last_seen = %s
            WHERE device_id = %s
        """
        params = (
            entity.device_fingerprint,
            entity.ip_address,
            entity.operating_system,
            entity.user_agent,
            entity.last_seen,
            entity.device_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM devices WHERE device_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Device]:
        query = "SELECT * FROM devices WHERE device_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Device.from_dict(row) if row else None

    def find_all(self) -> List[Device]:
        query = "SELECT * FROM devices"
        rows = self.db.fetch_all(query)
        return [Device.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Device]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM devices WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Device.from_dict(row) for row in rows]
