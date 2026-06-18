from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class RiskHistory:
    """
    Represents a RiskHistory domain entity in the FinGuard platform.
    Logs updates and shifts in a Customer's risk score.
    """
    def __init__(
        self,
        history_id: Optional[int],
        customer_id: int,
        previous_risk_score: int,
        new_risk_score: int,
        reason: Optional[str] = None,
        recorded_at: Optional[datetime] = None
    ) -> None:
        self.history_id = history_id
        self.customer_id = customer_id
        self.previous_risk_score = previous_risk_score
        self.new_risk_score = new_risk_score
        self.reason = reason
        self.recorded_at = recorded_at or datetime.now()

    def validate(self) -> None:
        """
        Validates risk history fields.
        Raises:
            ValidationException: If checks fail.
        """
        if self.customer_id <= 0:
            raise ValidationException(f"Invalid customer_id: {self.customer_id}. Must be positive.")
        if not (0 <= self.previous_risk_score <= 100):
            raise ValidationException(f"previous_risk_score must be between 0 and 100. Got: {self.previous_risk_score}")
        if not (0 <= self.new_risk_score <= 100):
            raise ValidationException(f"new_risk_score must be between 0 and 100. Got: {self.new_risk_score}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "history_id": self.history_id,
            "customer_id": self.customer_id,
            "previous_risk_score": self.previous_risk_score,
            "new_risk_score": self.new_risk_score,
            "reason": self.reason,
            "recorded_at": self.recorded_at.isoformat() if isinstance(self.recorded_at, datetime) else self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskHistory":
        """
        Deserializes a dictionary into a RiskHistory entity object instance.
        """
        recorded = data.get("recorded_at")
        if isinstance(recorded, str):
            try:
                recorded = datetime.fromisoformat(recorded)
            except ValueError:
                pass

        return cls(
            history_id=data.get("history_id"),
            customer_id=data.get("customer_id", 0),
            previous_risk_score=data.get("previous_risk_score", 0),
            new_risk_score=data.get("new_risk_score", 0),
            reason=data.get("reason"),
            recorded_at=recorded
        )

    def __str__(self) -> str:
        return f"RiskHistory(ID: {self.history_id}, Customer: {self.customer_id}, ScoreChange: {self.previous_risk_score} -> {self.new_risk_score}, Reason: '{self.reason}')"
