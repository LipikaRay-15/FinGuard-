import logging
from typing import Any, Dict, Optional
import threading

from models import Event
from services.event_service import EventService

class EventManager:
    """
    Thread-safe Singleton Event Dispatcher / Publisher.
    Coordinates event storage and ensures errors in logging do not disrupt primary transactions.
    """
    _instance: Optional['EventManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'EventManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventManager, cls).__new__(cls)
                cls._instance._event_service = EventService()
                cls._instance._logger = logging.getLogger("finguard.engines.event_manager")
        return cls._instance

    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[Any],
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[Event]:
        """
        Dispatches and logs an event. Errors are handled gracefully so they do not
        interfere with the caller's main database transaction.
        
        Args:
            event_type: The type of event (e.g. TRANSACTION_CREATED).
            entity_type: The category of entity (e.g. CUSTOMER, DEVICE).
            entity_id: The primary identifier of the entity.
            details: Extra details of the event context.
            
        Returns:
            The saved Event object or None if logging failed.
        """
        self._logger.debug(f"EventManager publishing '{event_type}' for entity '{entity_type}:{entity_id}'")
        try:
            eid_str = str(entity_id) if entity_id is not None else None
            evt = self._event_service.create_event(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=eid_str,
                details=details
            )
            return evt
        except Exception as e:
            self._logger.error(
                f"Gracefully intercepted event logging failure (Type: {event_type}, Entity: {entity_type}:{entity_id}): {e}",
                exc_info=True
            )
            return None
