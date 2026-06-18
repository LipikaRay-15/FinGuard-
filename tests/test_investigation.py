import os
import sys
import subprocess
from datetime import datetime
from decimal import Decimal

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
from models import RiskHistory, RiskProfile, Alert, Case, Event
from repositories import RiskHistoryRepository, RiskProfileRepository, AlertRepository, CaseRepository, EventRepository
from services import InvestigationService, DeviceService, TransactionService, AlertService, CaseService
from engines import InvestigationEngine, EventManager


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_investigation_calculations():
    print("Testing: Pure logic engine calculations...")
    engine = InvestigationEngine()

    # 1. Trust Score
    assert engine.calculate_trust_score(0) == 100
    assert engine.calculate_trust_score(45) == 55
    assert engine.calculate_trust_score(100) == 0
    assert engine.calculate_trust_score(120) == 0
    print("  [PASS] Trust score calculations verified.")

    # 2. Average Amount
    txs = [
        {"amount": 50.00},
        {"amount": 100.50},
        {"amount": 149.50}
    ]
    assert engine.calculate_average_amount(txs) == 100.00
    assert engine.calculate_average_amount([]) == 0.00
    print("  [PASS] Average amount calculations verified.")

    # 3. Fraud Attempts (declines)
    txs_attempts = [
        {"status": "approved"},
        {"status": "DECLINED"},
        {"status": "declined"},
        {"status": "reversed"}
    ]
    assert engine.count_fraud_attempts(txs_attempts) == 2
    print("  [PASS] Fraud attempts count verified.")

    # 4. Most Frequent City (coordinates mapping)
    # LAS VEGAS coordinates (36.1716, -115.1398)
    # LONDON coordinates (51.5074, -0.1278)
    # NEW YORK coordinates (40.7128, -74.0060)
    tx_locations = [
        {"location_latitude": 36.1716, "location_longitude": -115.1398}, # LAS VEGAS
        {"location_latitude": 51.5074, "location_longitude": -0.1278},   # LONDON
        {"location_latitude": 51.5075, "location_longitude": -0.1277},   # LONDON (close match)
        {"location_latitude": 40.7128, "location_longitude": -74.0060}    # NEW YORK
    ]
    assert engine.find_most_frequent_city(tx_locations) == "LONDON"
    print("  [PASS] Most frequent city coordinates mapping verified.")

    # 5. Behaviour Summary
    summ1 = engine.generate_behaviour_summary("CRITICAL", 150.00, "LONDON", 2)
    assert "2 declined" in summ1
    assert "CRITICAL" in summ1

    summ2 = engine.generate_behaviour_summary("HIGH", 2500.00, "NEW YORK", 0)
    assert "HIGH" in summ2
    assert "NEW YORK" in summ2

    summ3 = engine.generate_behaviour_summary("LOW", 50.00, "PARIS", 0)
    assert "LOW" in summ3
    assert "PARIS" in summ3
    print("  [PASS] Behaviour summary generation verified.")


