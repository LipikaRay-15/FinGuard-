from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class Whitelist:
    """
    Represents a Whitelist entry domain entity in the FinGuard platform.
    Can represent either a whitelisted Customer or a whitelisted Device.
    """
    def __init__(
        self,
        whitelist_id: Optional[int],
        entity_type: str, # 'CUSTOMER' or 'DEVICE'
        entity_id: int,    # Matches customer_id or device_id
        reason: Optional[str] = None,
        listed_at: Optional[datetime] = None
    ) -> None:
        self.whitelist_id = whitelist_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.reason = reason
        self.listed_at = listed_at or datetime.now()

    def validate(self) -> None:
        """
        Validates whitelist entry fields.
        Raises:
            ValidationException: If validations fail.
        """
        if self.entity_type not in ("CUSTOMER", "DEVICE"):
            raise ValidationException(f"Invalid whitelist entity_type: '{self.entity_type}'. Expected: CUSTOMER, DEVICE.")
        if self.entity_id <= 0:
            raise ValidationException(f"Invalid entity_id: {self.entity_id}. Must be positive.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "whitelist_id": self.whitelist_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "reason": self.reason,
            "listed_at": self.listed_at.isoformat() if isinstance(self.listed_at, datetime) else self.listed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Whitelist":
        """
        Deserializes a dictionary into a Whitelist entity object instance.
        """
        listed = data.get("listed_at")
        if isinstance(listed, str):
            try:
                listed = datetime.fromisoformat(listed)
            except ValueError:
                pass

        return cls(
            whitelist_id=data.get("whitelist_id"),
            entity_type=data.get("entity_type", "CUSTOMER"),
            entity_id=data.get("entity_id", 0),
            reason=data.get("reason"),
            listed_at=listed
        )

    def __str__(self) -> str:
        return f"Whitelist(ID: {self.whitelist_id}, Type: {self.entity_type}, EntityID: {self.entity_id}, Reason: '{self.reason}')"
