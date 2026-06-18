from datetime import datetime, date
from typing import Any, Dict, Optional

class Customer:
    """
    Represents a Customer domain entity in the FinGuard platform.
    """
    def __init__(
        self,
        customer_id: Optional[int],
        first_name: str,
        last_name: str,
        date_of_birth: Optional[Any] = None,
        gender: Optional[str] = None,
        email: str = "",
        phone: Optional[str] = None,
        status: str = "ACTIVE",
        pan: Optional[str] = None,
        account_number: Optional[str] = None,
        pincode: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        address: Optional[str] = None,
        risk_level: str = "LOW",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> None:
        self.customer_id = customer_id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.email = email
        self.phone = phone
        self.status = status
        self.pan = pan
        self.account_number = account_number
        self.pincode = pincode
        self.city = city
        self.state = state
        self.country = country
        self.address = address
        self.risk_level = risk_level
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def validate(self) -> None:
        """
        Performs data integrity and constraints validation on customer properties.
        
        Raises:
            CustomerValidationException: If any verification fails.
        """
        from services.customer_validator import CustomerValidator
        CustomerValidator.validate_customer(self)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the object properties into a dictionary.
        """
        dob_serialized = None
        if self.date_of_birth is not None:
            if hasattr(self.date_of_birth, "isoformat"):
                dob_serialized = self.date_of_birth.isoformat()
            else:
                dob_serialized = str(self.date_of_birth)
                
        return {
            "customer_id": self.customer_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": dob_serialized,
            "gender": self.gender,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "pan": self.pan,
            "account_number": self.account_number,
            "pincode": self.pincode,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "address": self.address,
            "risk_level": self.risk_level,
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
                
        date_of_birth = data.get("date_of_birth")
        if isinstance(date_of_birth, str) and date_of_birth.strip():
            try:
                date_of_birth = date.fromisoformat(date_of_birth)
            except ValueError:
                pass

        return cls(
            customer_id=data.get("customer_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            date_of_birth=date_of_birth,
            gender=data.get("gender"),
            email=data.get("email", ""),
            phone=data.get("phone"),
            status=data.get("status", "ACTIVE"),
            pan=data.get("pan"),
            account_number=data.get("account_number"),
            pincode=data.get("pincode"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
            address=data.get("address"),
            risk_level=data.get("risk_level", "LOW"),
            created_at=created_at,
            updated_at=updated_at
        )

    def __str__(self) -> str:
        return f"Customer(ID: {self.customer_id}, Name: {self.first_name} {self.last_name}, Email: {self.email}, Status: {self.status}, PAN: {self.pan}, Account: {self.account_number}, Pincode: {self.pincode})"
