from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from exceptions import ValidationException

class Transaction:
    """
    Represents a Transaction domain entity in the FinGuard platform.
    """
    def __init__(
        self,
        transaction_id: Optional[int],
        customer_id: int,
        merchant_id: Optional[int],
        device_id: Optional[int],
        amount: Union[float, Decimal, str],
        currency: str = "USD",
        transaction_type: str = "PURCHASE",
        status: str = "PENDING",
        location_latitude: Optional[Union[float, Decimal]] = None,
        location_longitude: Optional[Union[float, Decimal]] = None,
        transaction_time: Optional[datetime] = None
    ) -> None:
        self.transaction_id = transaction_id
        self.customer_id = customer_id
        self.merchant_id = merchant_id
        self.device_id = device_id
        self.amount = Decimal(str(amount)) if amount is not None else Decimal("0.00")
        self.currency = currency
        self.transaction_type = transaction_type
        self.status = status
        self.location_latitude = Decimal(str(location_latitude)) if location_latitude is not None else None
        self.location_longitude = Decimal(str(location_longitude)) if location_longitude is not None else None
        self.transaction_time = transaction_time or datetime.now()

    def validate(self) -> None:
        """
        Validates transaction field properties.
        Raises:
            ValidationException: If validations fail.
        """
        if self.customer_id <= 0:
            raise ValidationException(f"Invalid customer_id: {self.customer_id}. Must be positive.")
        if self.amount < Decimal("0.00"):
            raise ValidationException(f"Transaction amount cannot be negative. Got: {self.amount}")
        if not self.currency or len(self.currency) != 3:
            raise ValidationException(f"Transaction currency must be a 3-character ISO code (e.g. USD). Got: '{self.currency}'")
        if self.transaction_type not in ("PURCHASE", "WITHDRAWAL", "TRANSFER", "DEPOSIT"):
            raise ValidationException(f"Invalid transaction_type: '{self.transaction_type}'")
        if self.status not in ("PENDING", "APPROVED", "DECLINED", "FLAGGED"):
            raise ValidationException(f"Invalid transaction status: '{self.status}'")
            
        # Latitude range check
        if self.location_latitude is not None:
            if not (Decimal("-90.0") <= self.location_latitude <= Decimal("90.0")):
                raise ValidationException(f"Latitude must be between -90 and 90. Got: {self.location_latitude}")
                
        # Longitude range check
        if self.location_longitude is not None:
            if not (Decimal("-180.0") <= self.location_longitude <= Decimal("180.0")):
                raise ValidationException(f"Longitude must be between -180 and 180. Got: {self.location_longitude}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "merchant_id": self.merchant_id,
            "device_id": self.device_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "transaction_type": self.transaction_type,
            "status": self.status,
            "location_latitude": str(self.location_latitude) if self.location_latitude is not None else None,
            "location_longitude": str(self.location_longitude) if self.location_longitude is not None else None,
            "transaction_time": self.transaction_time.isoformat() if isinstance(self.transaction_time, datetime) else self.transaction_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """
        Deserializes a dictionary into a Transaction entity object instance.
        """
        tx_time = data.get("transaction_time")
        if isinstance(tx_time, str):
            try:
                tx_time = datetime.fromisoformat(tx_time)
            except ValueError:
                pass

        return cls(
            transaction_id=data.get("transaction_id"),
            customer_id=data.get("customer_id", 0),
            merchant_id=data.get("merchant_id"),
            device_id=data.get("device_id"),
            amount=data.get("amount", "0.00"),
            currency=data.get("currency", "USD"),
            transaction_type=data.get("transaction_type", "PURCHASE"),
            status=data.get("status", "PENDING"),
            location_latitude=data.get("location_latitude"),
            location_longitude=data.get("location_longitude"),
            transaction_time=tx_time
        )

    def __str__(self) -> str:
        return f"Transaction(ID: {self.transaction_id}, Customer: {self.customer_id}, Amount: {self.amount} {self.currency}, Type: {self.transaction_type}, Status: {self.status})"
