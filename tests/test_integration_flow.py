import sys
import os
import unittest
import subprocess
from decimal import Decimal
from datetime import datetime

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import DatabaseConnection
from services import (
    CustomerService, 
    TransactionService, 
    AlertService, 
    CaseService,
    BlacklistService,
    WhitelistService
)

class TestIntegrationFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reset the database schema using run_schema.py
        print("\n[SetupClass] Resetting database schema for integration testing...")
        schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
        subprocess.run([sys.executable, schema_script], check=True)
        print("[SetupClass] Database reset completed successfully.\n")

    def setUp(self):
        self.db = DatabaseConnection()
        self.customer_service = CustomerService()
        self.transaction_service = TransactionService()
        self.alert_service = AlertService()
        self.case_service = CaseService()
        self.blacklist_service = BlacklistService()
        self.whitelist_service = WhitelistService()

    def tearDown(self):
        self.db.commit()

    def test_e2e_finguard_pipeline(self):
        # 1. Create active Customer
        customer = self.customer_service.create_customer(
            first_name="Alice",
            last_name="Investigator",
            email="alice.inv@example.com",
            phone="+919999888877",
            pan="ABCDE1111A",
            account_number="1111222233",
            pincode="751024"
        )
        self.assertIsNotNone(customer.customer_id)
        
        # Verify customer created in DB
        cust_row = self.db.fetch_one("SELECT status FROM customers WHERE customer_id = %s", (customer.customer_id,))
        self.assertEqual(cust_row["status"], "ACTIVE")

        # 2. Add Transaction (Normal, below rules thresholds)
        # Category "SUPERMARKET" (MCC 5411) in location coordinates of MUMBAI (19.0760, 72.8777)
        tx1 = self.transaction_service.create_transaction(
            customer_id=customer.customer_id,
            amount=Decimal("150.00"),
            city="MUMBAI",
            merchant_category="SUPERMARKET",
            device_fingerprint="dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa4"
        )
        saved_tx1 = self.transaction_service.save_transaction(tx1)
        self.assertEqual(saved_tx1.status, "APPROVED")

        # Verify no alerts were created for this transaction
        alert_row1 = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts WHERE transaction_id = %s", (saved_tx1.transaction_id,))
        self.assertEqual(alert_row1["cnt"], 0)

        # 3. Add High Risk Transaction (Extreme Amount, should trigger High Transaction Amount check)
        # Category "CASINO" (MCC 7995) in location coordinates of LAS VEGAS (36.1716, -115.1398)
        # This triggers both High-Risk MCC rules and High Amount rule (points: 75 + 60)
        tx2 = self.transaction_service.create_transaction(
            customer_id=customer.customer_id,
            amount=Decimal("25000.00"),
            city="LAS VEGAS",
            merchant_category="CASINO",
            device_fingerprint="dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa4"
        )
        saved_tx2 = self.transaction_service.save_transaction(tx2)
        
        # Decision must be FLAGGED or DECLINED due to risk points
        self.assertIn(saved_tx2.status, ("FLAGGED", "DECLINED"))

        # Verify an Alert was automatically created
        alert_row2 = self.db.fetch_one("SELECT alert_id, risk_score, status FROM alerts WHERE transaction_id = %s", (saved_tx2.transaction_id,))
        self.assertIsNotNone(alert_row2)
        alert_id = alert_row2["alert_id"]
        self.assertGreater(alert_row2["risk_score"], 50)
        self.assertEqual(alert_row2["status"], "OPEN")

        # Verify a Case was automatically created for the alert in 'OPEN' state
        case_row = self.db.fetch_one("SELECT case_id, status, assigned_to FROM cases WHERE alert_id = %s", (alert_id,))
        self.assertIsNotNone(case_row)
        case_id = case_row["case_id"]
        self.assertEqual(case_row["status"], "OPEN")

        # 4. Perform case workflow transitions (Assign Case -> Under Review -> Analyst Note -> Resolved -> Closed)
        # Assign case
        self.case_service.assign_case(case_id, "Analyst James")
        case_check = self.db.fetch_one("SELECT assigned_to FROM cases WHERE case_id = %s", (case_id,))
        self.assertEqual(case_check["assigned_to"], "Analyst James")

        # Transition Case to UNDER_REVIEW
        self.case_service.change_status(case_id, "UNDER_REVIEW")
        case_check = self.db.fetch_one("SELECT status FROM cases WHERE case_id = %s", (case_id,))
        self.assertEqual(case_check["status"], "UNDER_REVIEW")

        # Add note
        self.case_service.add_analyst_note(case_id, "Verified user context via token check.")
        
        # Resolve Case
        self.case_service.resolve_case(case_id, "False alert, customer verified transaction details")
        case_check = self.db.fetch_one("SELECT status, resolution FROM cases WHERE case_id = %s", (case_id,))
        self.assertEqual(case_check["status"], "RESOLVED")
        self.assertEqual(case_check["resolution"], "False alert, customer verified transaction details")

        # Close Case
        self.case_service.close_case(case_id)
        case_check = self.db.fetch_one("SELECT status FROM cases WHERE case_id = %s", (case_id,))
        self.assertEqual(case_check["status"], "CLOSED")

        # 5. Verify Whitelist Bypass (Customer is whitelisted)
        self.whitelist_service.whitelist_customer(customer.customer_id, "Regular corporate risk tester profile")
        
        # Submit another high-risk transaction. Since the customer is whitelisted, it should immediately be APPROVED with 0 risk.
        tx3 = self.transaction_service.create_transaction(
            customer_id=customer.customer_id,
            amount=Decimal("50000.00"),
            city="LAS VEGAS",
            merchant_category="CASINO",
            device_fingerprint="dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa4"
        )
        saved_tx3 = self.transaction_service.save_transaction(tx3)
        self.assertEqual(saved_tx3.status, "APPROVED")

        # 6. Verify Blacklist Rejection (Customer is blacklisted)
        # Blacklist customer
        self.blacklist_service.blacklist_customer(customer.customer_id, "Chargeback trigger syndication link")
        
        # Customer status should now be BLOCKED
        cust_check = self.db.fetch_one("SELECT status FROM customers WHERE customer_id = %s", (customer.customer_id,))
        self.assertEqual(cust_check["status"], "BLOCKED")

        # Submit transaction on blocked customer. It must be declined/failed validation.
        tx4 = self.transaction_service.create_transaction(
            customer_id=customer.customer_id,
            amount=Decimal("10.00"),
            city="MUMBAI",
            merchant_category="SUPERMARKET",
            device_fingerprint="dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa4"
        )
        with self.assertRaises(Exception):
            self.transaction_service.save_transaction(tx4)

        # 7. Check audit logs were populated
        audit_row = self.db.fetch_one("SELECT COUNT(*) as cnt FROM audit_logs WHERE record_id = %s AND affected_table = 'cases'", (case_id,))
        self.assertGreater(audit_row["cnt"], 0)

if __name__ == "__main__":
    unittest.main()
