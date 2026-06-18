class DatabaseException(Exception):
    """Exception raised for errors in the database operations."""
    pass

class ValidationException(Exception):
    """Exception raised for errors in data validation."""
    pass

class RuleException(Exception):
    """Exception raised for errors in rule execution or parsing."""
    pass

class TransactionException(Exception):
    """Exception raised for errors processing a transaction."""
    pass

class TransactionNotFoundException(TransactionException):
    """Exception raised when a transaction is not found."""
    pass

class InvalidTransactionException(TransactionException):
    """Exception raised when a transaction validation fails."""
    pass

class FraudDetectionException(Exception):
    """Exception raised during fraud detection."""
    pass

class CaseException(Exception):
    """Exception raised for case management errors (like invalid state transitions)."""
    pass

class ConnectionException(DatabaseException):
    """Exception raised for database connection failures."""
    pass

class QueryExecutionException(DatabaseException):
    """Exception raised for query execution failures."""
    pass

class CustomerNotFoundException(Exception):
    """Exception raised when a requested customer is not found."""
    pass

class DuplicateCustomerException(Exception):
    """Exception raised when trying to create a customer with duplicate fields (email, PAN, account)."""
    pass

class InvalidCustomerException(Exception):
    """Exception raised when validation or formatting checks fail for a customer."""
    pass

class DeviceNotFoundException(Exception):
    """Exception raised when a requested device fingerprint or ID is not found."""
    pass

class DuplicateDeviceException(Exception):
    """Exception raised when attempting to register a device with duplicate unique properties."""
    pass

class InvalidDeviceException(Exception):
    """Exception raised when validation or formatting checks fail for a device."""
    pass


class CustomerValidationError(ValidationException):
    """Base exception for all customer attribute validation failures."""
    pass

class FirstNameValidationError(CustomerValidationError):
    """Raised when first name validation fails."""
    pass

class LastNameValidationError(CustomerValidationError):
    """Raised when last name validation fails."""
    pass

class DOBValidationError(CustomerValidationError):
    """Raised when date of birth validation fails."""
    pass

class GenderValidationError(CustomerValidationError):
    """Raised when gender validation fails."""
    pass

class EmailValidationError(CustomerValidationError):
    """Raised when email validation fails."""
    pass

class PhoneValidationError(CustomerValidationError):
    """Raised when phone number validation fails."""
    pass

class PANValidationError(CustomerValidationError):
    """Raised when PAN validation fails."""
    pass

class AccountNumberValidationError(CustomerValidationError):
    """Raised when account number validation fails."""
    pass

class CityValidationError(CustomerValidationError):
    """Raised when city validation fails."""
    pass

class AddressValidationError(CustomerValidationError):
    """Raised when address validation fails."""
    pass

class PincodeValidationError(CustomerValidationError):
    """Raised when pincode validation fails."""
    pass

class CustomerValidationException(ValidationException):
    """Exception that aggregates multiple customer validation errors."""
    def __init__(self, errors: list) -> None:
        self.errors = errors
        message = "Validation Errors\n" + "\n".join(f"❌ {err}" for err in errors) + "\nPlease correct the above fields."
        super().__init__(message)


