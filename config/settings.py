import os
import logging
from dotenv import load_dotenv

# Find the base directory (FinGuard/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")

# Load environment variables from the .env file at the project root
load_dotenv(dotenv_path=env_path)

# MySQL Connection Configurations
MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
try:
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
except ValueError:
    MYSQL_PORT = 3306

MYSQL_USER = os.getenv("MYSQL_USER", os.getenv("DB_USER", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "finguard_db"))

# Crucial compatibility configuration: MySQL C-Extension crash bypass.
# Setting to True forces mysql-connector-python to use the pure Python implementation,
# avoiding segfaults / interpreter crashes on newer Python interpreters on Windows.
MYSQL_USE_PURE = True

# Logging Directory and Log Files Settings
LOGS_DIR = os.path.join(BASE_DIR, "logs")
APPLICATION_LOG = os.path.join(LOGS_DIR, "application.log")
ERROR_LOG = os.path.join(LOGS_DIR, "error.log")
FRAUD_LOG = os.path.join(LOGS_DIR, "fraud.log")

# Backward compatibility aliases for existing codebase components
DB_HOST = MYSQL_HOST
DB_USER = MYSQL_USER
DB_PASSWORD = MYSQL_PASSWORD
DB_NAME = MYSQL_DATABASE
LOG_FILE = APPLICATION_LOG

def setup_logging() -> None:
    """
    Configures the application-wide logging system.
    Generates three separate files for different concerns:
    - application.log: general runtime records (INFO & above)
    - error.log: error, exceptions, and system failures (ERROR & above)
    - fraud.log: transactional fraud alerts and rule hits
    """
    # Create logs directory if it does not exist
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Base log formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Application Log Handler (INFO and above)
    app_handler = logging.FileHandler(APPLICATION_LOG, encoding="utf-8")
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    # 2. Error Log Handler (ERROR and above)
    err_handler = logging.FileHandler(ERROR_LOG, encoding="utf-8")
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(app_handler)
        root_logger.addHandler(err_handler)

    # 3. Fraud-specific Logger & Handler
    fraud_logger = logging.getLogger("finguard.fraud")
    fraud_logger.setLevel(logging.INFO)
    fraud_logger.propagate = False  # Prevent fraud alerts from cluttering the general app logs
    
    if not fraud_logger.handlers:
        fraud_handler = logging.FileHandler(FRAUD_LOG, encoding="utf-8")
        fraud_handler.setLevel(logging.INFO)
        fraud_handler.setFormatter(formatter)
        fraud_logger.addHandler(fraud_handler)

# ── User Preferences Onboarding Helpers ──────────────────────────────────────────
import json

USER_PREFS_FILE = os.path.join(BASE_DIR, "config", "user_preferences.json")

def load_user_preferences() -> dict:
    try:
        if os.path.exists(USER_PREFS_FILE):
            with open(USER_PREFS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"first_run_completed": False}

def save_user_preferences(prefs: dict) -> None:
    try:
        os.makedirs(os.path.dirname(USER_PREFS_FILE), exist_ok=True)
        with open(USER_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4)
    except Exception:
        pass
