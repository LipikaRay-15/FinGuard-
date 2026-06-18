import os
import sys
import subprocess
from datetime import datetime
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
settings.setup_logging()

from database import DatabaseConnection
from models import Transaction
from engines.explainable_risk_engine import ExplainableRiskEngine
from services.risk_explanation_service import RiskExplanationService
from services.transaction_service import TransactionService
from engines.fraud_detection_engine import FraudDetectionEngine


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_pure_engine():
    print("Testing: ExplainableRiskEngine pure logic...")
    engine = ExplainableRiskEngine()
    
    # 1. Recommended Actions
    assert engine.generate_recommended_action("LOW") == "Auto-Approve"
    assert engine.generate_recommended_action("MEDIUM") == "Manual Review Required"
    assert engine.generate_recommended_action("HIGH") == "Manual Review Required"
    assert engine.generate_recommended_action("CRITICAL") == "Auto-Decline & Suspend Account"
    
    # 2. Reason Lists formatting
    mock_rules = [
        {"rule_name": "High Transaction Amount", "risk_points": 30},
        {"rule_name": "Rapid Velocity Limit", "risk_points": 35},
        {"rule_name": "New Device", "risk_points": 20},
        {"rule_name": "Night Transaction", "risk_points": 10},
        {"rule_name": "Custom Unmapped Rule", "risk_points": 15}
    ]
    reasons = engine.generate_reason_list(mock_rules)
    assert len(reasons) == 5
    assert reasons[0] == "✓ High Amount detected (+30)"
    assert reasons[1] == "✓ Velocity Fraud detected (+35)"
    assert reasons[2] == "✓ New Device detected (+20)"
    assert reasons[3] == "✓ Night Transaction detected (+10)"
    assert reasons[4] == "✓ Custom Unmapped Rule detected (+15)"
    
    # 3. Explanation output string formatting
    explanation = engine.generate_explanation(
        transaction_code="TXN48291",
        risk_score=95,
        risk_level="HIGH",
        triggered_rules=mock_rules[:4],
        severity="HIGH",
        confidence=92.0
    )
    
    expected_layout = (
        "Transaction TXN48291\n"
        "Risk Score: 95\n"
        "Risk Level: HIGH\n"
        "Triggered Rules:\n"
        "✓ High Amount detected (+30)\n"
        "✓ Velocity Fraud detected (+35)\n"
        "✓ New Device detected (+20)\n"
        "✓ Night Transaction detected (+10)\n"
        "Severity:\n"
        "HIGH\n"
        "Confidence:\n"
        "92%\n"
        "Recommended Action:\n"
        "Manual Review Required"
    )
    
    assert explanation.strip() == expected_layout.strip()
    
    # 4. Summary formatting
    summary = engine.generate_summary("TXN48291", 95, "HIGH", "HIGH", 92.0)
    assert "TXN48291" in summary
    assert "HIGH" in summary
    assert "95" in summary
    
    print("  [PASS] ExplainableRiskEngine pure logic tests succeeded.")


def test_service_integration(service: RiskExplanationService, engine_fd: FraudDetectionEngine, tx_service: TransactionService, db: DatabaseConnection):
    print("\nTesting: RiskExplanationService database integration...")
    
    # Create a transaction for Alice (Customer 1)
    # Give it values to trigger: High Transaction Amount, Night Transaction (hour=23), New Device (device_id=999)
    # The transaction has latitude/longitude/merchant details to keep confidence high
    tx = Transaction(
        transaction_id=None,
        customer_id=1,
        merchant_id=1,
        device_id=2, # Seeded device ID not yet used by customer 1
        amount="15000.00", # > 10000
        currency="USD",
        transaction_type="PURCHASE",
        status="PENDING",
        location_latitude=Decimal("40.7128"),
        location_longitude=Decimal("-74.0060"),
        transaction_time=datetime(2026, 6, 18, 23, 15, 0) # Night hours (between 22 and 6)
    )
    
    db_tx = tx_service.tx_repo.create(tx)
    db.commit()
    
    # Run the fraud detector scanning flow
    engine_fd.detect_fraud(db_tx.transaction_id)
    
    # Generate explanation from service
    explanation = service.generate_explanation(db_tx.transaction_id)
    print("\nGenerated Explanation Output:")
    print("-" * 40)
    print(explanation)
    print("-" * 40)
    
    # Asserts
    assert f"Transaction TXN{db_tx.transaction_id}" in explanation
    assert "Risk Score: 165" in explanation # 75 + 40 + 50 = 165 (uncapped SUM)
    assert "Risk Level: CRITICAL" in explanation
    assert "✓ High Amount detected (+75)" in explanation
    assert "✓ Night Transaction detected (+40)" in explanation
    assert "✓ New Device detected (+50)" in explanation
    assert "Severity:\nHIGH" in explanation or "Severity:\nCRITICAL" in explanation
    assert "Confidence:" in explanation
    assert "Recommended Action:\nAuto-Decline & Suspend Account" in explanation
    
    # Summary & Reason list direct checks
    summary = service.generate_summary(db_tx.transaction_id)
    assert f"TXN{db_tx.transaction_id}" in summary
    assert "CRITICAL" in summary
    
    reasons = service.generate_reason_list(db_tx.transaction_id)
    assert any("High Amount detected" in r for r in reasons)
    
    print("  [PASS] RiskExplanationService database integration verified successfully.")


def main():
    print("==================================================")
    print("      RiskExplanationService Verification Tests")
    print("==================================================\n")
    
    reinit_db()
    db = DatabaseConnection()
    
    test_pure_engine()
    
    # Set up engine & services
    engine_fd = FraudDetectionEngine()
    tx_service = TransactionService()
    service = RiskExplanationService()
    
    test_service_integration(service, engine_fd, tx_service, db)
    
    print("\n==================================================")
    print("         All Risk Explanation Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
