#!/usr/bin/env python3
"""
FinGuard - Intelligent Financial Fraud & Risk Monitoring Platform
Module 20: Production CLI Menu and Integration Shell
"""

import sys
import logging
import importlib
from typing import Dict, Tuple
from decimal import Decimal

# Pre-define basic ASCII color codes
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
    Verify whether the required third-party libraries listed in requirements.txt
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
        
        logging.info(
            f"Starting connection check for database client: host={settings.MYSQL_HOST}, "
            f"port={settings.MYSQL_PORT}, user={settings.MYSQL_USER}, database={settings.MYSQL_DATABASE}"
        )
        
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

# =========================================================================
# CLI SUBMENU HELPERS
# =========================================================================

def menu_add_customer():
    from services import CustomerService, PincodeService
    from exceptions import CustomerValidationException
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            1. ADD NEW CUSTOMER")
    print(f"{CYAN}=========================================={RESET}")
    first_name = input("Enter First Name: ").strip() or None
    last_name = input("Enter Last Name: ").strip() or None
    date_of_birth = input("Enter Date of Birth (YYYY-MM-DD): ").strip() or None
    gender = input("Enter Gender (Male/Female/Other/Prefer not to say): ").strip() or None
    email = input("Enter Email: ").strip() or None
    phone = input("Enter Phone: ").strip() or None
    pan = input("Enter Indian PAN (e.g., ABCDE1234F): ").strip().upper() or None
    account_number = input("Enter Account Number: ").strip() or None
    pincode = input("Enter Indian Pincode: ").strip() or None
    address = input("Enter Address: ").strip() or None
    
    # Auto-resolve location
    city, state, country = None, None, None
    if pincode:
        loc = PincodeService.fetch_location_from_pincode(pincode)
        if loc:
            city = loc["city"]
            state = loc["state"]
            country = loc["country"]
            print(f"{GREEN}Auto-resolved location:{RESET} City={city}, State={state}, Country={country}")

    try:
        service = CustomerService()
        customer = service.create_customer(
            first_name=first_name,
            last_name=last_name,
            email=email,
            date_of_birth=date_of_birth,
            gender=gender,
            phone=phone,
            pan=pan,
            account_number=account_number,
            pincode=pincode,
            city=city,
            state=state,
            country=country,
            address=address,
            risk_level="LOW"
        )
        print(f"\n{GREEN}Success: Customer created successfully with ID: {customer.customer_id}{RESET}")
    except CustomerValidationException as e:
        print(f"\n{RED}{e}{RESET}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

def menu_create_transaction():
    from services import TransactionService
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            2. CREATE TRANSACTION")
    print(f"{CYAN}=========================================={RESET}")
    try:
        customer_id = int(input("Enter Customer ID: ").strip())
        amount = Decimal(input("Enter Amount: ").strip())
    except Exception:
        print(f"{RED}Error: Customer ID must be an integer, and Amount must be a decimal.{RESET}")
        return
        
    city = input("Enter City (MUMBAI, NEW YORK, LONDON, TOKYO, PARIS, LAS VEGAS, optional): ").strip() or None
    merchant_category = input("Enter Merchant Category (GAMBLING, CASINO, SUPERMARKET, optional): ").strip() or None
    device_fingerprint = input("Enter Device Fingerprint Hash (optional): ").strip() or None
    currency = input("Enter Currency (default: USD): ").strip() or "USD"
    transaction_type = input("Enter Transaction Type (PURCHASE/WITHDRAWAL/TRANSFER/DEPOSIT, default: PURCHASE): ").strip().upper() or "PURCHASE"
    
    try:
        service = TransactionService()
        tx = service.create_transaction(
            customer_id=customer_id,
            amount=amount,
            city=city,
            merchant_category=merchant_category,
            device_fingerprint=device_fingerprint,
            currency=currency,
            transaction_type=transaction_type
        )
        saved_tx = service.save_transaction(tx)
        print(f"\n{GREEN}Success: Transaction registered successfully.{RESET}")
        print(f"Transaction ID: {saved_tx.transaction_id}")
        print(f"Risk Decision:  {saved_tx.status}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

def menu_run_fraud_detection():
    from engines import FraudDetectionEngine
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            3. RUN FRAUD DETECTION")
    print(f"{CYAN}=========================================={RESET}")
    try:
        transaction_id = int(input("Enter Transaction ID to scan: ").strip())
    except ValueError:
        print(f"{RED}Error: Transaction ID must be an integer.{RESET}")
        return
        
    try:
        engine = FraudDetectionEngine()
        result = engine.detect_fraud(transaction_id)
        print(f"\n{GREEN}Scan Completed for Transaction ID: {result['transaction_id']}{RESET}")
        print(f"Risk Score:     {result['risk_score']}/100")
        print(f"Severity Level: {result['severity']}")
        print(f"Rule Executions Breakdown:")
        if result['triggered_rules']:
            for rule in result['triggered_rules']:
                print(f"  {RED}✓ {rule['rule_name']} (+{rule['risk_points']} points){RESET}")
                print(f"    Reason: {rule.get('reason', '')}")
        else:
            print(f"  {GREEN}No rules triggered.{RESET}")
            
        try:
            from services.risk_explanation_service import RiskExplanationService
            explanation_service = RiskExplanationService()
            explanation = explanation_service.generate_explanation(transaction_id)
            print(f"\n{CYAN}--- Human-Readable Risk Explanation ---{RESET}")
            print(explanation)
        except Exception:
            pass
            
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

def menu_alerts():
    from services import AlertService
    alert_service = AlertService()
    from tabulate import tabulate
    
    while True:
        print(f"\n{CYAN}=========================================={RESET}")
        print(f"            4. ALERTS LIFE-CYCLE SUBMENU")
        print(f"{CYAN}=========================================={RESET}")
        print("1. View Open/Under-Review Alerts")
        print("2. View Customer Alert History")
        print("3. Update Alert Status")
        print("4. Escalate Alert")
        print("5. Back to Main Menu")
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            try:
                alerts = alert_service.get_open_alerts()
                if not alerts:
                    print(f"\n{GREEN}No open alerts in database.{RESET}")
                else:
                    data = [[a.alert_id, a.transaction_id, a.customer_id, a.risk_score, a.severity, a.status] for a in alerts]
                    print("\n" + tabulate(data, headers=["Alert ID", "TX ID", "Cust ID", "Risk", "Severity", "Status"], tablefmt="grid"))
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "2":
            try:
                customer_id = int(input("Enter Customer ID: ").strip())
                alerts = alert_service.get_alert_history(customer_id)
                if not alerts:
                    print(f"\n{GREEN}No alert history found for customer {customer_id}.{RESET}")
                else:
                    data = [[a.alert_id, a.transaction_id, a.customer_id, a.risk_score, a.severity, a.status] for a in alerts]
                    print("\n" + tabulate(data, headers=["Alert ID", "TX ID", "Cust ID", "Risk", "Severity", "Status"], tablefmt="grid"))
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "3":
            try:
                alert_id = int(input("Enter Alert ID: ").strip())
                print("Statuses: OPEN, UNDER_REVIEW, RESOLVED, FALSE_POSITIVE, CLOSED")
                new_status = input("Enter new status: ").strip().upper()
                if new_status in ("RESOLVED", "FALSE_POSITIVE", "CLOSED"):
                    alert_service.close_alert(alert_id, new_status)
                else:
                    alert_service.update_alert_status(alert_id, new_status)
                print(f"\n{GREEN}Success: Alert {alert_id} updated to {new_status}.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "4":
            try:
                alert_id = int(input("Enter Alert ID: ").strip())
                notes = input("Enter escalation notes: ").strip()
                alert_service.escalate_alert(alert_id, notes)
                print(f"\n{GREEN}Success: Alert {alert_id} escalated successfully.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "5":
            break
        else:
            print(f"{RED}Invalid input. Try again.{RESET}")

def menu_cases():
    from services import CaseService
    from repositories import CaseRepository
    case_service = CaseService()
    case_repo = CaseRepository()
    from tabulate import tabulate
    
    while True:
        print(f"\n{CYAN}=========================================={RESET}")
        print(f"            5. CASES WORKFLOW SUBMENU")
        print(f"{CYAN}=========================================={RESET}")
        print("1. View All Cases")
        print("2. View Case History Timeline")
        print("3. Assign Case to Investigator")
        print("4. Transition Case Status")
        print("5. Add Investigator Note")
        print("6. Add Remark")
        print("7. Resolve Case")
        print("8. Close Case")
        print("9. Back to Main Menu")
        choice = input("Select option (1-9): ").strip()
        
        if choice == "1":
            try:
                cases = case_repo.find_all()
                if not cases:
                    print(f"\n{GREEN}No cases registered in database.{RESET}")
                else:
                    data = [[c.case_id, c.alert_id, c.assigned_to, c.status, c.priority, c.resolution] for c in cases]
                    print("\n" + tabulate(data, headers=["Case ID", "Alert ID", "Assigned", "Status", "Priority", "Resolution"], tablefmt="grid"))
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "2":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                history = case_service.get_case_history(case_id)
                if not history:
                    print(f"\n{GREEN}No history event timeline found for case {case_id}.{RESET}")
                else:
                    print(f"\n{CYAN}Case Timeline Events:{RESET}")
                    for event in history:
                        print(f"  - {event}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "3":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                analyst = input("Enter Analyst/Investigator Name: ").strip()
                case_service.assign_case(case_id, analyst)
                print(f"\n{GREEN}Success: Case {case_id} assigned to '{analyst}'.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "4":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                print("Allowed: OPEN, UNDER_REVIEW, ESCALATED, RESOLVED, CLOSED")
                new_status = input("Enter new status: ").strip().upper()
                case_service.change_status(case_id, new_status)
                print(f"\n{GREEN}Success: Case {case_id} status transitioned to {new_status}.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "5":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                note = input("Enter analyst note: ").strip()
                case_service.add_analyst_note(case_id, note)
                print(f"\n{GREEN}Success: Investigator note added.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "6":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                remark = input("Enter remark: ").strip()
                case_service.add_remark(case_id, remark)
                print(f"\n{GREEN}Success: Case remark recorded successfully.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "7":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                resolution = input("Enter resolution reason details: ").strip()
                case_service.resolve_case(case_id, resolution)
                print(f"\n{GREEN}Success: Case {case_id} resolved.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "8":
            try:
                case_id = int(input("Enter Case ID: ").strip())
                case_service.close_case(case_id)
                print(f"\n{GREEN}Success: Case {case_id} closed successfully.{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "9":
            break
        else:
            print(f"{RED}Invalid input. Try again.{RESET}")

def menu_investigation():
    from services import InvestigationService
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            6. RUN CUSTOMER INVESTIGATION")
    print(f"{CYAN}=========================================={RESET}")
    try:
        customer_id = int(input("Enter Customer ID: ").strip())
    except ValueError:
        print(f"{RED}Error: Customer ID must be an integer.{RESET}")
        return
        
    try:
        service = InvestigationService()
        report = service.investigate_customer(customer_id)
        
        print("\n" + "=" * 60)
        print("               CUSTOMER FRAUD INVESTIGATION REPORT")
        print("=" * 60)
        
        c = report["customer_profile"]
        print(f"Customer Name: {c['first_name']} {c['last_name']} (ID: {c['customer_id']})")
        print(f"Email Address: {c['email']}")
        print(f"Mobile Phone:  {c['phone']}")
        print(f"PAN card No:   {c.get('pan') or 'N/A'}")
        print(f"Bank Account:  {c.get('account_number') or 'N/A'}")
        print(f"Profile State: {c['status']}")
        print("-" * 60)
        
        rp = report["risk_profile"]
        curr_score = rp["current_risk_score"] if rp else 0
        risk_tier = rp["risk_tier"] if rp else "LOW"
        print(f"Risk Score:    {curr_score}/100")
        print(f"Risk Level:    {risk_tier}")
        print(f"Trust Score:   {report['trust_score']}%")
        print(f"Behavior Summary: {report['behaviour_summary']}")
        print(f"Average Amount:   ${report['average_amount']:.2f}")
        print(f"Declined Attempts: {report['fraud_attempts']}")
        print(f"Most Risky City:   {report['most_frequent_city']}")
        print("-" * 60)
        
        print("Associated Devices Used:")
        if report["devices_used"]:
            for d in report["devices_used"]:
                print(f"  - OS: {d.get('operating_system')}, IP: {d.get('ip_address')}, Fingerprint: {d.get('device_fingerprint')[:15]}...")
        else:
            print("  None detected.")
        print("-" * 60)
        
        print("Investigation Log Timeline Events:")
        if report["timeline"]:
            for event in report["timeline"]:
                print(f"  - {event}")
        else:
            print("  No timeline event audits present.")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"{RED}Error compiling investigation: {e}{RESET}")

def menu_analytics():
    from services import AnalyticsService
    from tabulate import tabulate
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            7. SYSTEM ANALYTICS DASHBOARD")
    print(f"{CYAN}=========================================={RESET}")
    
    try:
        service = AnalyticsService()
        analytics = service.get_system_analytics()
        
        print(f"\nFraud Declines Rate:        {analytics['fraud_percentage']}%")
        print(f"Average Transaction Value:  ${analytics['average_transaction_amount']:.2f}")
        print(f"False Positive Alert Ratio: {analytics['false_positive_ratio']}%")
        print(f"Average Case Close Time:    {analytics['case_resolution_time']:.1f} seconds")
        print("-" * 60)
        
        print("\nTop 5 Risky Customers:")
        if analytics["top_risky_customers"]:
            data = [[c["customer_id"], c["customer_name"], c["risk_score"], c["risk_tier"]] for c in analytics["top_risky_customers"]]
            print(tabulate(data, headers=["ID", "Name", "Score", "Tier"], tablefmt="simple"))
        else:
            print("  No risky customers recorded.")
            
        print("\nTop 5 Risky Cities:")
        if analytics["top_risky_cities"]:
            data = [[c["city"], c["total_count"], c["fraud_count"]] for c in analytics["top_risky_cities"]]
            print(tabulate(data, headers=["City", "Total Trx", "Fraud Count"], tablefmt="simple"))
        else:
            print("  No city coordinates data.")
            
        print("\nTop Risky Merchant Categories:")
        if analytics["top_risky_merchant_categories"]:
            data = [[m["merchant_category"], m["fraud_count"], f"{m['average_score']:.1f}", m["risk_level"]] for m in analytics["top_risky_merchant_categories"]]
            print(tabulate(data, headers=["Category", "Fraud count", "Avg Score", "Risk Level"], tablefmt="simple"))
        else:
            print("  No category metadata analytics.")
            
        print("\nMost Triggered Fraud rules:")
        if analytics["most_triggered_rules"]:
            data = [[r["rule_name"], r["trigger_count"]] for r in analytics["most_triggered_rules"]]
            print(tabulate(data, headers=["Rule Name", "Triggers"], tablefmt="simple"))
        else:
            print("  No rules logs triggered.")
            
    except Exception as e:
        print(f"{RED}Error compiling dashboard: {e}{RESET}")

def menu_reports():
    from reports import ReportGenerator
    generator = ReportGenerator()
    from tabulate import tabulate
    
    while True:
        print(f"\n{CYAN}=========================================={RESET}")
        print(f"            8. REPORTS & CSV EXPORTS")
        print(f"{CYAN}=========================================={RESET}")
        print("1. Generate Daily Operations Report")
        print("2. Generate Weekly Operations Report")
        print("3. Generate Monthly Operations Report")
        print("4. Generate High Risk Customers Report")
        print("5. Generate Fraud Summary Report")
        print("6. Generate Case Statistics Report")
        print("7. Generate Alert Statistics Report")
        print("8. Export System Log Data to CSV")
        print("9. Back to Main Menu")
        choice = input("Select option (1-9): ").strip()
        
        if choice in ("1", "2", "3"):
            try:
                if choice == "1":
                    stats = generator.generate_daily_report()
                    title = "DAILY OPERATIONS SUMMARY"
                elif choice == "2":
                    stats = generator.generate_weekly_report()
                    title = "WEEKLY OPERATIONS SUMMARY"
                else:
                    stats = generator.generate_monthly_report()
                    title = "MONTHLY OPERATIONS SUMMARY"
                    
                print(f"\n==========================================")
                print(f"       {title}")
                print(f"==========================================")
                print(f"Window Duration:             {stats['window_days']} Days")
                print(f"Total Transactions Processed: {stats['total_transactions']}")
                print(f"Fraud Transaction Declined:  {stats['fraud_count']}")
                print(f"Fraud Declines Percentage:   {stats['fraud_rate_percentage']}%")
                print(f"Total Transactions Volume:   ${stats['total_transaction_amount']:.2f}")
                print(f"Average Transaction value:   ${stats['average_transaction_amount']:.2f}")
                print(f"Alerts Triggered:            {stats['alerts_generated']}")
                print(f"==========================================\n")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "4":
            try:
                report = generator.generate_high_risk_customer_report()
                if not report:
                    print(f"\n{GREEN}No high risk customers found.{RESET}")
                else:
                    data = [[c['customer_id'], c['customer_name'], c['email'], c['risk_score'], c['risk_tier']] for c in report]
                    print("\n" + tabulate(data, headers=["ID", "Name", "Email", "Risk Score", "Tier"], tablefmt="grid"))
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "5":
            try:
                stats = generator.generate_fraud_summary_report()
                print("\n==========================================")
                print("          FRAUD SUMMARY REPORT")
                print("==========================================")
                print(f"Total Fraud Declines count:    {stats['total_fraud_transactions']}")
                print(f"Total Fraud Declines Volume:   ${stats['total_fraud_amount']:.2f}")
                print("-" * 42)
                print("Top Risky Categories:")
                for r in stats['top_merchant_categories']:
                    print(f"  MCC Category: {r['merchant_category']} (Declines: {r['fraud_count']})")
                print("-" * 42)
                print("Top Risky Cities:")
                for r in stats['top_risky_cities']:
                    print(f"  City Name: {r['city']} (Declines: {r['fraud_count']})")
                print("==========================================\n")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "6":
            try:
                stats = generator.generate_case_statistics_report()
                print("\n==========================================")
                print("          CASE STATISTICS REPORT")
                print("==========================================")
                print(f"Total Cases Triggered:        {stats['total_cases']}")
                print(f"Average Case Resolution Time: {stats['average_resolution_time_seconds']:.1f} seconds")
                print("-" * 42)
                print("Status Distribution:")
                for k, v in stats['status_distribution'].items():
                    print(f"  - {k}: {v}")
                print("-" * 42)
                print("Priority Distribution:")
                for k, v in stats['priority_distribution'].items():
                    print(f"  - {k}: {v}")
                print("==========================================\n")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "7":
            try:
                stats = generator.generate_alert_statistics_report()
                print("\n==========================================")
                print("          ALERT STATISTICS REPORT")
                print("==========================================")
                print(f"Total Alerts Triggered:       {stats['total_alerts']}")
                print(f"Average Risk Score:           {stats['average_risk_score']:.1f}/100")
                print("-" * 42)
                print("Status Distribution:")
                for k, v in stats['status_distribution'].items():
                    print(f"  - {k}: {v}")
                print("-" * 42)
                print("Severity Distribution:")
                for k, v in stats['severity_distribution'].items():
                    print(f"  - {k}: {v}")
                print("==========================================\n")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "8":
            try:
                print("Available: TRANSACTIONS, ALERTS, CASES")
                entity = input("Enter category to export: ").strip().upper()
                csv_data = generator.generate_csv_export(entity)
                print(f"\n{GREEN}CSV Export for {entity}:{RESET}\n")
                print(csv_data)
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        elif choice == "9":
            break
        else:
            print(f"{RED}Invalid input. Try again.{RESET}")

def menu_simulator():
    from simulator import FraudSimulator
    print(f"\n{CYAN}=========================================={RESET}")
    print(f"            9. RUN TELEMETRY SIMULATOR")
    print(f"{CYAN}=========================================={RESET}")
    try:
        num_customers = int(input("Enter synthetic customers to generate (default: 50): ").strip() or "50")
        num_transactions = int(input("Enter transaction streaming limit (default: 200): ").strip() or "200")
        fraud_ratio = float(input("Enter target fraud ratio (0.0 to 1.0, default: 0.15): ").strip() or "0.15")
    except ValueError:
        print(f"{RED}Error: Invalid numeric input parameters.{RESET}")
        return
        
    print(f"\nInitializing synthetic simulator runtime context...")
    try:
        simulator = FraudSimulator()
        simulator.run_simulation(
            num_customers=num_customers,
            num_transactions=num_transactions,
            fraud_ratio=fraud_ratio
        )
        print(f"\n{GREEN}Success: Telemetry simulation run completed successfully.{RESET}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

def cli_menu():
    """
    Main interactive presentation shell.
    """
    while True:
        print(f"\n{CYAN}========================================================================{RESET}")
        print(f"                 FINGUARD FRAUD INVESTIGATION TERMINAL")
        print(f"{CYAN}========================================================================{RESET}")
        print("1  Add Customer")
        print("2  Create Transaction")
        print("3  Run Fraud Detection")
        print("4  Alerts")
        print("5  Cases")
        print("6  Investigation")
        print("7  Analytics")
        print("8  Reports")
        print("9  Simulator")
        print("10 Exit")
        print(f"{CYAN}------------------------------------------------------------------------{RESET}")
        choice = input("Enter option index (1-10): ").strip()
        
        if choice == "1":
            menu_add_customer()
        elif choice == "2":
            menu_create_transaction()
        elif choice == choice == "3":
            menu_run_fraud_detection()
        elif choice == "4":
            menu_alerts()
        elif choice == "5":
            menu_cases()
        elif choice == "6":
            menu_investigation()
        elif choice == "7":
            menu_analytics()
        elif choice == "8":
            menu_reports()
        elif choice == "9":
            menu_simulator()
        elif choice == "10":
            print(f"\n{GREEN}Exiting FinGuard Management Terminal. Goodbye!{RESET}\n")
            break
        else:
            print(f"\n{RED}Error: Choice '{choice}' is not recognized. Please pick a number between 1 and 10.{RESET}")

# =========================================================================
# MAIN VALIDATION AND LAUNCHER ENTRY
# =========================================================================

def main() -> None:
    """
    System entry point for platform verification and CLI presentation.
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
            
    # 4. Print validation status report
    try:
        import colorama
        from tabulate import tabulate
        colorama.init(autoreset=True)
        
        c_green = colorama.Fore.GREEN + colorama.Style.BRIGHT
        c_red = colorama.Fore.RED + colorama.Style.BRIGHT
        c_reset = colorama.Style.RESET_ALL
        
        print(f"\n{CYAN}========================================================================")
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
        print("\n")
        
    except ImportError:
        # Fallback to plain print statements
        print("\n========================================================================")
        print("       FinGuard - Intelligent Financial Fraud & Risk Monitoring")
        print("                      Startup Verification Checks")
        print("========================================================================\n")
        print(f"Python Version Compatibility: {py_msg} -> {'PASS' if py_ok else 'FAIL'}")
        print(f"Enterprise Custom Exceptions: {exceptions_msg} -> {'PASS' if exceptions_ok else 'FAIL'}")
        print(f"Configuration Variables Setup: {config_msg} -> {'PASS' if config_ok else 'FAIL'}")
        print(f"MySQL Connection (use_pure=True): {db_msg} -> {'PASS' if db_ok else 'FAIL'}")
        print("\n")

    system_ready = py_ok and exceptions_ok and libs_ok and config_ok and db_ok
    
    if "--cli" in sys.argv:
        if system_ready:
            print(f"{GREEN}SUCCESS: All verification checks passed. Starting management terminal...{RESET}\n")
            logging.info("Verification checks completed. Starting CLI terminal...")
            try:
                cli_menu()
            except KeyboardInterrupt:
                print(f"\n\n{GREEN}Terminal execution interrupted. Goodbye!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}ERROR: Environment validation failed. Review the logs/error.log file.{RESET}\n")
            if libs_ok:
                logging.critical("Validation failed. One or more components are not ready.")
            sys.exit(1)
    else:
        # Launch GUI by default
        if system_ready:
            print(f"{GREEN}SUCCESS: All verification checks passed. Launching FinGuard GUI...{RESET}\n")
            logging.info("Verification checks completed. Starting GUI...")
            try:
                from ui.main_window import MainWindow, SplashScreen
                app = MainWindow()
                splash = SplashScreen(app)
                app.mainloop()
            except Exception as e:
                print(f"{RED}ERROR: Failed to launch GUI: {e}{RESET}\n")
                logging.critical(f"Failed to launch GUI: {e}", exc_info=True)
                sys.exit(1)
        else:
            print(f"{RED}ERROR: Environment validation failed. Review the logs/error.log file.{RESET}\n")
            if libs_ok:
                logging.critical("Validation failed. One or more components are not ready.")
            sys.exit(1)

if __name__ == "__main__":
    main()

