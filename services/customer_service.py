import logging
import re
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import (
    CustomerNotFoundException,
    DuplicateCustomerException,
    InvalidCustomerException,
    ValidationException,
    CustomerValidationException
)
from models import Customer, RiskProfile
from repositories import CustomerRepository, RiskProfileRepository
from services.pincode_service import PincodeService

class CustomerService:
    """
    Service class orchestrating business logic for Customer management.
    Integrates validators, repository queries, duplicate preventions,
    and risk profile evaluations.
    """
    def __init__(self) -> None:
        self.customer_repo = CustomerRepository()
        self.risk_repo = RiskProfileRepository()
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.services.customer")

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validates email structure using standard RFC 5322 regex.
        """
        if not email:
            return False
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_mobile(mobile: str) -> bool:
        """
        Validates mobile numbers (+ prefix followed by 10 to 15 digits).
        """
        if not mobile:
            return False
        pattern = r"^\+?[0-9]{10,15}$"
        return bool(re.match(pattern, mobile))

    @staticmethod
    def validate_pan(pan: str) -> bool:
        """
        Validates Indian Permanent Account Number (PAN) format:
        5 uppercase letters, 4 numeric digits, 1 uppercase letter.
        """
        if not pan:
            return False
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        return bool(re.match(pattern, pan.upper()))

    def _check_duplicates(
        self,
        email: str,
        pan: Optional[str],
        account_number: Optional[str],
        exclude_customer_id: Optional[int] = None
    ) -> None:
        """
        Verifies unique constraints before inserts or updates.
        Raises DuplicateCustomerException if a clash is identified.
        """
        # 1. Email check
        clashing_emails = self.customer_repo.search({"email": email})
        for c in clashing_emails:
            if exclude_customer_id is None or c.customer_id != exclude_customer_id:
                self.logger.warning(f"Duplicate check clashing on email: {email}")
                raise DuplicateCustomerException(f"Customer with email '{email}' already exists.")

        # 2. PAN check
        if pan:
            clashing_pans = self.customer_repo.search({"pan": pan})
            for c in clashing_pans:
                if exclude_customer_id is None or c.customer_id != exclude_customer_id:
                    self.logger.warning(f"Duplicate check clashing on PAN: {pan}")
                    raise DuplicateCustomerException(f"Customer with PAN '{pan}' already exists.")

        # 3. Account Number check
        if account_number:
            clashing_accounts = self.customer_repo.search({"account_number": account_number})
            for c in clashing_accounts:
                if exclude_customer_id is None or c.customer_id != exclude_customer_id:
                    self.logger.warning(f"Duplicate check clashing on account number: {account_number}")
                    raise DuplicateCustomerException(f"Customer with account number '{account_number}' already exists.")

    def create_customer(
        self,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: Optional[Any] = None,
        gender: Optional[str] = None,
        phone: Optional[str] = None,
        status: str = "ACTIVE",
        pan: Optional[str] = None,
        account_number: Optional[str] = None,
        pincode: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        address: Optional[str] = None,
        risk_level: str = "LOW"
    ) -> Customer:
        """
        Validates customer attributes and inserts record if no duplicates exist.
        
        Raises:
            CustomerValidationException: If format validation fails.
            DuplicateCustomerException: If clashing fields exist.
        """
        # Auto-fetch location if valid pincode is provided
        if pincode:
            loc = PincodeService.fetch_location_from_pincode(pincode)
            if loc:
                city = loc["city"]
                state = loc["state"]
                country = loc["country"]

        cust = Customer(
            customer_id=None,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            email=email,
            phone=phone,
            status=status,
            pan=pan,
            account_number=account_number,
            pincode=pincode,
            city=city,
            state=state,
            country=country,
            address=address,
            risk_level=risk_level
        )
        
        # Call validate first to collect format validation errors
        cust.validate()

        # Prevent duplicate entries
        self._check_duplicates(email, pan, account_number)

        try:
            saved = self.customer_repo.create(cust)
            self.db.commit()
            
            # Audit log
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="CREATE_CUSTOMER",
                affected_table="customers",
                record_id=saved.customer_id,
                old_values=None,
                new_values=saved.to_dict(),
                performed_by="SYSTEM"
            )
            return saved

        except Exception as e:
            self.db.rollback()
            if isinstance(e, CustomerValidationException):
                raise
            if isinstance(e, ValidationException):
                raise InvalidCustomerException(f"Validation failure: {e}")
            raise

    def update_customer(
        self,
        customer_id: int,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: Optional[Any] = None,
        gender: Optional[str] = None,
        phone: Optional[str] = None,
        status: str = "ACTIVE",
        pan: Optional[str] = None,
        account_number: Optional[str] = None,
        pincode: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        address: Optional[str] = None,
        risk_level: str = "LOW"
    ) -> None:
        """
        Modifies properties of an existing customer record.
        
        Raises:
            CustomerNotFoundException: If customer does not exist.
            CustomerValidationException: If format validations fail.
            DuplicateCustomerException: If updates clash with another customer's properties.
        """
        # Confirm existence
        cust = self.customer_repo.find_by_id(customer_id)
        if not cust:
            self.logger.error(f"Failed updating: Customer ID {customer_id} not found.")
            raise CustomerNotFoundException(f"Customer with ID {customer_id} does not exist.")

        old_values = cust.to_dict()

        # Auto-fetch location if valid pincode is provided
        if pincode:
            loc = PincodeService.fetch_location_from_pincode(pincode)
            if loc:
                city = loc["city"]
                state = loc["state"]
                country = loc["country"]

        # Update fields
        cust.first_name = first_name
        cust.last_name = last_name
        cust.date_of_birth = date_of_birth
        cust.gender = gender
        cust.email = email
        cust.phone = phone
        cust.status = status
        cust.pan = pan
        cust.account_number = account_number
        cust.pincode = pincode
        cust.city = city
        cust.state = state
        cust.country = country
        cust.address = address
        cust.risk_level = risk_level

        # Call validate first to collect format validation errors
        cust.validate()

        # Check for clashing duplicates excluding the current customer
        self._check_duplicates(email, pan, account_number, exclude_customer_id=customer_id)

        try:
            self.customer_repo.update(cust)
            self.db.commit()
            self.logger.info(f"Successfully updated customer ID {customer_id}")
            from engines.event_manager import EventManager
            EventManager().log_event(
                event_type="CUSTOMER_UPDATED",
                entity_type="CUSTOMER",
                entity_id=customer_id,
                details={"email": email, "status": status}
            )
            
            # Audit log
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="UPDATE_CUSTOMER",
                affected_table="customers",
                record_id=customer_id,
                old_values=old_values,
                new_values=cust.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as ve:
            self.db.rollback()
            if isinstance(ve, CustomerValidationException):
                raise
            if isinstance(ve, ValidationException):
                raise InvalidCustomerException(f"Validation failure: {ve}")
            raise

    def delete_customer(self, customer_id: int) -> None:
        """
        Removes customer profile.
        
        Raises:
            CustomerNotFoundException: If customer does not exist.
        """
        cust = self.customer_repo.find_by_id(customer_id)
        if not cust:
            self.logger.error(f"Failed deletion: Customer ID {customer_id} not found.")
            raise CustomerNotFoundException(f"Customer with ID {customer_id} does not exist.")
            
        old_values = cust.to_dict()
        try:
            self.customer_repo.delete(customer_id)
            self.db.commit()
            self.logger.info(f"Successfully deleted customer ID {customer_id}")
            
            # Audit log
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="DELETE_CUSTOMER",
                affected_table="customers",
                record_id=customer_id,
                old_values=old_values,
                new_values=None,
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            raise

    def get_customer_by_id(self, customer_id: int) -> Customer:
        """
        Gets customer by id.
        
        Raises:
            CustomerNotFoundException: If customer does not exist.
        """
        cust = self.customer_repo.find_by_id(customer_id)
        if not cust:
            raise CustomerNotFoundException(f"Customer with ID {customer_id} does not exist.")
        return cust

    def search_customer(self, filters: Dict[str, Any]) -> List[Customer]:
        """
        Queries customers matching key-value constraints.
        """
        return self.customer_repo.search(filters)

    def change_risk_level(self, customer_id: int, new_score: int, new_tier: str) -> None:
        """
        Recalibrates current risk metrics, updating or initializing risk profile settings.
        
        Raises:
            CustomerNotFoundException: If customer does not exist.
            InvalidCustomerException: If risk tier or score violates boundary constraints.
        """
        # Validate customer existance
        cust = self.customer_repo.find_by_id(customer_id)
        if not cust:
            raise CustomerNotFoundException(f"Customer with ID {customer_id} does not exist.")

        # Validate risk parameters
        if not (0 <= new_score <= 100):
            raise InvalidCustomerException(f"Risk score must be between 0 and 100. Got: {new_score}")
        if new_tier not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise InvalidCustomerException(f"Invalid risk tier: '{new_tier}'. Expected: LOW, MEDIUM, HIGH, CRITICAL.")

        try:
            # Query existing profile
            profiles = self.risk_repo.search({"customer_id": customer_id})
            if profiles:
                profile = profiles[0]
                profile.current_risk_score = new_score
                profile.risk_tier = new_tier
                self.risk_repo.update(profile)
                self.logger.info(f"Updated risk profile for customer {customer_id} (Score={new_score}, Tier={new_tier})")
            else:
                profile = RiskProfile(
                    profile_id=None,
                    customer_id=customer_id,
                    current_risk_score=new_score,
                    risk_tier=new_tier
                )
                self.risk_repo.create(profile)
                self.logger.info(f"Created risk profile for customer {customer_id} (Score={new_score}, Tier={new_tier})")
        except ValidationException as ve:
            raise InvalidCustomerException(f"Risk evaluation constraint failure: {ve}")
