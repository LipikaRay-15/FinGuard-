import os
import sys
import glob
import json
import subprocess
from datetime import datetime

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
settings.setup_logging()

# Setup stdout for Unicode support
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import DatabaseConnection
from services import (
    CustomerService,
    AlertService,
    CaseService,
    InvestigationService,
    TransactionService,
    AuditLogService
)
from engines import RuleEngine
from reports import ReportGenerator
from scheduler import Scheduler


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_audit_logging(db: DatabaseConnection):
    print("Testing: Python Audit Logging triggers...")
    
    cust_service = CustomerService()
    rule_engine = RuleEngine()
    tx_service = TransactionService()
    case_service = CaseService()
    alert_service = AlertService()
    inv_service = InvestigationService()
    audit_service = AuditLogService()
    
    # 1. Customer Creation Audit
    cust = cust_service.create_customer(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1555010077",
        status="ACTIVE",
        pan="ABCDE1234F",
        account_number="9876543210",
        pincode="751024"
    )
    assert cust.customer_id is not None
    
    # Verify CREATE_CUSTOMER audit log
    logs = audit_service.get_audit_logs({"user_action": "CREATE_CUSTOMER", "record_id": cust.customer_id})
    assert len(logs) == 1
    assert logs[0].affected_table == "customers"
    assert logs[0].new_values["email"] == "jane.doe@example.com"
    print("  [PASS] CREATE_CUSTOMER audit logging verified.")

    # 2. Customer Update Audit
    cust_service.update_customer(
        customer_id=cust.customer_id,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="+1555010077",
        status="ACTIVE",
        pan="ABCDE1234F",
        account_number="9876543210",
        pincode="751024"
    )
    
    # Verify UPDATE_CUSTOMER audit log
    logs = audit_service.get_audit_logs({"user_action": "UPDATE_CUSTOMER", "record_id": cust.customer_id})
    assert len(logs) == 1
    assert logs[0].old_values["last_name"] == "Doe"
    assert logs[0].new_values["last_name"] == "Smith"
    print("  [PASS] UPDATE_CUSTOMER audit logging verified.")

    # 3. Customer Deletion Audit
    cust_service.delete_customer(cust.customer_id)
    logs = audit_service.get_audit_logs({"user_action": "DELETE_CUSTOMER", "record_id": cust.customer_id})
    assert len(logs) == 1
    assert logs[0].old_values["email"] == "jane.smith@example.com"
    assert logs[0].new_values is None
    print("  [PASS] DELETE_CUSTOMER audit logging verified.")

    # 4. Rule Enable/Disable Audit
    # Rule 1 is seeded 'High Transaction Amount'
    rule_engine.disable_rule(rule_id=1)
    logs = audit_service.get_audit_logs({"user_action": "DISABLE_RULE", "record_id": 1})
    assert len(logs) == 1
    assert logs[0].new_values["enabled"] is False
    
    rule_engine.enable_rule(rule_id=1)
    logs = audit_service.get_audit_logs({"user_action": "ENABLE_RULE", "record_id": 1})
    assert len(logs) == 1
    assert logs[0].new_values["enabled"] is True
    print("  [PASS] Rule Enable/Disable audit logging verified.")

    # 5. Transaction Creation Audit
    # Use customer 1 (seeded Alice)
    tx = tx_service.create_transaction(
        customer_id=1,
        amount="250.00",
        city="LONDON",
        merchant_category="SUPERMARKET",
        transaction_type="PURCHASE"
    )
    saved_tx = tx_service.save_transaction(tx)
    assert saved_tx.transaction_id is not None
    
    # Verify CREATE_TRANSACTION audit log
    logs = audit_service.get_audit_logs({"user_action": "CREATE_TRANSACTION", "record_id": saved_tx.transaction_id})
    assert len(logs) == 1
    assert float(logs[0].new_values["amount"]) == 250.00
    print("  [PASS] CREATE_TRANSACTION audit logging verified.")

    # 6. Alert & Case updates Audit
    # Find generated alert for this transaction
    alert_row = db.fetch_one("SELECT alert_id FROM alerts WHERE transaction_id = %s", (saved_tx.transaction_id,))
    if alert_row:
        alert_id = alert_row["alert_id"]
        # Update alert
        alert_service.update_alert_status(alert_id, "UNDER_REVIEW")
        logs = audit_service.get_audit_logs({"user_action": "UPDATE_ALERT_STATUS", "record_id": alert_id})
        assert len(logs) == 1
        assert logs[0].new_values["status"] == "UNDER_REVIEW"

        # Escalate alert
        alert_service.escalate_alert(alert_id, "Escalating test case")
        logs = audit_service.get_audit_logs({"user_action": "ESCALATE_ALERT", "record_id": alert_id})
        assert len(logs) == 1
        assert logs[0].new_values["status"] == "UNDER_REVIEW"

        # Close alert
        alert_service.close_alert(alert_id, "RESOLVED - legitimate test transaction")
        logs = audit_service.get_audit_logs({"user_action": "CLOSE_ALERT", "record_id": alert_id})
        assert len(logs) == 1
        assert logs[0].new_values["status"] == "RESOLVED"
        
        # Verify Case modifications log
        case_row = db.fetch_one("SELECT case_id FROM cases WHERE alert_id = %s", (alert_id,))
        if case_row:
            case_id = case_row["case_id"]
            case_service.assign_case(case_id, "Analyst Bob")
            logs = audit_service.get_audit_logs({"user_action": "ASSIGN_CASE", "record_id": case_id})
            assert len(logs) == 1
            assert logs[0].new_values["assigned_to"] == "Analyst Bob"

            case_service.change_status(case_id, "UNDER_REVIEW")
            logs = audit_service.get_audit_logs({"user_action": "CHANGE_CASE_STATUS", "record_id": case_id})
            assert len(logs) == 1
            assert logs[0].new_values["status"] == "UNDER_REVIEW"

            case_service.add_remark(case_id, "Verified with system admin")
            logs = audit_service.get_audit_logs({"user_action": "ADD_CASE_REMARK", "record_id": case_id})
            assert len(logs) == 1
            assert "Verified with system admin" in logs[0].new_values["remarks"]

            case_service.resolve_case(case_id, "Test transaction approved")
            logs = audit_service.get_audit_logs({"user_action": "RESOLVE_CASE", "record_id": case_id})
            assert len(logs) == 1
            assert logs[0].new_values["status"] == "RESOLVED"

            case_service.close_case(case_id)
            logs = audit_service.get_audit_logs({"user_action": "CLOSE_CASE", "record_id": case_id})
            assert len(logs) == 1
            assert logs[0].new_values["status"] == "CLOSED"
            print("  [PASS] Alert and Case update audit logging verified.")

    # 7. Customer Investigation Audit
    inv_service.investigate_customer(1)
    logs = audit_service.get_audit_logs({"user_action": "INVESTIGATE_CUSTOMER", "record_id": 1})
    assert len(logs) == 1
    assert "trust_score" in logs[0].new_values
    print("  [PASS] INVESTIGATE_CUSTOMER audit logging verified.")


