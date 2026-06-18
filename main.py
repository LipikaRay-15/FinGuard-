#!/usr/bin/env python3
"""
FinGuard - Intelligent Financial Fraud & Risk Monitoring Platform
Module 0: Startup Verification and Environment Validation Checks
"""

import sys
import logging
import importlib
from typing import Dict, Tuple

# Pre-define basic ASCII color codes in case colorama is not yet available
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def check_python_version() -> Tuple[bool, str]:
    """
    Verifies that the running Python version meets the required standard (>= 3.8).
    """
    req_version = (3, 8)
    curr_version = sys.version_info
    version_str = f"{curr_version.major}.{curr_version.minor}.{curr_version.micro}"
    
    if curr_version >= req_version:
        return True, f"Python {version_str} (Compatible)"
    else:
        return False, f"Python {version_str} (Incompatible: Requires >= 3.8)"

def check_libraries() -> Tuple[bool, Dict[str, str]]:
    """
    Verify whether the required third-party libraries list in requirements.txt
    are installed in the active environment.
    """
    required_libs = {
        "mysql.connector": "mysql-connector-python",
        "pandas": "pandas",
        "numpy": "numpy",
        "faker": "Faker",
        "schedule": "schedule",
        "tabulate": "tabulate",
        "colorama": "colorama",
        "dotenv": "python-dotenv"
    }
    
    results = {}
    all_ok = True
    
    for module_name, pip_name in required_libs.items():
        try:
            importlib.import_module(module_name)
            results[pip_name] = "PASSED"
        except ImportError:
            results[pip_name] = "FAILED (Missing)"
            all_ok = False
            
    return all_ok, results

def test_mysql_connection() -> Tuple[bool, str]:
    """
    Validates connection parameters and tests connection with the MySQL server.
    Loads configurations from settings.py.
    """
    try:
        from config import settings
        import mysql.connector
        
        # Log connection attempt details
        logging.info(
            f"Starting connection check for database client: host={settings.MYSQL_HOST}, "
            f"port={settings.MYSQL_PORT}, user={settings.MYSQL_USER}, database={settings.MYSQL_DATABASE}"
        )
        
        # Connect to database using configuration options
        # Note: use_pure=settings.MYSQL_USE_PURE is True to circumvent C-extension crash on Python 3.13 Windows venvs.
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            use_pure=settings.MYSQL_USE_PURE
        )
        
        server_info = conn.server_info
        conn.close()
        
        logging.info("MySQL verification connection completed successfully.")
        return True, f"Connected (Server: {server_info})"
    except Exception as e:
        error_msg = f"Connection failed: {str(e)}"
        logging.error(f"MySQL verification failed. Connection error details: {error_msg}", exc_info=True)
        return False, error_msg

def main() -> None:
    """
    System entry point for platform verification.
    """
    # 1. Verify custom exceptions load properly
    try:
        from exceptions import (
            DatabaseException,
            ValidationException,
            RuleException,
            TransactionException,
            FraudDetectionException,
            CaseException,
        )
        exceptions_ok = True
        exceptions_msg = "Exceptions classes loaded successfully"
    except ImportError as e:
        exceptions_ok = False
        exceptions_msg = f"Failed to load custom exceptions: {str(e)}"

    # 2. Run runtime tests
    py_ok, py_msg = check_python_version()
    libs_ok, lib_results = check_libraries()
    
    config_ok = False
    config_msg = "Skipped (Dependencies missing)"
    db_ok = False
    db_msg = "Skipped (Dependencies missing)"
    
    # 3. Setup configurations & Logging if dependencies are met
    if libs_ok:
        try:
            from config import settings
            # Initialize logging configuration mapping to logs/ folder
            settings.setup_logging()
            logging.info("=========================================")
            logging.info("Starting FinGuard Platform Verification")
            logging.info("=========================================")
            config_ok = True
            config_msg = "Configurations loaded successfully"
            
            # Test connection to MySQL database
            db_ok, db_msg = test_mysql_connection()
        except Exception as e:
            config_msg = f"Failure loading configuration settings: {str(e)}"
            logging.error(f"Settings setup error: {config_msg}", exc_info=True)
            
    # 4. Print results
    try:
        # Import styling libraries
        import colorama
        from tabulate import tabulate
        colorama.init(autoreset=True)
        
        c_green = colorama.Fore.GREEN + colorama.Style.BRIGHT
        c_red = colorama.Fore.RED + colorama.Style.BRIGHT
        c_yellow = colorama.Fore.YELLOW + colorama.Style.BRIGHT
        c_cyan = colorama.Fore.CYAN + colorama.Style.BRIGHT
        c_reset = colorama.Style.RESET_ALL
        
        print(f"\n{c_cyan}========================================================================")
        print(f"       FinGuard - Intelligent Financial Fraud & Risk Monitoring")
        print(f"                      Startup Verification Checks")
        print(f"========================================================================{c_reset}\n")
        
        core_checks = [
            ["Python Version Compatibility", py_msg, c_green + "PASS" if py_ok else c_red + "FAIL"],
            ["Enterprise Custom Exceptions", exceptions_msg, c_green + "PASS" if exceptions_ok else c_red + "FAIL"],
            ["Configuration Variables Setup", config_msg, c_green + "PASS" if config_ok else c_red + "FAIL"],
            ["MySQL Connection (use_pure=True)", db_msg, c_green + "PASS" if db_ok else c_red + "FAIL"]
        ]
        
        print(tabulate(core_checks, headers=["System Component Check", "Diagnostics / Information", "Status"], tablefmt="grid"))
        
        print(f"\n{c_cyan}------------------------------------------------------------------------")
        print("                 Python Dependency Libraries Check")
        print(f"------------------------------------------------------------------------{c_reset}\n")
        
        lib_statuses = []
        for name, stat in lib_results.items():
            status_text = c_green + "AVAILABLE" if stat == "PASSED" else c_red + "MISSING"
            lib_statuses.append([name, status_text])
            
        print(tabulate(lib_statuses, headers=["Python Library", "Import Status"], tablefmt="simple"))
        print("\n")
        
    except ImportError:
        # Fallback to plain print statements if styling libs are not loaded
        print("\n========================================================================")
        print("       FinGuard - Intelligent Financial Fraud & Risk Monitoring")
        print("                      Startup Verification Checks")
        print("========================================================================\n")
        print(f"Python Version Compatibility: {py_msg} -> {'PASS' if py_ok else 'FAIL'}")
        print(f"Enterprise Custom Exceptions: {exceptions_msg} -> {'PASS' if exceptions_ok else 'FAIL'}")
        print(f"Configuration Variables Setup: {config_msg} -> {'PASS' if config_ok else 'FAIL'}")
        print(f"MySQL Connection (use_pure=True): {db_msg} -> {'PASS' if db_ok else 'FAIL'}")
        print("\nDependency Libraries Status:")
        for name, stat in lib_results.items():
            print(f"  - {name}: {stat}")
        print("\n")

    # 5. Check if all required setup components are ready
    system_ready = py_ok and exceptions_ok and libs_ok and config_ok and db_ok
    
    if system_ready:
        print(f"{GREEN}SUCCESS: All verification checks passed. FinGuard platform is ready.{RESET}\n")
        logging.info("Verification checks completed. FinGuard platform is ready.")
        sys.exit(0)
    else:
        print(f"{RED}ERROR: Environment validation failed. Review the logs/error.log file.{RESET}\n")
        if libs_ok:
            logging.critical("Validation failed. One or more components are not ready.")
        sys.exit(1)

if __name__ == "__main__":
    main()
