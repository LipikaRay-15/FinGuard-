import sys
import os
import unittest
from datetime import datetime

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from exceptions import ValidationException
from models import Customer, Device, Transaction, Alert, Case, FraudRule

class TestDomainModels(unittest.TestCase):
    def test_customer_validation(self):
        # 1. Valid customer
        c = Customer(
            customer_id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            status="ACTIVE",
            pan="ABCDE1234F",
            account_number="1234567890",
            pincode="110001",
            city="New Delhi",
            state="Delhi",
            country="India"
        )
        c.validate()  # Should not raise any exceptions

        # 2. Invalid first_name
        c.first_name = ""
        with self.assertRaises(ValidationException):
            c.validate()
        c.first_name = "John"

        # 3. Invalid last_name
        c.last_name = " "
        with self.assertRaises(ValidationException):
            c.validate()
        c.last_name = "Doe"

        # 4. Invalid email format
        c.email = "invalid_email"
        with self.assertRaises(ValidationException):
            c.validate()
        c.email = "john.doe@example.com"

        # 5. Invalid status
        c.status = "DEACTIVATED"
        with self.assertRaises(ValidationException):
            c.validate()
        c.status = "ACTIVE"

        # 6. Invalid PAN empty
        c.pan = ""
        with self.assertRaises(ValidationException):
            c.validate()
        c.pan = "ABCDE1234F"

        # 7. Invalid account number empty
        c.account_number = ""
        with self.assertRaises(ValidationException):
            c.validate()

    def test_device_validation(self):
        # 1. Valid device (64-character SHA-256 fingerprint hash)
        d_fingerprint = "a" * 64
        d = Device(
            device_id=1,
            device_fingerprint=d_fingerprint,
            ip_address="192.168.1.1",
            operating_system="Linux",
            user_agent="Firefox"
        )
        d.validate()

        # 2. Device fingerprint length != 64
        d.device_fingerprint = "short"
        with self.assertRaises(ValidationException):
            d.validate()
        d.device_fingerprint = d_fingerprint

        # 3. IP address empty
        d.ip_address = ""
        with self.assertRaises(ValidationException):
            d.validate()
        d.ip_address = "192.168.1.1"

        # 4. IP address invalid structure
        d.ip_address = "invalid_ip"
        with self.assertRaises(ValidationException):
            d.validate()

    def test_transaction_validation(self):
        # 1. Valid transaction
        t = Transaction(
            transaction_id=1,
            customer_id=10,
            merchant_id=20,
            device_id=30,
            amount=500.50,
            currency="USD",
            transaction_type="PURCHASE",
            status="PENDING",
            location_latitude=40.7128,
            location_longitude=-74.0060
        )
        t.validate()

        # 2. Negative amount
        t.amount = -10.00
        with self.assertRaises(ValidationException):
            t.validate()
        t.amount = 500.50

        # 3. Invalid currency length
        t.currency = "US"
        with self.assertRaises(ValidationException):
            t.validate()
        t.currency = "USD"

        # 4. Invalid transaction type
        t.transaction_type = "BILLPAY"
        with self.assertRaises(ValidationException):
            t.validate()
        t.transaction_type = "PURCHASE"

        # 5. Invalid status
        t.status = "CANCELLED"
        with self.assertRaises(ValidationException):
            t.validate()

    def test_alert_validation(self):
        # 1. Valid alert
        a = Alert(
            alert_id=1,
            transaction_id=10,
            customer_id=20,
            risk_score=75,
            severity="HIGH",
            status="OPEN",
            created_at=datetime.now()
        )
        a.validate()

        # 2. Negative risk score
        a.risk_score = -5
        with self.assertRaises(ValidationException):
            a.validate()
        a.risk_score = 75

        # 3. Score above 100
        a.risk_score = 105
        with self.assertRaises(ValidationException):
            a.validate()
        a.risk_score = 75

        # 4. Invalid severity
        a.severity = "VERY_HIGH"
        with self.assertRaises(ValidationException):
            a.validate()
        a.severity = "HIGH"

        # 5. Invalid status
        a.status = "COMPLETED"
        with self.assertRaises(ValidationException):
            a.validate()

    def test_case_validation(self):
        # 1. Valid case
        c = Case(
            case_id=1,
            alert_id=10,
            assigned_to="Investigator John",
            status="OPEN",
            priority="HIGH",
            notes="Suspicious casino volume",
            remarks=None,
            analyst_notes=None,
            resolution=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        c.validate()

        # 2. Invalid status
        c.status = "SUSPENDED"
        with self.assertRaises(ValidationException):
            c.validate()
        c.status = "OPEN"

        # 3. Invalid priority
        c.priority = "NONE"
        with self.assertRaises(ValidationException):
            c.validate()

    def test_fraud_rule_validation(self):
        # 1. Valid rule
        r = FraudRule(
            rule_id=1,
            rule_name="Velocity Rule",
            description="Checks velocity frequency",
            field_name="velocity",
            operator=">",
            threshold="3",
            risk_points=40,
            priority=1,
            severity="MEDIUM",
            enabled=True,
            stop_execution=False
        )
        r.validate()

        # 2. Missing rule name
        r.rule_name = ""
        with self.assertRaises(ValidationException):
            r.validate()
        r.rule_name = "Velocity Rule"

        # 3. Invalid risk points
        r.risk_points = -10
        with self.assertRaises(ValidationException):
            r.validate()
        r.risk_points = 40

        # 4. Invalid severity
        r.severity = "CRIT"
        with self.assertRaises(ValidationException):
            r.validate()

if __name__ == "__main__":
    unittest.main()
