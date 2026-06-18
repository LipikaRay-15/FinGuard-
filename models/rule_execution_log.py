from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class RuleExecutionLog:
    """
    Represents a RuleExecutionLog domain entity in the FinGuard platform.
    Tracks logic outcomes of executing a specific FraudRule.
    """
    def __init__(
        self,
        execution_id: Optional[int],
        transaction_id: int,
        rule_id: int,
        triggered: bool,
        risk_score_awarded: int,
        execution_time: Optional[datetime] = None
    ) -> None:
        self.execution_id = execution_id
        self.transaction_id = transaction_id
        self.rule_id = rule_id
        self.triggered = triggered
        self.risk_score_awarded = risk_score_awarded
        self.execution_time = execution_time or datetime.now()

    def validate(self) -> None:
        """
        Validates rule execution log fields.
        Raises:
            ValidationException: If validations fail.
        """
        if self.transaction_id <= 0:
            raise ValidationException(f"Invalid transaction_id: {self.transaction_id}. Must be positive.")
        if self.rule_id <= 0:
            raise ValidationException(f"Invalid rule_id: {self.rule_id}. Must be positive.")
        if not (0 <= self.risk_score_awarded <= 100):
            raise ValidationException(f"risk_score_awarded must be between 0 and 100. Got: {self.risk_score_awarded}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "execution_id": self.execution_id,
            "transaction_id": self.transaction_id,
            "rule_id": self.rule_id,
            "triggered": self.triggered,
            "risk_score_awarded": self.risk_score_awarded,
            "execution_time": self.execution_time.isoformat() if isinstance(self.execution_time, datetime) else self.execution_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleExecutionLog":
        """
        Deserializes a dictionary into a RuleExecutionLog entity object instance.
        """
        exec_time = data.get("execution_time")
        if isinstance(exec_time, str):
            try:
                exec_time = datetime.fromisoformat(exec_time)
            except ValueError:
                pass

        return cls(
            execution_id=data.get("execution_id"),
            transaction_id=data.get("transaction_id", 0),
            rule_id=data.get("rule_id", 0),
            triggered=data.get("triggered", False),
            risk_score_awarded=data.get("risk_score_awarded", 0),
            execution_time=exec_time
        )

    def __str__(self) -> str:
        return f"RuleExecutionLog(ID: {self.execution_id}, Tx: {self.transaction_id}, Rule: {self.rule_id}, Triggered: {self.triggered}, Score: {self.risk_score_awarded})"
