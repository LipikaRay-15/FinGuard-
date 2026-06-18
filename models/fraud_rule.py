import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from exceptions import ValidationException

class FraudRule:
    """
    Represents a FraudRule domain entity in the FinGuard platform.
    Defines rule parameters and scoring weights.
    """
    def __init__(
        self,
        rule_id: Optional[int],
        rule_name: str,
        description: Optional[str],
        criteria_json: Union[str, Dict[str, Any]],
        risk_score: int = 0,
        is_active: bool = True,
        created_at: Optional[datetime] = None
    ) -> None:
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.description = description
        
        # Keep criteria_json as a parsed dict internally
        if isinstance(criteria_json, str):
            try:
                self.criteria_json = json.loads(criteria_json)
            except json.JSONDecodeError:
                self.criteria_json = {}
        else:
            self.criteria_json = criteria_json or {}
            
        self.risk_score = risk_score
        self.is_active = is_active
        self.created_at = created_at or datetime.now()

    def validate(self) -> None:
        """
        Validates fraud rule fields.
        Raises:
            ValidationException: If validations fail.
        """
        if not self.rule_name or not self.rule_name.strip():
            raise ValidationException("FraudRule rule_name cannot be empty.")
        if not isinstance(self.criteria_json, dict):
            raise ValidationException("criteria_json must be a valid JSON dictionary.")
        if not (0 <= self.risk_score <= 100):
            raise ValidationException(f"FraudRule risk_score must be between 0 and 100. Got: {self.risk_score}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "criteria_json": self.criteria_json,
            "risk_score": self.risk_score,
            "is_active": self.is_active,
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

        criteria = data.get("criteria_json", {})
        
        return cls(
            rule_id=data.get("rule_id"),
            rule_name=data.get("rule_name", ""),
            description=data.get("description"),
            criteria_json=criteria,
            risk_score=data.get("risk_score", 0),
            is_active=data.get("is_active", True),
            created_at=created_at
        )

    def __str__(self) -> str:
        return f"FraudRule(ID: {self.rule_id}, Name: {self.rule_name}, Risk: {self.risk_score}, Active: {self.is_active})"
