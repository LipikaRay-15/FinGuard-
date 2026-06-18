import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import ValidationException, DatabaseException
from models import Event
from repositories import EventRepository

class EventService:
    """
    Service class responsible for coordinating Event persistence, retrieval,
    searching, and timeline building.
    """
    def __init__(self) -> None:
        self.event_repo = EventRepository()
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.services.event_service")

    def create_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Event:
        """
        Creates and persists a new system event.
        
        Args:
            event_type: The type of event (e.g. TRANSACTION_CREATED).
            entity_type: The type of target entity (e.g. CUSTOMER, TRANSACTION).
            entity_id: The ID identifying the target entity.
            details: Dictionary containing event metadata.
            
        Returns:
            The saved Event object.
            
        Raises:
            ValidationException: If fields are invalid.
            DatabaseException: If database insert fails.
        """
        self.logger.debug(f"Creating event '{event_type}' for entity '{entity_type}:{entity_id}'")
        
        try:
            event = Event(
                event_id=None,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                details=details,
                created_at=datetime.now()
            )
            saved = self.event_repo.create(event)
            self.db.commit()
            self.logger.info(f"Event logged successfully. ID: {saved.event_id}, Type: {saved.event_type}")
            return saved
        except ValidationException as ve:
            self.logger.error(f"Event validation failed: {ve}")
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to persist event to store: {e}", exc_info=True)
            raise DatabaseException(f"Event store creation failed: {e}")

    def get_event(self, event_id: int) -> Event:
        """
        Retrieves a single event by its ID.
        
        Raises:
            ValueError: If the event does not exist.
        """
        event = self.event_repo.find_by_id(event_id)
        if not event:
            raise ValueError(f"Event with ID {event_id} not found in store.")
        return event

    def get_events_by_entity(self, entity_type: str, entity_id: str) -> List[Event]:
        """
        Retrieves all events matching the specified entity type and ID.
        """
        if not entity_type or not entity_id:
            return []
        return self.event_repo.search({"entity_type": entity_type, "entity_id": str(entity_id)})

    def get_events_by_type(self, event_type: str) -> List[Event]:
        """
        Retrieves all events of the specified event type.
        """
        if not event_type:
            return []
        return self.event_repo.search({"event_type": event_type})

    def get_timeline(self, entity_type: str, entity_id: str) -> List[Event]:
        """
        Retrieves all events matching the specified entity type and ID,
        sorted chronologically by created_at (ascending).
        """
        events = self.get_events_by_entity(entity_type, entity_id)
        # Sort by creation timeline ascending
        events.sort(key=lambda x: x.created_at)
        return events

    def search_events(self, filters: Dict[str, Any]) -> List[Event]:
        """
        Searches and filters events dynamically using the repository search.
        """
        self.logger.debug(f"Searching events with filters: {filters}")
        return self.event_repo.search(filters)
