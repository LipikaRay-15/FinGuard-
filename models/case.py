from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class Case:
    """
    Represents a Case domain entity in the FinGuard platform.
    Tracks investigation details of alerts.
    """
    def __init__(
        self,
        case_id: Optional[int],
        alert_id: int,
        assigned_to: Optional[str] = None,
        status: str = "OPEN",
        priority: str = "MEDIUM",
        notes: Optional[str] = None,
        remarks: Optional[str] = None,
        analyst_notes: Optional[str] = None,
        resolution: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> None:
        self.case_id = case_id
        self.alert_id = alert_id
        self.assigned_to = assigned_to
        self.status = status.upper() if status else "OPEN"
        self.priority = priority.upper() if priority else "MEDIUM"
        self.notes = notes
        self.remarks = remarks
        self.analyst_notes = analyst_notes
        self.resolution = resolution
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def validate(self) -> None:
        """
        Validates case fields.
        Raises:
            ValidationException: If checks fail.
        """
        if self.alert_id <= 0:
            raise ValidationException(f"Invalid alert_id: {self.alert_id}. Must be positive.")
        if self.status not in ("OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED"):
            raise ValidationException(f"Invalid case status: '{self.status}'")
        if self.priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValidationException(f"Invalid case priority: '{self.priority}'")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "case_id": self.case_id,
            "alert_id": self.alert_id,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "priority": self.priority,
            "notes": self.notes,
            "remarks": self.remarks,
            "analyst_notes": self.analyst_notes,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        """
        Deserializes a dictionary into a Case entity object instance.
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                pass
                
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                pass

        return cls(
            case_id=data.get("case_id"),
            alert_id=data.get("alert_id", 0),
            assigned_to=data.get("assigned_to"),
            status=data.get("status", "OPEN"),
            priority=data.get("priority", "MEDIUM"),
            notes=data.get("notes"),
            remarks=data.get("remarks"),
            analyst_notes=data.get("analyst_notes"),
            resolution=data.get("resolution"),
            created_at=created_at,
            updated_at=updated_at
        )

    def __str__(self) -> str:
        return f"Case(ID: {self.case_id}, Alert: {self.alert_id}, Assignee: {self.assigned_to}, Status: {self.status}, Priority: {self.priority})"
