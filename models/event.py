import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from exceptions import ValidationException

class Event:
    """
    Represents an Event domain entity in the FinGuard platform.
    Logs auxiliary system actions (e.g. CUSTOMER_CREATED, TRANSACTION_FAILED) linked to entities.
    """
    def __init__(
        self,
        event_id: Optional[int],
        event_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[Union[str, Dict[str, Any]]] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        self.event_id = event_id
        self.event_type = event_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        
        # Details parsed as dict
        if isinstance(details, str):
            try:
                self.details = json.loads(details)
            except json.JSONDecodeError:
                self.details = {}
        else:
            self.details = details or {}
            
        self.created_at = created_at or datetime.now()

    def validate(self) -> None:
        """
        Validates event fields.
        Raises:
            ValidationException: If validations fail.
        """
        if not self.event_type or not self.event_type.strip():
            raise ValidationException("Event event_type cannot be empty.")
        if not self.entity_type or not self.entity_type.strip():
            raise ValidationException("Event entity_type cannot be empty.")
        if not isinstance(self.details, dict):
            raise ValidationException("Event details must be a valid JSON dictionary.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """
        Deserializes a dictionary into an Event entity object instance.
        """
        created_at = data.get("created_at") or data.get("event_time")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                pass

        details = data.get("details", {})
        
        return cls(
            event_id=data.get("event_id"),
            event_type=data.get("event_type", ""),
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id") or data.get("customer_id"), # fallback for mapping
            details=details,
            created_at=created_at
        )

    def __str__(self) -> str:
        return f"Event(ID: {self.event_id}, Type: {self.event_type}, Entity: {self.entity_type}:{self.entity_id})"
