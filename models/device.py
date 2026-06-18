from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class Device:
    """
    Represents a Device domain entity in the FinGuard platform.
    Used for machine/browser fingerprinting check correlations.
    """
    def __init__(
        self,
        device_id: Optional[int],
        device_fingerprint: str,
        ip_address: str,
        operating_system: Optional[str] = None,
        user_agent: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        self.device_id = device_id
        self.device_fingerprint = device_fingerprint
        self.ip_address = ip_address
        self.operating_system = operating_system
        self.user_agent = user_agent
        self.created_at = created_at or datetime.now()

    def validate(self) -> None:
        """
        Validates device fields.
        Raises:
            ValidationException: If any verification fails.
        """
        if not self.device_fingerprint or not self.device_fingerprint.strip():
            raise ValidationException("Device device_fingerprint cannot be empty.")
        if len(self.device_fingerprint) != 64:
            # Expecting a SHA-256 hash
            raise ValidationException("Device fingerprint must be a 64-character SHA-256 hash.")
        if not self.ip_address or not self.ip_address.strip():
            raise ValidationException("Device ip_address cannot be empty.")
        # Check basic IP structure
        if "." not in self.ip_address and ":" not in self.ip_address:
            raise ValidationException(f"Invalid IP address format: '{self.ip_address}'")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "device_id": self.device_id,
            "device_fingerprint": self.device_fingerprint,
            "ip_address": self.ip_address,
            "operating_system": self.operating_system,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """
        Deserializes a dictionary into a Device entity object instance.
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                pass

        return cls(
            device_id=data.get("device_id"),
            device_fingerprint=data.get("device_fingerprint", ""),
            ip_address=data.get("ip_address", ""),
            operating_system=data.get("operating_system"),
            user_agent=data.get("user_agent"),
            created_at=created_at
        )

    def __str__(self) -> str:
        return f"Device(ID: {self.device_id}, Fingerprint: {self.device_fingerprint[:8]}..., IP: {self.ip_address}, OS: {self.operating_system})"
