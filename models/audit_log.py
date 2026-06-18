import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from exceptions import ValidationException

class AuditLog:
    """
    Represents an AuditLog domain entity in the FinGuard platform.
    Records operations performed on key system models.
    """
    def __init__(
        self,
        audit_id: Optional[int],
        user_action: str,
        affected_table: Optional[str],
        record_id: Optional[int],
        old_values: Optional[Union[str, Dict[str, Any]]] = None,
        new_values: Optional[Union[str, Dict[str, Any]]] = None,
        performed_by: str = "SYSTEM",
        performed_at: Optional[datetime] = None
    ) -> None:
        self.audit_id = audit_id
        self.user_action = user_action
        self.affected_table = affected_table
        self.record_id = record_id
        
        # Parse old/new values as dicts
        if isinstance(old_values, str):
            try:
                self.old_values = json.loads(old_values)
            except json.JSONDecodeError:
                self.old_values = {}
        else:
            self.old_values = old_values
            
        if isinstance(new_values, str):
            try:
                self.new_values = json.loads(new_values)
            except json.JSONDecodeError:
                self.new_values = {}
        else:
            self.new_values = new_values

        self.performed_by = performed_by
        self.performed_at = performed_at or datetime.now()

    def validate(self) -> None:
        """
        Validates audit log fields.
        Raises:
            ValidationException: If checks fail.
        """
        if not self.user_action or not self.user_action.strip():
            raise ValidationException("AuditLog user_action cannot be empty.")
        if not self.performed_by or not self.performed_by.strip():
            raise ValidationException("AuditLog performed_by cannot be empty.")
        if self.old_values is not None and not isinstance(self.old_values, dict):
            raise ValidationException("AuditLog old_values must be a valid JSON dictionary.")
        if self.new_values is not None and not isinstance(self.new_values, dict):
            raise ValidationException("AuditLog new_values must be a valid JSON dictionary.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "audit_id": self.audit_id,
            "user_action": self.user_action,
            "affected_table": self.affected_table,
            "record_id": self.record_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at.isoformat() if isinstance(self.performed_at, datetime) else self.performed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLog":
        """
        Deserializes a dictionary into an AuditLog entity object instance.
        """
        perf_at = data.get("performed_at")
        if isinstance(perf_at, str):
            try:
                perf_at = datetime.fromisoformat(perf_at)
            except ValueError:
                pass

        return cls(
            audit_id=data.get("audit_id"),
            user_action=data.get("user_action", ""),
            affected_table=data.get("affected_table"),
            record_id=data.get("record_id"),
            old_values=data.get("old_values"),
            new_values=data.get("new_values"),
            performed_by=data.get("performed_by", "SYSTEM"),
            performed_at=perf_at
        )

    def __str__(self) -> str:
        return f"AuditLog(ID: {self.audit_id}, Action: {self.user_action}, Table: {self.affected_table}, Record: {self.record_id}, Operator: {self.performed_by})"
