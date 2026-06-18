from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class MerchantProfile:
    """
    Represents a MerchantProfile domain entity in the FinGuard platform.
    Defines trust ratings and risk levels of merchants.
    """
    def __init__(
        self,
        merchant_id: Optional[int],
        merchant_name: str,
        merchant_category_code: str,
        risk_level: str = "LOW",
        trust_score: int = 100,
        created_at: Optional[datetime] = None
    ) -> None:
        self.merchant_id = merchant_id
        self.merchant_name = merchant_name
        self.merchant_category_code = merchant_category_code
        self.risk_level = risk_level
        self.trust_score = trust_score
        self.created_at = created_at or datetime.now()

    def validate(self) -> None:
        """
        Validates merchant profile fields.
        Raises:
            ValidationException: If checks fail.
        """
        if not self.merchant_name or not self.merchant_name.strip():
            raise ValidationException("MerchantProfile merchant_name cannot be empty.")
        if not self.merchant_category_code or len(self.merchant_category_code) != 4 or not self.merchant_category_code.isdigit():
            raise ValidationException(f"Merchant Category Code (MCC) must be a 4-digit numeric string. Got: '{self.merchant_category_code}'")
        if self.risk_level not in ("LOW", "MEDIUM", "HIGH"):
            raise ValidationException(f"Invalid risk_level: '{self.risk_level}'. Expected: LOW, MEDIUM, HIGH.")
        if not (0 <= self.trust_score <= 100):
            raise ValidationException(f"trust_score must be between 0 and 100. Got: {self.trust_score}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "merchant_category_code": self.merchant_category_code,
            "risk_level": self.risk_level,
            "trust_score": self.trust_score,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MerchantProfile":
        """
        Deserializes a dictionary into a MerchantProfile entity object instance.
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                pass

        return cls(
            merchant_id=data.get("merchant_id"),
            merchant_name=data.get("merchant_name", ""),
            merchant_category_code=data.get("merchant_category_code", ""),
            risk_level=data.get("risk_level", "LOW"),
            trust_score=data.get("trust_score", 100),
            created_at=created_at
        )

    def __str__(self) -> str:
        return f"MerchantProfile(ID: {self.merchant_id}, Name: {self.merchant_name}, MCC: {self.merchant_category_code}, Risk: {self.risk_level}, Trust: {self.trust_score})"
