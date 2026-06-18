import os
import sys
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
from simulator import FraudSimulator


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_fraud_simulation(db: DatabaseConnection):
    print("Testing: Fraud Simulation orchestration flow...")
    
    simulator = FraudSimulator()
    
    # Run a quick, scaled-down simulation for automated testing
    summary = simulator.run_simulation(
        num_customers=50, 
        num_transactions=200, 
        fraud_ratio=0.15
    )
    
    # Assertions on metrics summary
    assert summary["customers_generated"] == 50
    assert summary["transactions_simulated"] >= 200
    assert summary["transactions_approved"] > 0
    assert summary["audit_logs_recorded"] > 0
    assert summary["rule_executions_logged"] > 0
    
    print("  [PASS] Simulation summary metrics validated.")

    # 1. Verify custom data distributions (multiple devices and cities)
    cities_row = db.fetch_all("SELECT DISTINCT location_latitude, location_longitude FROM transactions WHERE location_latitude IS NOT NULL")
    assert len(cities_row) > 1
    print(f"  [PASS] City coordinate mappings verified (Count: {len(cities_row)}).")

    device_row = db.fetch_all("SELECT DISTINCT device_id FROM transactions WHERE device_id IS NOT NULL")
    assert len(device_row) > 1
    print(f"  [PASS] Device fingerprint mappings verified (Count: {len(device_row)}).")

    # 2. Verify alert and case triggers
    alerts_cnt = db.fetch_one("SELECT COUNT(*) as c FROM alerts")["c"]
    cases_cnt = db.fetch_one("SELECT COUNT(*) as c FROM cases")["c"]
    assert alerts_cnt > 0
    assert cases_cnt > 0
    print(f"  [PASS] Security alert triggers verified. Alerts: {alerts_cnt}, Cases: {cases_cnt}")

    # 3. Verify rule execution histories mapping
    rule_logs = db.fetch_all("SELECT DISTINCT rule_name FROM rule_execution_logs WHERE triggered = TRUE")
    triggered_rules = [r["rule_name"] for r in rule_logs]
    print(f"  Triggered Fraud Rules in DB: {triggered_rules}")
    assert len(triggered_rules) > 0
    print("  [PASS] Rule executions logs mapping verified.")

    # 4. Verify audit trail logs mapping
    audit_cnt = db.fetch_one("SELECT COUNT(*) as c FROM audit_logs")["c"]
    assert audit_cnt > 0
    print(f"  [PASS] Audit logs trail mapped successfully (Count: {audit_cnt}).")


def main():
    print("==================================================")
    print("      FinGuard Module 19 Verification Suite")
    print("==================================================\n")
    
    reinit_db()
    db = DatabaseConnection()
    
    test_fraud_simulation(db)
    
    print("\n==================================================")
    print("      All Module 19 Verification Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
