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

