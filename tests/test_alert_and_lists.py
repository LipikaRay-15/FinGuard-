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
from models import Transaction
from services import AlertService, BlacklistService, WhitelistService
from engines import AlertManager
from services.transaction_service import TransactionService


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_blacklist_operations(service: BlacklistService, db: DatabaseConnection):
    print("Testing: Blacklist operations...")
    
    # 1. Blacklist Customer
    service.blacklist_customer(customer_id=1, reason="Fraudulent activity baseline")
    is_bl, reason = service.check_blacklist(customer_id=1)
    assert is_bl is True
    assert "Fraudulent activity baseline" in reason

    # Check status updated to BLOCKED in customers table
    cust_row = db.fetch_one("SELECT status FROM customers WHERE customer_id = 1")
    assert cust_row["status"] == "BLOCKED"

    # 2. Blacklist Device
    service.blacklist_device(device_id=2, reason="Stolen fingerprint device signature")
    is_bl, reason = service.check_blacklist(device_id=2)
    assert is_bl is True
    assert "Stolen fingerprint" in reason

    # 3. Block PAN
    service.block_pan(pan="4111222233", reason="Linked to carding scheme")
    is_bl, reason = service.check_blacklist(pan="4111222233")
    assert is_bl is True
    assert "carding scheme" in reason

    # 4. Block Account
    service.block_account(account_number="1234567890", reason="Receiver bank account mule")
    is_bl, reason = service.check_blacklist(account_number="1234567890")
    assert is_bl is True
    assert "mule" in reason

    # 5. Check audit events in event store
    ev1 = db.fetch_all("SELECT * FROM events WHERE event_type = 'CUSTOMER_BLACKLISTED'")
    assert len(ev1) == 1
    ev2 = db.fetch_all("SELECT * FROM events WHERE event_type = 'PAN_BLOCKED'")
    assert len(ev2) == 1

    print("  [PASS] Blacklist customer, device, PAN, and account checks passed.")


def test_whitelist_operations(service: WhitelistService, db: DatabaseConnection):
    print("\nTesting: Whitelist operations...")
    
    # 1. Whitelist Customer
    service.whitelist_customer(customer_id=2, reason="Known VIP trader account override")
    is_wl, reason = service.check_whitelist(customer_id=2)
    assert is_wl is True
    assert "VIP trader" in reason

    # 2. Whitelist Device
    service.whitelist_device(device_id=1, reason="Corporate verified laptop terminal")
    is_wl, reason = service.check_whitelist(device_id=1)
    assert is_wl is True
    assert "verified laptop" in reason

    # 3. Check audit events
    ev = db.fetch_all("SELECT * FROM events WHERE event_type = 'CUSTOMER_WHITELISTED'")
    assert len(ev) == 1

    print("  [PASS] Whitelist customer and device checks passed.")


def test_alert_lifecycle(service: AlertService, db: DatabaseConnection):
    print("\nTesting: Alert service lifecycle operations...")
    
    # 1. Generate alert
    alert = service.generate_alert(
        transaction_id=1, # seeded TX
        customer_id=1,
        risk_score=75,
        severity="HIGH",
        status="OPEN"
    )
    assert alert.alert_id is not None
    assert alert.severity == "HIGH"
    assert alert.status == "OPEN"

    # 2. Update alert status
    service.update_alert_status(alert.alert_id, "UNDER_REVIEW")
    loaded = service.alert_repo.find_by_id(alert.alert_id)
    assert loaded.status == "UNDER_REVIEW"

    # 3. Escalate alert (bump severity: HIGH -> CRITICAL, status becomes UNDER_REVIEW)
    service.escalate_alert(alert.alert_id, notes="Manual escalation by investigator")
    loaded = service.alert_repo.find_by_id(alert.alert_id)
    assert loaded.severity == "CRITICAL"
    assert loaded.status == "UNDER_REVIEW"

    # 4. Close alert (resolution FALSE_POSITIVE)
    service.close_alert(alert.alert_id, resolution="Legitimate holiday travel transaction - false positive")
    loaded = service.alert_repo.find_by_id(alert.alert_id)
    assert loaded.status == "FALSE_POSITIVE"

    # 5. Listings and History
    open_alerts = service.get_open_alerts()
    # Should not contain the closed one
    assert not any(a.alert_id == alert.alert_id for a in open_alerts)

    # Re-open a new alert to test open list
    alert2 = service.generate_alert(transaction_id=2, customer_id=1, risk_score=85, severity="HIGH")
    open_alerts = service.get_open_alerts()
    assert any(a.alert_id == alert2.alert_id for a in open_alerts)

    history = service.get_alert_history(customer_id=1)
    assert len(history) >= 2

    # 6. Event Store auditing check
    ev_gen = db.fetch_all("SELECT * FROM events WHERE event_type = 'ALERT_GENERATED'")
    assert len(ev_gen) >= 2
    ev_closed = db.fetch_all("SELECT * FROM events WHERE event_type = 'ALERT_CLOSED'")
    assert len(ev_closed) == 1

    print("  [PASS] Alert generation, update, escalation, close, and retrieval history passed.")


