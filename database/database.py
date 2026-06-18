import logging
import threading
from typing import Any, Dict, List, Optional
import mysql.connector
from mysql.connector import Error

from config import settings
from exceptions import ConnectionException, QueryExecutionException

class DatabaseConnection:
    """
    Thread-safe Singleton Connection Manager for MySQL.
    Provides standard methods for queries execution, transaction control,
    and automatic reconnection handling.
    """
    _instance: Optional['DatabaseConnection'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'DatabaseConnection':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseConnection, cls).__new__(cls)
                cls._instance._connection = None
                cls._instance._logger = logging.getLogger("finguard.database")
        return cls._instance

    def connect(self) -> None:
        """
        Establishes a connection to the MySQL database.
        If a connection is already active, this method is a no-op.
        
        Raises:
            ConnectionException: If the connection attempt fails.
        """
        if self._connection is not None and self._connection.is_connected():
            self._logger.debug("Database connection already established.")
            return

        try:
            self._logger.info(
                f"Establishing connection to MySQL server at {settings.MYSQL_HOST}:{settings.MYSQL_PORT} "
                f"for database: {settings.MYSQL_DATABASE}"
            )
            # Connecting to database using settings configurations
            # Note: use_pure=settings.MYSQL_USE_PURE is critical on Windows venvs to avoid interpreter crash.
            self._connection = mysql.connector.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                use_pure=settings.MYSQL_USE_PURE
            )
            self._logger.info("Successfully connected to MySQL database.")
        except Error as e:
            self._logger.error(f"Failed to connect to MySQL database: {e}", exc_info=True)
            raise ConnectionException(f"Database connection failed: {e}")

    def disconnect(self) -> None:
        """
        Closes the active database connection if it exists.
        """
        if self._connection is not None:
            try:
                if self._connection.is_connected():
                    self._connection.close()
                    self._logger.info("MySQL database connection closed successfully.")
            except Error as e:
                self._logger.warning(f"Error occurred while closing the connection: {e}")
            finally:
                self._connection = None

    def close(self) -> None:
        """
        Alias for disconnect() to provide compatibility.
        """
        self.disconnect()

    def _validate_and_reconnect(self) -> None:
        """
        Checks if the database connection is open and active.
        If the connection has been lost, automatically reconnects.
        
        Raises:
            ConnectionException: If reconnection fails.
        """
        if self._connection is None:
            self.connect()
            return

        try:
            # ping checks connection health and automatically attempts to reconnect if broken
            self._connection.ping(reconnect=True, attempts=3, delay=2)
        except Error:
            self._logger.warning("Database connection lost. Attempting manual reconnection...")
            self.connect()

    def execute(self, query: str, params: Optional[tuple] = None) -> mysql.connector.cursor.MySQLCursor:
        """
        Executes an SQL query (e.g. INSERT, UPDATE, DELETE).
        
        Args:
            query: The SQL query string.
            params: Tuple of query parameters.
            
        Returns:
            The cursor object.
            
        Raises:
            QueryExecutionException: If query execution fails.
        """
        self._validate_and_reconnect()
        # Ensure we always get results as dictionary rows
        cursor = self._connection.cursor(dictionary=True)
        try:
            self._logger.debug(f"Executing Query: {query} | Params: {params}")
            cursor.execute(query, params)
            return cursor
        except Error as e:
            self._logger.error(f"Query execution failed: {query} | Params: {params} | Error: {e}", exc_info=True)
            raise QueryExecutionException(f"Failed to execute SQL query: {e}")

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Executes a query and fetches the first result row as a dictionary.
        
        Args:
            query: The SELECT query string.
            params: Tuple of query parameters.
            
        Returns:
            Dictionary representing the row, or None if no record is found.
            
        Raises:
            QueryExecutionException: If query execution fails.
        """
        self._validate_and_reconnect()
        cursor = self._connection.cursor(dictionary=True)
        try:
            self._logger.debug(f"Fetching One: {query} | Params: {params}")
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            cursor.close()
            self._logger.error(f"Fetch one failed: {query} | Params: {params} | Error: {e}", exc_info=True)
            raise QueryExecutionException(f"Failed to fetch record: {e}")

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Executes a query and fetches all result rows as a list of dictionaries.
        
        Args:
            query: The SELECT query string.
            params: Tuple of query parameters.
            
        Returns:
            List of dictionaries representing the rows.
            
        Raises:
            QueryExecutionException: If query execution fails.
        """
        self._validate_and_reconnect()
        cursor = self._connection.cursor(dictionary=True)
        try:
            self._logger.debug(f"Fetching All: {query} | Params: {params}")
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            cursor.close()
            self._logger.error(f"Fetch all failed: {query} | Params: {params} | Error: {e}", exc_info=True)
            raise QueryExecutionException(f"Failed to fetch records: {e}")

    def commit(self) -> None:
        """
        Commits the current transaction.
        
        Raises:
            QueryExecutionException: If commit fails.
        """
        if self._connection is not None:
            try:
                self._connection.commit()
                self._logger.debug("Database transaction committed successfully.")
            except Error as e:
                self._logger.error(f"Failed to commit transaction: {e}", exc_info=True)
                raise QueryExecutionException(f"Failed to commit database transaction: {e}")

    def rollback(self) -> None:
        """
        Rolls back the current transaction.
        
        Raises:
            QueryExecutionException: If rollback fails.
        """
        if self._connection is not None:
            try:
                self._connection.rollback()
                self._logger.info("Database transaction rolled back successfully.")
            except Error as e:
                self._logger.error(f"Failed to rollback transaction: {e}", exc_info=True)
                raise QueryExecutionException(f"Failed to rollback database transaction: {e}")
