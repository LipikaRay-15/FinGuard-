from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class Blacklist:
    """
    Represents a Blacklist entry domain entity in the FinGuard platform.
    Can represent either a blacklisted Customer or a blacklisted Device.
    """
    def __init__(
        self,
        blacklist_id: Optional[int],
        entity_type: str, # 'CUSTOMER' or 'DEVICE'
        entity_id: int,    # Matches customer_id or device_id
        reason: str,
        listed_at: Optional[datetime] = None
    ) -> None:
        self.blacklist_id = blacklist_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.reason = reason
        self.listed_at = listed_at or datetime.now()

    def validate(self) -> None:
        """
        Validates blacklist entry fields.
        Raises:
            ValidationException: If validations fail.
        """
        if self.entity_type not in ("CUSTOMER", "DEVICE"):
            raise ValidationException(f"Invalid blacklist entity_type: '{self.entity_type}'. Expected: CUSTOMER, DEVICE.")
        if self.entity_id <= 0:
            raise ValidationException(f"Invalid entity_id: {self.entity_id}. Must be positive.")
        if not self.reason or not self.reason.strip():
            raise ValidationException("Blacklist reason cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "blacklist_id": self.blacklist_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "reason": self.reason,
            "listed_at": self.listed_at.isoformat() if isinstance(self.listed_at, datetime) else self.listed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Blacklist":
        """
        Deserializes a dictionary into a Blacklist entity object instance.
        """
        listed = data.get("listed_at")
        if isinstance(listed, str):
            try:
                listed = datetime.fromisoformat(listed)
            except ValueError:
                pass

        return cls(
            blacklist_id=data.get("blacklist_id"),
            entity_type=data.get("entity_type", "CUSTOMER"),
            entity_id=data.get("entity_id", 0),
            reason=data.get("reason", ""),
            listed_at=listed
        )

    def __str__(self) -> str:
        return f"Blacklist(ID: {self.blacklist_id}, Type: {self.entity_type}, EntityID: {self.entity_id}, Reason: '{self.reason}')"