def test_report_generation():
    print("\nTesting: ReportGenerator formatting and outputs...")
    rep_gen = ReportGenerator()
    
    # 1. Periodical aggregates
    daily = rep_gen.generate_daily_report()
    assert "total_transactions" in daily
    assert "total_transaction_amount" in daily
    
    weekly = rep_gen.generate_weekly_report()
    assert "window_days" in weekly
    assert weekly["window_days"] == 7
    
    monthly = rep_gen.generate_monthly_report()
    assert "window_days" in monthly
    assert monthly["window_days"] == 30
    print("  [PASS] Daily, Weekly, and Monthly Operations reports compile correctly.")

    # 2. High Risk customer lists
    hr_cust = rep_gen.generate_high_risk_customer_report()
    assert isinstance(hr_cust, list)
    print("  [PASS] High Risk Customers list generated successfully.")

    # 3. Fraud Summary
    fraud_summary = rep_gen.generate_fraud_summary_report()
    assert "total_fraud_transactions" in fraud_summary
    assert "total_fraud_amount" in fraud_summary
    print("  [PASS] Fraud Summary report compiles successfully.")

    # 4. Diagnostics: Case and Alert stats
    case_stats = rep_gen.generate_case_statistics_report()
    assert "total_cases" in case_stats
    assert "status_distribution" in case_stats
    
    alert_stats = rep_gen.generate_alert_statistics_report()
    assert "total_alerts" in alert_stats
    assert "severity_distribution" in alert_stats
    print("  [PASS] Diagnostics reports (Case and Alert stats) verify successfully.")

    # 5. CSV Data Exports
    csv_tx = rep_gen.generate_csv_export("TRANSACTIONS")
    assert "transaction_id,customer_id" in csv_tx
    
    csv_alerts = rep_gen.generate_csv_export("ALERTS")
    assert "alert_id,transaction_id" in csv_alerts

    csv_cases = rep_gen.generate_csv_export("CASES")
    assert "case_id,alert_id" in csv_cases
    print("  [PASS] CSV exports for Transactions, Alerts, and Cases validated.")


