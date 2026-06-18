import os
import json
import mysql.connector
from mysql.connector import Error
from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from logs.logger import get_logger

logger = get_logger(__name__)

def get_mysql_connection_without_db():
    """Establishes connection to the MySQL server without specifying a database."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )

def initialize_database():
    """Initializes the database by dropping/recreating it and running the SQL schema."""
    schema_path = os.path.join(os.path.dirname(__file__), "db_schema.sql")
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at: {schema_path}")
        print(f"Error: Schema file not found at: {schema_path}")
        return False

    try:
        # Step 1: Create the database
        logger.info("Connecting to MySQL to recreate the database...")
        conn = get_mysql_connection_without_db()
        cursor = conn.cursor()
        
        # Recreate database
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
        cursor.execute(f"CREATE DATABASE {DB_NAME};")
        logger.info(f"Database '{DB_NAME}' created successfully.")
        cursor.close()
        conn.close()

        # Step 2: Run schema script
        logger.info(f"Connecting to database '{DB_NAME}' to initialize schema...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()

        # Read schema file
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Execute statements (handling multiple statements separated by ';')
        statements = schema_sql.split(";")
        for stmt in statements:
            cleaned_stmt = stmt.strip()
            if cleaned_stmt and not cleaned_stmt.startswith("--"):
                try:
                    cursor.execute(cleaned_stmt)
                except Error as e:
                    logger.error(f"Error executing statement: {cleaned_stmt[:100]}... Error: {e}")
                    raise e
        
        conn.commit()
        logger.info("Database schema initialized successfully.")

        # Step 3: Seed Default Rules
        seed_default_rules(cursor)
        conn.commit()

        cursor.close()
        conn.close()
        print("Database initialization completed successfully!")
        return True

    except Error as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"Error: Database initialization failed: {e}")
        return False

def seed_default_rules(cursor):
    """Seeds default rules into the rules table."""
    logger.info("Seeding default rules...")
    default_rules = [
        {
            "name": "High Transaction Amount",
            "description": "Flags any transaction where the amount exceeds $10,000.",
            "criteria_json": json.dumps({"max_amount": 10000.0, "risk_score": 75})
        },
        {
            "name": "Rapid Velocity Limit",
            "description": "Flags accounts initiating more than 3 transactions within a 5-minute window.",
            "criteria_json": json.dumps({"max_transactions": 3, "time_window_minutes": 5, "risk_score": 80})
        },
        {
            "name": "Impossible Location Velocity",
            "description": "Flags physical transactions occurring in different locations at speed exceeding travel capabilities (>150 km/h).",
            "criteria_json": json.dumps({"max_speed_kmh": 150.0, "risk_score": 85})
        },
        {
            "name": "High-Risk Merchant Category",
            "description": "Flags transactions happening at high-risk categories like casinos, gambling sites, and cryptocurrency brokers.",
            "criteria_json": json.dumps({"flagged_categories": ["Gambling", "Casino", "Cryptocurrency"], "risk_score": 60})
        }
    ]

    for rule in default_rules:
        cursor.execute(
            "INSERT INTO rules (name, description, criteria_json, is_active) VALUES (%s, %s, %s, TRUE);",
            (rule["name"], rule["description"], rule["criteria_json"])
        )
    logger.info("Default rules seeded successfully.")

if __name__ == "__main__":
    initialize_database()
