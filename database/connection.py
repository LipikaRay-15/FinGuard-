import mysql.connector
from mysql.connector import Error
from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from logs.logger import get_logger
from exceptions.custom_exceptions import DatabaseException

logger = get_logger(__name__)

class DatabaseConnection:
    """Singleton class for Database Connection."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance.connection = None
        return cls._instance

    def connect(self):
        if self.connection is None or not self.connection.is_connected():
            try:
                self.connection = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME
                )
                logger.info("Successfully connected to the MySQL database.")
            except Error as e:
                logger.error(f"Error while connecting to MySQL: {e}")
                raise DatabaseException(f"Database connection failed: {e}")

    def execute(self, query: str, params: tuple = None):
        self.connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor
        except Error as e:
            logger.error(f"Query execution failed: {query} - Params: {params} - Error: {e}")
            raise DatabaseException(f"Query execution failed: {e}")

    def fetch_one(self, query: str, params: tuple = None) -> dict:
        cursor = self.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    def fetch_all(self, query: str, params: tuple = None) -> list:
        cursor = self.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result

    def commit(self):
        if self.connection and self.connection.is_connected():
            self.connection.commit()

    def rollback(self):
        if self.connection and self.connection.is_connected():
            self.connection.rollback()
            logger.info("Database transaction rolled back.")

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed.")
