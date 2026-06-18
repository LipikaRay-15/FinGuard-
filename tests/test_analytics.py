import os
import sys
import subprocess
from datetime import datetime, timedelta
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
from models import RiskHistory, RiskProfile, Alert, Case, Transaction
from repositories import (
    RiskHistoryRepository, 
    RiskProfileRepository, 
    AlertRepository, 
    CaseRepository, 
    TransactionRepository
)
from services import (
    MerchantProfileService,
    RiskHistoryService,
    AnalyticsService,
    TransactionService
)


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_analytics_and_profile_services():
    db = DatabaseConnection()
    
    # 1. Clean up seeded transaction registers to prevent default seeds interference
    db.execute("DELETE FROM rule_execution_logs")
    db.execute("DELETE FROM cases")
    db.execute("DELETE FROM alerts")
    db.execute("DELETE FROM transactions")
    db.execute("DELETE FROM risk_history")
    db.execute("DELETE FROM risk_profiles")
    db.commit()

    tx_service = TransactionService()
    alert_repo = AlertRepository()
    case_repo = CaseRepository()
    risk_profile_repo = RiskProfileRepository()
    risk_history_repo = RiskHistoryRepository()

    # 2. Insert test transactions
    # Laser Vegas coordinates: 36.1716, -115.1398 (Supermarket Mall, ID 1)
    # London coordinates: 51.5074, -0.1278 (Vegas Crypto Casino, ID 2)
    # New York coordinates: 40.7128, -74.0060 (Golden Pawn Shop, ID 3)
    
    # Tx 1: Customer 1, amount 100.00, APPROVED, city Las Vegas
    tx1 = Transaction(
        transaction_id=None,
        customer_id=1,
        merchant_id=1,
        device_id=1,
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        status="APPROVED",
        location_latitude=Decimal("36.1716"),
        location_longitude=Decimal("-115.1398"),
        transaction_time=datetime(2026, 6, 18, 10, 0, 0)
    )
    tx_service.tx_repo.create(tx1)

    # Tx 2: Customer 1, amount 500.00, DECLINED, city London
    tx2 = Transaction(
        transaction_id=None,
        customer_id=1,
        merchant_id=2,
        device_id=1,
        amount=Decimal("500.00"),
        currency="USD",
        transaction_type="PURCHASE",
        status="DECLINED",
        location_latitude=Decimal("51.5074"),
        location_longitude=Decimal("-0.1278"),
        transaction_time=datetime(2026, 6, 18, 11, 0, 0)
    )
    tx_service.tx_repo.create(tx2)

    # Tx 3: Customer 2, amount 12000.00, DECLINED, city New York
    tx3 = Transaction(
        transaction_id=None,
        customer_id=2,
        merchant_id=3,
        device_id=1,
        amount=Decimal("12000.00"),
        currency="USD",
        transaction_type="PURCHASE",
        status="DECLINED",
        location_latitude=Decimal("40.7128"),
        location_longitude=Decimal("-74.0060"),
        transaction_time=datetime(2026, 6, 18, 12, 0, 0)
    )
    tx_service.tx_repo.create(tx3)
    db.commit()

    # 3. Create test Alerts
    # Alert 1: Tx 2, Customer 1, risk score 75, severity HIGH, status OPEN
    a1 = Alert(
        alert_id=None,
        transaction_id=tx2.transaction_id,
        customer_id=1,
        risk_score=75,
        severity="HIGH",
        status="OPEN",
        created_at=datetime(2026, 6, 18, 11, 1, 0)
    )
    alert_repo.create(a1)

    # Alert 2: Tx 3, Customer 2, risk score 90, severity CRITICAL, status FALSE_POSITIVE
    a2 = Alert(
        alert_id=None,
        transaction_id=tx3.transaction_id,
        customer_id=2,
        risk_score=90,
        severity="CRITICAL",
        status="FALSE_POSITIVE",
        created_at=datetime(2026, 6, 18, 12, 1, 0)
    )
    alert_repo.create(a2)
    db.commit()

    # 4. Create test Cases
    # Case 1: Alert 1, status OPEN
    c1 = Case(
        case_id=None,
        alert_id=a1.alert_id,
        assigned_to="System Queue",
        status="OPEN",
        priority="HIGH",
        created_at=datetime(2026, 6, 18, 11, 2, 0),
        updated_at=datetime(2026, 6, 18, 11, 2, 0)
    )
    case_repo.create(c1)

    # Case 2: Alert 2, status RESOLVED (created at 12:02, resolved at 12:32 -> 30 mins = 1800s resolution)
    c2 = Case(
        case_id=None,
        alert_id=a2.alert_id,
        assigned_to="Analyst Sarah",
        status="RESOLVED",
        priority="HIGH",
        resolution="Legitimate corporate transaction",
        created_at=datetime(2026, 6, 18, 12, 2, 0),
        updated_at=datetime(2026, 6, 18, 12, 32, 0)
    )
    case_repo.create(c2)
    db.commit()

    # 5. Populate Rule Execution Logs
    db.execute(
        "INSERT INTO rule_execution_logs (transaction_id, rule_id, rule_name, triggered, risk_score_awarded, severity) "
        "VALUES (%s, 3, 'High-Risk Merchant Category', TRUE, 60, 'MEDIUM')",
        (tx2.transaction_id,)
    )
    db.execute(
        "INSERT INTO rule_execution_logs (transaction_id, rule_id, rule_name, triggered, risk_score_awarded, severity) "
        "VALUES (%s, 1, 'High Transaction Amount', TRUE, 75, 'HIGH')",
        (tx3.transaction_id,)
    )
    db.commit()

    # 6. Populate Risk Profiles
    # Customer 1 (Alice): score 75, tier HIGH
    rp1 = RiskProfile(
        profile_id=None,
        customer_id=1,
        current_risk_score=75,
        risk_tier="HIGH"
    )
    risk_profile_repo.create(rp1)

    # Customer 2 (Bob): score 100, tier CRITICAL
    rp2 = RiskProfile(
        profile_id=None,
        customer_id=2,
        current_risk_score=100,
        risk_tier="CRITICAL"
    )
    risk_profile_repo.create(rp2)
    db.commit()

    # 7. Populate Risk History
    rh1 = RiskHistory(
        history_id=None,
        customer_id=1,
        previous_risk_score=20,
        new_risk_score=75,
        reason="Triggered High-Risk Merchant Category alert",
        recorded_at=datetime(2026, 6, 18, 11, 5, 0)
    )
    risk_history_repo.create(rh1)

    rh2 = RiskHistory(
        history_id=None,
        customer_id=2,
        previous_risk_score=10,
        new_risk_score=100,
        reason="Triggered High Transaction Amount alert",
        recorded_at=datetime(2026, 6, 18, 12, 5, 0)
    )
    risk_history_repo.create(rh2)
    db.commit()

    # --------------------------------------------------
    # Verify MerchantProfileService
    # --------------------------------------------------
    print("Testing: MerchantProfileService aggregates query...")
    merchant_service = MerchantProfileService()
    merchants_stats = merchant_service.get_merchant_analytics()
    
    assert len(merchants_stats) > 0
    # Mapped from seeded profiles: MCC 7995 (Vegas Crypto Casino, merchant_id 2) has 1 decline (fraud_count = 1)
    gambling_mcc = [m for m in merchants_stats if m["merchant_category"] == "7995"]
    assert len(gambling_mcc) == 1
    assert gambling_mcc[0]["fraud_count"] == 1
    assert gambling_mcc[0]["average_score"] == 75.00
    assert gambling_mcc[0]["risk_level"] == "HIGH"
    print("  [PASS] MerchantProfileService analytics assertions verified.")

    # --------------------------------------------------
    # Verify RiskHistoryService
    # --------------------------------------------------
    print("\nTesting: RiskHistoryService projection and mappings...")
    risk_history_service = RiskHistoryService()
    
    # Test customer 1 details
    rh_details = risk_history_service.get_risk_history(customer_id=1)
    assert len(rh_details) == 1
    assert rh_details[0]["customer_id"] == 1
    assert rh_details[0]["score"] == 75
    assert rh_details[0]["risk_level"] == "HIGH"
    assert isinstance(rh_details[0]["timestamp"], datetime)
    
    # Test all details
    all_details = risk_history_service.get_risk_history()
    assert len(all_details) == 2
    assert all_details[0]["score"] == 100 # sorted descending recorded_at
    assert all_details[0]["risk_level"] == "CRITICAL"
    print("  [PASS] RiskHistoryService projections verified.")

    # --------------------------------------------------
    # Verify AnalyticsService
    # --------------------------------------------------
    print("\nTesting: AnalyticsService dashboard aggregations...")
    analytics_service = AnalyticsService()
    summary = analytics_service.get_system_analytics()

    # Fraud Percentage: (2 declined tx / 3 total tx) * 100 = 66.67%
    assert summary["fraud_percentage"] == 66.67
    
    # Average transaction amount: (100.00 + 500.00 + 12000.00) / 3 = 4200.00
    assert summary["average_transaction_amount"] == 4200.00
    
    # False Positive Ratio: (1 false positive alert / 2 total alerts) * 100 = 50.00%
    assert summary["false_positive_ratio"] == 50.00

    # Top Risky Customers (descending score ranking)
    assert len(summary["top_risky_customers"]) == 2
    assert summary["top_risky_customers"][0]["customer_id"] == 2
    assert summary["top_risky_customers"][0]["risk_score"] == 100
    assert summary["top_risky_customers"][0]["risk_tier"] == "CRITICAL"
    assert "Bob" in summary["top_risky_customers"][0]["customer_name"]
    
    # Case Resolution Time: resolved case took 30 mins = 1800s. Average of resolved/closed cases is 1800.0
    assert summary["case_resolution_time"] == 1800.0

    # Alert distributions counts
    assert summary["alert_distribution"]["status_distribution"]["OPEN"] == 1
    assert summary["alert_distribution"]["status_distribution"]["FALSE_POSITIVE"] == 1
    assert summary["alert_distribution"]["severity_distribution"]["HIGH"] == 1
    assert summary["alert_distribution"]["severity_distribution"]["CRITICAL"] == 1

    # Most Triggered Rules
    assert len(summary["most_triggered_rules"]) == 2
    # both rules executed once
    rule_names = {r["rule_name"] for r in summary["most_triggered_rules"]}
    assert "High Transaction Amount" in rule_names
    assert "High-Risk Merchant Category" in rule_names

    # Daily trends (18 June 2026 has 3 total tx, 2 fraud)
    assert len(summary["daily_trends"]) == 1
    assert summary["daily_trends"][0]["date"] == "2026-06-18"
    assert summary["daily_trends"][0]["transaction_count"] == 3
    assert summary["daily_trends"][0]["fraud_count"] == 2

    # Hourly trends (hours 10, 11, 12 should have 1 transaction frequency counts)
    hourly = summary["hourly_trends"]
    assert len(hourly) == 24
    assert hourly[10]["transaction_count"] == 1
    assert hourly[11]["transaction_count"] == 1
    assert hourly[12]["transaction_count"] == 1
    
    print("  [PASS] AnalyticsService metrics aggregates checked successfully.")


def main():
    print("==================================================")
    print("        Analytics Engine Verification")
    print("==================================================\n")
    
    reinit_db()
    test_analytics_and_profile_services()
    
    print("\n==================================================")
    print("         All Analytics Engine Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