def test_alert_manager_coordination(manager: AlertManager, tx_service: TransactionService, db: DatabaseConnection):
    print("\nTesting: AlertManager routing logic with lists check...")

    # Scenario A: Whitelisted Customer Bob (Customer 2 is whitelisted in previous step)
    # Risk score 80 normally triggers alert, but Bob is whitelisted -> Should return None (bypass)
    tx_wl = tx_service.create_transaction(customer_id=2, amount="500.00", status="PENDING")
    db_tx_wl = tx_service.tx_repo.create(tx_wl)
    db.commit()

    alert_wl = manager.process_transaction_risk(db_tx_wl.transaction_id, risk_score=80, risk_level="HIGH")
    assert alert_wl is None
    print("  [PASS] Whitelist bypass check: whitelisted customer risk generated 0 alerts (bypassed).")

    # Scenario B: Blacklisted Customer Alice (Customer 1 is blacklisted in previous step)
    # Risk score 30 (usually LOW, no alert) -> but Alice is blacklisted -> Should generate a CRITICAL alert
    tx_bl = tx_service.create_transaction(customer_id=1, amount="50.00", status="PENDING")
    db_tx_bl = tx_service.tx_repo.create(tx_bl)
    db.commit()

    alert_bl = manager.process_transaction_risk(db_tx_bl.transaction_id, risk_score=30, risk_level="LOW")
    assert alert_bl is not None
    assert alert_bl.severity == "CRITICAL"
    print("  [PASS] Blacklist priority check: blacklisted customer generated a CRITICAL alert successfully.")

    # Scenario C: Normal transaction (Customer 5 - no list matches)
    # Insert Customer 5 first
    db.execute(
        "INSERT INTO customers (customer_id, first_name, last_name, email, phone, status) "
        "VALUES (5, 'Eva', 'Green', 'eva@example.com', '+1555010099', 'ACTIVE')"
    )
    db.commit()
    
    # Risk score 60 -> Should generate alert with HIGH/MEDIUM severity
    tx_normal = tx_service.create_transaction(customer_id=5, amount="1500.00", status="PENDING")
    db_tx_normal = tx_service.tx_repo.create(tx_normal)
    db.commit()

    alert_normal = manager.process_transaction_risk(db_tx_normal.transaction_id, risk_score=60, risk_level="HIGH")
    assert alert_normal is not None
    assert alert_normal.severity == "HIGH"
    print("  [PASS] Normal coordination check: non-listed customer generated alert correctly.")


def main():
    print("==================================================")
    print("      Alert & List Management Verification")
    print("==================================================\n")
    
    reinit_db()
    db = DatabaseConnection()
    
    blacklist_serv = BlacklistService()
    whitelist_serv = WhitelistService()
    alert_serv = AlertService()
    alert_mgr = AlertManager()
    tx_serv = TransactionService()

    test_blacklist_operations(blacklist_serv, db)
    test_whitelist_operations(whitelist_serv, db)
    test_alert_lifecycle(alert_serv, db)
    test_alert_manager_coordination(alert_mgr, tx_serv, db)
    
    print("\n==================================================")
    print("       All Alert & List Management Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
