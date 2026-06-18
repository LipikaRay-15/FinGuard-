import re
from datetime import datetime, date
from typing import Any, List
from exceptions import (
    FirstNameValidationError,
    LastNameValidationError,
    DOBValidationError,
    GenderValidationError,
    EmailValidationError,
    PhoneValidationError,
    PANValidationError,
    AccountNumberValidationError,
    PincodeValidationError,
    AddressValidationError,
    CustomerValidationException
)

class CustomerValidator:
    """
    Utility class implementing robust and specific validations for customer fields.
    Collects validation errors rather than raising them immediately.
    """

    @staticmethod
    def validate_first_name(first_name: str) -> None:
        if not first_name or not isinstance(first_name, str) or not first_name.strip():
            raise FirstNameValidationError("Invalid First Name")
        val = first_name.strip()
        if not re.match(r"^[a-zA-Z]+$", val) or not (2 <= len(val) <= 50):
            raise FirstNameValidationError("Invalid First Name")

    @staticmethod
    def validate_last_name(last_name: str) -> None:
        if not last_name or not isinstance(last_name, str) or not last_name.strip():
            raise LastNameValidationError("Invalid Last Name")
        val = last_name.strip()
        if not re.match(r"^[a-zA-Z]+$", val) or not (2 <= len(val) <= 50):
            raise LastNameValidationError("Invalid Last Name")

    @staticmethod
    def validate_date_of_birth(dob: Any) -> None:
        if dob is None:
            return
        
        dob_date = None
        if isinstance(dob, (date, datetime)):
            dob_date = dob if isinstance(dob, date) else dob.date()
        elif isinstance(dob, str):
            if not dob.strip():
                raise DOBValidationError("Invalid Date of Birth")
            try:
                dob_date = datetime.strptime(dob.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise DOBValidationError("Invalid Date of Birth")
        else:
            raise DOBValidationError("Invalid Date of Birth")

        today = date.today()
        if dob_date > today:
            raise DOBValidationError("Invalid Date of Birth")

        # Age calculation
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        if age < 18:
            raise DOBValidationError("Invalid Date of Birth")

    @staticmethod
    def validate_gender(gender: str) -> None:
        if gender is None:
            return
        if not isinstance(gender, str) or gender.strip() not in ("Male", "Female", "Other", "Prefer not to say"):
            raise GenderValidationError("Invalid Gender")

    @staticmethod
    def validate_email(email: str) -> None:
        if not email or not isinstance(email, str) or not email.strip():
            raise EmailValidationError("Invalid Email")
        val = email.strip()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, val):
            raise EmailValidationError("Invalid Email")

    @staticmethod
    def validate_phone(phone: str) -> None:
        if phone is None:
            return
        if not isinstance(phone, str) or not phone.strip():
            raise PhoneValidationError("Invalid Phone Number")
        val = phone.strip()
        pattern = r"^\+?[0-9]{10,15}$"
        if not re.match(pattern, val):
            raise PhoneValidationError("Invalid Phone Number")

    @staticmethod
    def validate_pan(pan: str) -> None:
        if pan is None:
            return
        if not isinstance(pan, str) or not pan.strip():
            raise PANValidationError("Invalid PAN")
        val = pan.strip().upper()
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        if not re.match(pattern, val):
            raise PANValidationError("Invalid PAN")

    @staticmethod
    def validate_account_number(account_number: str) -> None:
        if account_number is None:
            return
        if not isinstance(account_number, str) or not account_number.strip():
            raise AccountNumberValidationError("Invalid Account Number")
        val = account_number.strip()
        pattern = r"^\d{8,18}$"
        if not re.match(pattern, val):
            raise AccountNumberValidationError("Invalid Account Number")

    @staticmethod
    def validate_pincode(pincode: str) -> None:
        if pincode is None:
            raise PincodeValidationError("Invalid Pincode")
        if not isinstance(pincode, str) or not pincode.strip():
            raise PincodeValidationError("Invalid Pincode")
        val = pincode.strip()
        pattern = r"^\d{6}$"
        if not re.match(pattern, val):
            raise PincodeValidationError("Invalid Pincode")

    @staticmethod
    def validate_address(address: str) -> None:
        if address is None:
            return
        if not isinstance(address, str) or not address.strip():
            raise AddressValidationError("Address too short")
        val = address.strip()
        if len(val) < 10:
            raise AddressValidationError("Address too short")
        if len(val) > 200:
            raise AddressValidationError("Address too long")

    @classmethod
    def validate_customer(cls, customer) -> None:
        """
        Executes validations across all attributes. Collects errors and raises CustomerValidationException if any occur.
        """
        errors: List[str] = []
        
        # 1. First Name
        try:
            cls.validate_first_name(customer.first_name)
        except FirstNameValidationError as e:
            errors.append(str(e))

        # 2. Last Name
        try:
            cls.validate_last_name(customer.last_name)
        except LastNameValidationError as e:
            errors.append(str(e))

        # 3. Date of Birth
        try:
            cls.validate_date_of_birth(customer.date_of_birth)
        except DOBValidationError as e:
            errors.append(str(e))

        # 4. Gender
        try:
            cls.validate_gender(customer.gender)
        except GenderValidationError as e:
            errors.append(str(e))

        # 5. Email
        try:
            cls.validate_email(customer.email)
        except EmailValidationError as e:
            errors.append(str(e))

        # 6. Phone
        try:
            cls.validate_phone(customer.phone)
        except PhoneValidationError as e:
            errors.append(str(e))

        # 7. PAN
        try:
            cls.validate_pan(customer.pan)
        except PANValidationError as e:
            errors.append(str(e))

        # 8. Account Number
        try:
            cls.validate_account_number(customer.account_number)
        except AccountNumberValidationError as e:
            errors.append(str(e))

        # 9. Pincode
        try:
            cls.validate_pincode(customer.pincode)
        except PincodeValidationError as e:
            errors.append(str(e))

        # 10. Address
        try:
            cls.validate_address(customer.address)
        except AddressValidationError as e:
            errors.append(str(e))

        # 11. Status check
        if customer.status not in ("ACTIVE", "SUSPENDED", "BLOCKED", "INACTIVE"):
            errors.append(f"Invalid customer status: '{customer.status}'. Expected: ACTIVE, SUSPENDED, BLOCKED, INACTIVE.")

        if errors:
            raise CustomerValidationException(errors)
