import json
from typing import Any, Dict, List, Optional
from database import DatabaseConnection
from models import Event
from repositories.base_repository import BaseRepository

class EventRepository(BaseRepository[Event]):
    """
    Repository class handling persistence and queries for the Event domain entity.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()

    def create(self, entity: Event) -> Event:
        entity.validate()
        query = """
            INSERT INTO events (event_type, entity_type, entity_id, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        details_str = json.dumps(entity.details)
        params = (
            entity.event_type,
            entity.entity_type,
            entity.entity_id,
            details_str,
            entity.created_at
        )
        cursor = self.db.execute(query, params)
        entity.event_id = cursor.lastrowid
        cursor.close()
        return entity

    def update(self, entity: Event) -> None:
        entity.validate()
        query = """
            UPDATE events
            SET event_type = %s, entity_type = %s, entity_id = %s, details = %s
            WHERE event_id = %s
        """
        details_str = json.dumps(entity.details)
        params = (
            entity.event_type,
            entity.entity_type,
            entity.entity_id,
            details_str,
            entity.event_id
        )
        cursor = self.db.execute(query, params)
        cursor.close()

    def delete(self, id_val: int) -> None:
        query = "DELETE FROM events WHERE event_id = %s"
        cursor = self.db.execute(query, (id_val,))
        cursor.close()

    def find_by_id(self, id_val: int) -> Optional[Event]:
        query = "SELECT * FROM events WHERE event_id = %s"
        row = self.db.fetch_one(query, (id_val,))
        return Event.from_dict(row) if row else None

    def find_all(self) -> List[Event]:
        query = "SELECT * FROM events"
        rows = self.db.fetch_all(query)
        return [Event.from_dict(row) for row in rows]

    def search(self, filters: Dict[str, Any]) -> List[Event]:
        if not filters:
            return self.find_all()

        where_clauses = []
        params = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        query = f"SELECT * FROM events WHERE " + " AND ".join(where_clauses)
        rows = self.db.fetch_all(query, tuple(params))
        return [Event.from_dict(row) for row in rows]
