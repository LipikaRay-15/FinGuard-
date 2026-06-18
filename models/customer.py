from datetime import datetime
from typing import Any, Dict, Optional
from exceptions import ValidationException

class Customer:
    """
    Represents a Customer domain entity in the FinGuard platform.
    Now includes Permanent Account Number (PAN) and Account Number support.
    """
    def __init__(
        self,
        customer_id: Optional[int],
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str] = None,
        status: str = "ACTIVE",
        pan: Optional[str] = None,
        account_number: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> None:
        self.customer_id = customer_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.status = status
        self.pan = pan
        self.account_number = account_number
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def validate(self) -> None:
        """
        Performs data integrity and constraints validation on customer properties.
        
        Raises:
            ValidationException: If any verification fails.
        """
        if not self.first_name or not self.first_name.strip():
            raise ValidationException("Customer first_name cannot be empty.")
        if not self.last_name or not self.last_name.strip():
            raise ValidationException("Customer last_name cannot be empty.")
        if not self.email or "@" not in self.email:
            raise ValidationException(f"Invalid email address format: '{self.email}'")
        if self.status not in ("ACTIVE", "SUSPENDED", "BLOCKED"):
            raise ValidationException(f"Invalid customer status: '{self.status}'. Expected: ACTIVE, SUSPENDED, BLOCKED.")
        if self.pan is not None and len(self.pan) == 0:
            raise ValidationException("PAN, if provided, cannot be empty.")
        if self.account_number is not None and len(self.account_number) == 0:
            raise ValidationException("Account number, if provided, cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        return {
            "customer_id": self.customer_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "pan": self.pan,
            "account_number": self.account_number,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        """
        Deserializes a dictionary into a Customer entity object instance.
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
            customer_id=data.get("customer_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone"),
            status=data.get("status", "ACTIVE"),
            pan=data.get("pan"),
            account_number=data.get("account_number"),
            created_at=created_at,
            updated_at=updated_at
        )

    def __str__(self) -> str:
        return f"Customer(ID: {self.customer_id}, Name: {self.first_name} {self.last_name}, Email: {self.email}, Status: {self.status}, PAN: {self.pan}, Account: {self.account_number})"
