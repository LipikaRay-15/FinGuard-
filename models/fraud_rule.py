from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class FraudRule:
    """
    Represents a FraudRule domain entity in the FinGuard platform.
    Defines dynamic fields, operators, thresholds, and risk weights for database-driven execution.
    """
    def __init__(
        self,
        rule_id: Optional[int],
        rule_name: str,
        description: Optional[str],
        field_name: str,
        operator: str,
        threshold: str,
        risk_points: int = 0,
        priority: int = 0,
        severity: str = "MEDIUM",
        enabled: bool = True,
        stop_execution: bool = False,
        created_at: Optional[datetime] = None
    ) -> None:
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.description = description
        self.field_name = field_name
        self.operator = operator
        self.threshold = threshold
        self.risk_points = risk_points
        self.priority = priority
        self.severity = severity
        self.enabled = enabled
        self.stop_execution = stop_execution
        self.created_at = created_at or datetime.now()

    def validate(self) -> None:
        """
        Validates fraud rule fields.
        Raises:
            ValidationException: If validations fail.
        """
        if not self.rule_name or not self.rule_name.strip():
            raise ValidationException("FraudRule rule_name cannot be empty.")
        if not self.field_name or not self.field_name.strip():
            raise ValidationException("FraudRule field_name cannot be empty.")
        if not self.operator or not self.operator.strip():
            raise ValidationException("FraudRule operator cannot be empty.")
        if self.threshold is None:
            raise ValidationException("FraudRule threshold cannot be None.")
        if not (0 <= self.risk_points <= 100):
            raise ValidationException(f"FraudRule risk_points must be between 0 and 100. Got: {self.risk_points}")
        if self.severity.upper() not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValidationException(f"Invalid severity value: '{self.severity}'. Expected: LOW, MEDIUM, HIGH, CRITICAL.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "field_name": self.field_name,
            "operator": self.operator,
            "threshold": self.threshold,
            "risk_points": self.risk_points,
            "priority": self.priority,
            "severity": self.severity,
            "enabled": self.enabled,
            "stop_execution": self.stop_execution,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FraudRule":
        """
        Deserializes a dictionary into a FraudRule entity object instance.
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                pass

        return cls(
            rule_id=data.get("rule_id"),
            rule_name=data.get("rule_name", ""),
            description=data.get("description"),
            field_name=data.get("field_name", ""),
            operator=data.get("operator", ""),
            threshold=data.get("threshold", ""),
            risk_points=data.get("risk_points", 0),
            priority=data.get("priority", 0),
            severity=data.get("severity", "MEDIUM"),
            enabled=bool(data.get("enabled", True)),
            stop_execution=bool(data.get("stop_execution", False)),
            created_at=created_at
        )

    def __str__(self) -> str:
        return f"FraudRule(ID: {self.rule_id}, Name: {self.rule_name}, Field: {self.field_name}, Op: {self.operator}, Risk: {self.risk_points}, Enabled: {self.enabled})"