def test_scheduler_activities(db: DatabaseConnection):
    print("\nTesting: Scheduler background logic and Retention / Archiving policies...")
    scheduler = Scheduler()

    # Create dummy logs to verify logs cleanup (older than 90 days)
    db.execute(
        "INSERT INTO audit_logs (audit_id, user_action, affected_table, record_id, performed_by, performed_at) "
        "VALUES (9999, 'CLEANUP_TEST', 'test_table', 1, 'TESTER', NOW() - INTERVAL 100 DAY)"
    )
    db.execute(
        "INSERT INTO rule_execution_logs (execution_id, transaction_id, rule_id, rule_name, triggered, risk_score_awarded, severity, execution_time) "
        "VALUES (9999, 1, 1, 'Velocity Check', TRUE, 80, 'HIGH', NOW() - INTERVAL 100 DAY)"
    )
    db.execute(
        "INSERT INTO events (event_id, event_type, entity_type, entity_id, created_at) "
        "VALUES (9999, 'TEST_EVENT', 'CUSTOMER', '1', NOW() - INTERVAL 100 DAY)"
    )
    db.commit()

    # Verify log items inserted
    assert db.fetch_one("SELECT COUNT(*) as c FROM audit_logs WHERE audit_id = 9999")["c"] == 1
    
    # Run logs cleanup task
    scheduler.run_cleanup_logs()
    
    # Verify they were deleted (older than 90 days)
    assert db.fetch_one("SELECT COUNT(*) as c FROM audit_logs WHERE audit_id = 9999")["c"] == 0
    assert db.fetch_one("SELECT COUNT(*) as c FROM rule_execution_logs WHERE execution_id = 9999")["c"] == 0
    assert db.fetch_one("SELECT COUNT(*) as c FROM events WHERE event_id = 9999")["c"] == 0
    print("  [PASS] 90 Days logs retention policy cleanup verified successfully.")

    # Create dummy records to verify archiving policy (older than 180 days)
    # Use clean file path globbing under reports/archive
    archive_pattern = os.path.join(PROJECT_ROOT, "reports", "archive", "*_archive_*.json")
    for f in glob.glob(archive_pattern):
        try:
            os.remove(f)
        except OSError:
            pass

    db.execute(
        "INSERT INTO transactions (transaction_id, customer_id, amount, transaction_type, status, transaction_time) "
        "VALUES (9999, 1, 500.00, 'PURCHASE', 'FLAGGED', NOW() - INTERVAL 200 DAY)"
    )
    db.execute(
        "INSERT INTO alerts (alert_id, transaction_id, customer_id, risk_score, severity, status, created_at) "
        "VALUES (9999, 9999, 1, 80, 'HIGH', 'OPEN', NOW() - INTERVAL 200 DAY)"
    )
    db.execute(
        "INSERT INTO cases (case_id, alert_id, status, priority, created_at) "
        "VALUES (9999, 9999, 'OPEN', 'HIGH', NOW() - INTERVAL 200 DAY)"
    )
    db.commit()

    # Run archiving task
    scheduler.run_archive_old_records()

    # Verify they were deleted from DB
    assert db.fetch_one("SELECT COUNT(*) as c FROM cases WHERE case_id = 9999")["c"] == 0
    assert db.fetch_one("SELECT COUNT(*) as c FROM alerts WHERE alert_id = 9999")["c"] == 0
    assert db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE transaction_id = 9999")["c"] == 0

    # Verify files were generated in reports/archive
    archive_files = glob.glob(archive_pattern)
    assert len(archive_files) > 0
    print(f"  [PASS] 180 Days archiving policy verified. Generated archive files: {[os.path.basename(f) for f in archive_files]}")

    # Run daily report write to check file write
    daily_pattern = os.path.join(PROJECT_ROOT, "reports", "daily_report_*.json")
    for f in glob.glob(daily_pattern):
        try:
            os.remove(f)
        except OSError:
            pass
            
    scheduler.run_daily_reports()
    daily_files = glob.glob(daily_pattern)
    assert len(daily_files) == 1
    print(f"  [PASS] Scheduler file output daily_report successfully verified.")


def main():
    print("==================================================")
    print("      FinGuard Module 18 Verification Suite")
    print("==================================================\n")
    
    reinit_db()
    db = DatabaseConnection()
    
    test_audit_logging(db)
    test_report_generation()
    test_scheduler_activities(db)
    
    print("\n==================================================")
    print("      All Module 18 Verification Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
