import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from exceptions import ValidationException

class Event:
    """
    Represents an Event domain entity in the FinGuard platform.
    Logs auxiliary user events (e.g. login attempts, reset passwords).
    """
    def __init__(
        self,
        event_id: Optional[int],
        event_type: str,
        customer_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Union[str, Dict[str, Any]]] = None,
        event_time: Optional[datetime] = None
    ) -> None:
        self.event_id = event_id
        self.event_type = event_type
        self.customer_id = customer_id
        self.ip_address = ip_address
        
        # Details parsed as dict
        if isinstance(details, str):
            try:
                self.details = json.loads(details)
            except json.JSONDecodeError:
                self.details = {}
        else:
            self.details = details or {}
            
        self.event_time = event_time or datetime.now()

    def validate(self) -> None:
        """
        Validates event fields.
        Raises:
            ValidationException: If validations fail.
        """
        if not self.event_type or not self.event_type.strip():
            raise ValidationException("Event event_type cannot be empty.")
        if self.customer_id is not None and self.customer_id <= 0:
            raise ValidationException(f"Invalid customer_id: {self.customer_id}. Must be positive.")
        if not isinstance(self.details, dict):
            raise ValidationException("Event details must be a valid JSON dictionary.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "customer_id": self.customer_id,
            "ip_address": self.ip_address,
            "details": self.details,
            "event_time": self.event_time.isoformat() if isinstance(self.event_time, datetime) else self.event_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """
        Deserializes a dictionary into an Event entity object instance.
        """
        evt_time = data.get("event_time")
        if isinstance(evt_time, str):
            try:
                evt_time = datetime.fromisoformat(evt_time)
            except ValueError:
                pass

        details = data.get("details", {})
        
        return cls(
            event_id=data.get("event_id"),
            event_type=data.get("event_type", ""),
            customer_id=data.get("customer_id"),
            ip_address=data.get("ip_address"),
            details=details,
            event_time=evt_time
        )

    def __str__(self) -> str:
        return f"Event(ID: {self.event_id}, Type: {self.event_type}, Customer: {self.customer_id}, IP: {self.ip_address})"
