import sys
import os
import unittest
from decimal import Decimal

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engines.risk_calculator import RiskCalculator
from models import Transaction

class TestRiskCalculator(unittest.TestCase):
    def test_calculate_score_aggregation_methods(self):
        rules = [
            {"rule_name": "Rule A", "risk_points": 50, "severity": "HIGH"},
            {"rule_name": "Rule B", "risk_points": 40, "severity": "MEDIUM"},
            {"rule_name": "Rule C", "risk_points": 30, "severity": "LOW"},
        ]
        
        # 1. SUM aggregation: 50 + 40 + 30 = 120
        self.assertEqual(RiskCalculator.calculate_score(rules, method="SUM"), 120)
        # 2. MAX aggregation: max(50, 40, 30) = 50
        self.assertEqual(RiskCalculator.calculate_score(rules, method="MAX"), 50)
        # 3. WEIGHTED aggregation:
        # Rule A (HIGH): 50 * 0.8 = 40.0
        # Rule B (MEDIUM): 40 * 0.5 = 20.0
        # Rule C (LOW): 30 * 0.2 = 6.0
        # Total = 40.0 + 20.0 + 6.0 = 66.0 -> 66
        self.assertEqual(RiskCalculator.calculate_score(rules, method="WEIGHTED"), 66)

        # Empty rule list returns 0
        self.assertEqual(RiskCalculator.calculate_score([], method="SUM"), 0)

    def test_determine_risk_level(self):
        # LOW (0-30)
        self.assertEqual(RiskCalculator.determine_risk_level(0), "LOW")
        self.assertEqual(RiskCalculator.determine_risk_level(30), "LOW")
        # MEDIUM (31-60)
        self.assertEqual(RiskCalculator.determine_risk_level(31), "MEDIUM")
        self.assertEqual(RiskCalculator.determine_risk_level(60), "MEDIUM")
        # HIGH (61-99)
        self.assertEqual(RiskCalculator.determine_risk_level(61), "HIGH")
        self.assertEqual(RiskCalculator.determine_risk_level(99), "HIGH")
        # CRITICAL (100+)
        self.assertEqual(RiskCalculator.determine_risk_level(100), "CRITICAL")
        self.assertEqual(RiskCalculator.determine_risk_level(150), "CRITICAL")

    def test_calculate_confidence(self):
        # Create a mock transaction with full fields populated
        tx = Transaction(
            transaction_id=1,
            customer_id=10,
            merchant_id=20,
            device_id=30,
            amount=Decimal("100.00"),
            currency="USD",
            transaction_type="PURCHASE",
            status="PENDING",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060")
        )

        # 1. Full details + high baseline volume (>=10 history items) -> 100.0% confidence
        conf = RiskCalculator.calculate_confidence(tx, history_count=12)
        self.assertEqual(conf, 100.0)

        # 2. Missing device_id -> -15%
        tx.device_id = None
        conf = RiskCalculator.calculate_confidence(tx, history_count=12)
        self.assertEqual(conf, 85.0)
        tx.device_id = 30

        # 3. Missing locations -> -15%
        tx.location_latitude = None
        tx.location_longitude = None
        conf = RiskCalculator.calculate_confidence(tx, history_count=12)
        self.assertEqual(conf, 85.0)
        tx.location_latitude = Decimal("40.7128")
        tx.location_longitude = Decimal("-74.0060")

        # 4. Low baseline history count (0 history items) -> -30%
        conf = RiskCalculator.calculate_confidence(tx, history_count=0)
        self.assertEqual(conf, 70.0)

        # 5. Low baseline history count (2 history items) -> -20%
        conf = RiskCalculator.calculate_confidence(tx, history_count=2)
        self.assertEqual(conf, 80.0)

        # 6. Low baseline history count (5 history items) -> -10%
        conf = RiskCalculator.calculate_confidence(tx, history_count=5)
        self.assertEqual(conf, 90.0)

        # 7. Floor cap (min confidence = 30.0%)
        # Strip all: device_id None (-15), merchant_id None (-10), location None (-15), history 0 (-30)
        # Expected: 100 - 15 - 10 - 15 - 30 = 30%
        tx.device_id = None
        tx.merchant_id = None
        tx.location_latitude = None
        tx.location_longitude = None
        conf = RiskCalculator.calculate_confidence(tx, history_count=0)
        self.assertEqual(conf, 30.0)

if __name__ == "__main__":
    unittest.main()
