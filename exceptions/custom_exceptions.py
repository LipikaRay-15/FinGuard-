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