def test_investigation_service_flow():
    print("\nTesting: InvestigationService database aggregation and timeline workflow...")
    
    db = DatabaseConnection()
    # Clean up seeded transactions/alerts/cases for customer 1
    db.execute("DELETE FROM transactions WHERE customer_id = 1")
    db.commit()

    device_service = DeviceService()
    tx_service = TransactionService()
    alert_service = AlertService()
    case_service = CaseService()
    investigation_service = InvestigationService()
    
    # 1. Register test device
    device = device_service.register_device(
        device_fingerprint="d" * 64,
        ip_address="192.168.1.50",
        operating_system="macOS",
        user_agent="Mozilla/5.0..."
    )
    assert device.device_id is not None

    # 2. Insert transactions to trigger metrics
    # Customer 1 (Alice) is seeded in schema.sql
    # Let's process three transactions
    # 11:00 PM - Approved LAS VEGAS transaction
    tx1 = tx_service.create_transaction(
        customer_id=1,
        amount="50.00",
        city="LAS VEGAS",
        device_id=device.device_id,
        transaction_time=datetime(2026, 6, 18, 23, 0, 0),
        status="APPROVED"
    )
    tx_service.tx_repo.create(tx1)

    # 11:15 PM - Approved LONDON transaction
    tx2 = tx_service.create_transaction(
        customer_id=1,
        amount="150.00",
        city="LONDON",
        device_id=device.device_id,
        transaction_time=datetime(2026, 6, 18, 23, 15, 0),
        status="APPROVED"
    )
    tx_service.tx_repo.create(tx2)

    # 11:30 PM - Declined LONDON transaction
    tx3 = tx_service.create_transaction(
        customer_id=1,
        amount="250.00",
        city="LONDON",
        device_id=device.device_id,
        transaction_time=datetime(2026, 6, 18, 23, 30, 0),
        status="DECLINED"
    )
    tx_service.tx_repo.create(tx3)
    db.commit()

    # Log some events corresponding to the timeline example:
    # 11:00 PM Transaction Created
    EventManager().log_event(
        event_type="TRANSACTION_CREATED",
        entity_type="TRANSACTION",
        entity_id=tx1.transaction_id,
        details={"customer_id": 1, "amount": "50.00"}
    )
    db.execute("UPDATE events SET created_at = %s WHERE entity_id = %s AND event_type = 'TRANSACTION_CREATED'", (datetime(2026, 6, 18, 23, 0, 0), str(tx1.transaction_id)))
    
    # 11:01 PM High Amount Rule Triggered (RULE_TRIGGERED)
    EventManager().log_event(
        event_type="RULE_TRIGGERED",
        entity_type="RULE",
        entity_id="High Transaction Amount",
        details={"transaction_id": tx1.transaction_id, "rule_name": "High Transaction Amount"}
    )
    db.execute("UPDATE events SET created_at = %s WHERE entity_id = 'High Transaction Amount' AND event_type = 'RULE_TRIGGERED'", (datetime(2026, 6, 18, 23, 1, 0),))
    
    # 11:02 PM Alert Generated (ALERT_GENERATED)
    alert = alert_service.generate_alert(
        transaction_id=tx1.transaction_id,
        customer_id=1,
        risk_score=75,
        severity="HIGH",
        status="OPEN"
    )
    db.execute("UPDATE events SET created_at = %s WHERE entity_id = %s AND event_type = 'ALERT_GENERATED'", (datetime(2026, 6, 18, 23, 2, 0), str(alert.alert_id)))
    
    # 11:03 PM Case Created (CASE_CREATED)
    case = case_service.create_case(
        alert_id=alert.alert_id,
        priority="HIGH",
        notes="Automated risk case creation"
    )
    db.execute("UPDATE events SET created_at = %s WHERE entity_id = %s AND event_type = 'CASE_CREATED'", (datetime(2026, 6, 18, 23, 3, 0), str(case.case_id)))

    # 11:10 PM Analyst Updated Case (CASE_UPDATED)
    case_service.assign_case(case.case_id, "Analyst Dave")
    db.execute("UPDATE events SET created_at = %s WHERE entity_id = %s AND event_type = 'CASE_UPDATED'", (datetime(2026, 6, 18, 23, 10, 0), str(case.case_id)))

    db.commit()

    # Create/update risk profile for Alice
    risk_profile_repo = RiskProfileRepository()
    existing_profiles = risk_profile_repo.search({"customer_id": 1})
    if existing_profiles:
        profile = existing_profiles[0]
        profile.current_risk_score = 75
        profile.risk_tier = "HIGH"
        risk_profile_repo.update(profile)
    else:
        profile = RiskProfile(
            profile_id=None,
            customer_id=1,
            current_risk_score=75,
            risk_tier="HIGH"
        )
        risk_profile_repo.create(profile)
    db.commit()

    # Create dynamic RiskHistory entry
    risk_history_repo = RiskHistoryRepository()
    rh_entry = RiskHistory(
        history_id=None,
        customer_id=1,
        previous_risk_score=20,
        new_risk_score=75,
        reason="Triggered High Amount and Velocity fraud alerts",
        recorded_at=datetime(2026, 6, 18, 23, 5, 0)
    )
    risk_history_repo.create(rh_entry)
    db.commit()

    # 3. Perform Investigation
    investigation = investigation_service.investigate_customer(1)

    # 4. Assertions on investigation object
    assert investigation["customer_profile"] is not None
    assert investigation["customer_profile"]["customer_id"] == 1
    assert investigation["customer_profile"]["first_name"] == "Alice"
    
    assert investigation["trust_score"] == 25 # 100 - 75 risk score from risk profile (profile score is updated by procedures or set to 75 in database)
    assert investigation["fraud_attempts"] == 1 # 1 declined tx (tx3)
    assert investigation["most_frequent_city"] == "LONDON" # 2 London, 1 Las Vegas
    assert investigation["average_amount"] == 150.00 # (50 + 150 + 250) / 3 = 150
    
    assert len(investigation["devices_used"]) == 1
    assert investigation["devices_used"][0]["operating_system"] == "macOS"

    assert len(investigation["risk_history"]) == 1
    assert investigation["risk_history"][0]["new_risk_score"] == 75

    # 5. Assertions on Timeline
    timeline = investigation["timeline"]
    print("\nGenerated Timeline Output:")
    for line in timeline:
        print(f" - {line}")
    
    assert len(timeline) >= 5
    assert any("Transaction Created" in line for line in timeline)
    assert any("High Amount Rule Triggered" in line for line in timeline)
    assert any("Alert Generated" in line for line in timeline)
    assert any("Case Created" in line for line in timeline)
    assert any("Analyst Updated Case" in line for line in timeline)
    
    # Check that INVESTIGATION_STARTED event is created in database
    ev_investigation = db.fetch_all("SELECT * FROM events WHERE event_type = 'INVESTIGATION_STARTED'")
    assert len(ev_investigation) == 1
    assert ev_investigation[0]["entity_id"] == "1"
    
    print("\n  [PASS] Timeline and investigation database flows verified successfully!")


def main():
    print("==================================================")
    print("       Investigation Engine Verification")
    print("==================================================")
    
    reinit_db()
    test_investigation_calculations()
    test_investigation_service_flow()
    
    print("\n==================================================")
    print("        All Investigation Engine Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
