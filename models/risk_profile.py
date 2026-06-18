from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class RiskProfile:
    """
    Represents a RiskProfile domain entity in the FinGuard platform.
    Consolidates the current risk evaluation for a Customer.
    """
    def __init__(
        self,
        profile_id: Optional[int],
        customer_id: int,
        current_risk_score: int = 0,
        risk_tier: str = "LOW",
        last_evaluated_at: Optional[datetime] = None
    ) -> None:
        self.profile_id = profile_id
        self.customer_id = customer_id
        self.current_risk_score = current_risk_score
        self.risk_tier = risk_tier
        self.last_evaluated_at = last_evaluated_at or datetime.now()

    def validate(self) -> None:
        """
        Validates risk profile fields.
        Raises:
            ValidationException: If checks fail.
        """
        if self.customer_id <= 0:
            raise ValidationException(f"Invalid customer_id: {self.customer_id}. Must be positive.")
        if not (0 <= self.current_risk_score <= 100):
            raise ValidationException(f"current_risk_score must be between 0 and 100. Got: {self.current_risk_score}")
        if self.risk_tier not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValidationException(f"Invalid risk_tier: '{self.risk_tier}'. Expected: LOW, MEDIUM, HIGH, CRITICAL.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "profile_id": self.profile_id,
            "customer_id": self.customer_id,
            "current_risk_score": self.current_risk_score,
            "risk_tier": self.risk_tier,
            "last_evaluated_at": self.last_evaluated_at.isoformat() if isinstance(self.last_evaluated_at, datetime) else self.last_evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskProfile":
        """
        Deserializes a dictionary into a RiskProfile entity object instance.
        """
        last_eval = data.get("last_evaluated_at")
        if isinstance(last_eval, str):
            try:
                last_eval = datetime.fromisoformat(last_eval)
            except ValueError:
                pass

        return cls(
            profile_id=data.get("profile_id"),
            customer_id=data.get("customer_id", 0),
            current_risk_score=data.get("current_risk_score", 0),
            risk_tier=data.get("risk_tier", "LOW"),
            last_evaluated_at=last_eval
        )

    def __str__(self) -> str:
        return f"RiskProfile(ID: {self.profile_id}, Customer: {self.customer_id}, Score: {self.current_risk_score}, Tier: {self.risk_tier})"
