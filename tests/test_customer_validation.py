import sys
import os
import unittest
from datetime import date, datetime, timedelta

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from exceptions import (
    CustomerValidationException,
    FirstNameValidationError,
    LastNameValidationError,
    DOBValidationError,
    GenderValidationError,
    EmailValidationError,
    PhoneValidationError,
    PANValidationError,
    AccountNumberValidationError,
    PincodeValidationError,
    AddressValidationError
)
from models import Customer
from services import CustomerValidator, PincodeService

class TestCustomerValidation(unittest.TestCase):
    
    def test_valid_customer_full(self):
        c = Customer(
            customer_id=1,
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1995-05-15",
            gender="Prefer not to say",
            email="jane.doe@example.com",
            phone="+919876543210",
            status="ACTIVE",
            pan="ABCDE1234F",
            account_number="9876543210",
            pincode="751024",
            city="Bhubaneswar",
            state="Odisha",
            country="India",
            address="123 Financial District Building"
        )
        # Should not raise any exceptions
        c.validate()

    def test_missing_and_invalid_first_name(self):
        # Alphabets only, 2-50 length
        c = Customer(customer_id=1, first_name="", last_name="Doe", email="jane@example.com", pincode="110001")
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid First Name", ctx.exception.errors)

        c.first_name = "J"
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid First Name", ctx.exception.errors)

        c.first_name = "Jane12"
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid First Name", ctx.exception.errors)

    def test_missing_and_invalid_last_name(self):
        # Alphabets only, 2-50 length
        c = Customer(customer_id=1, first_name="Jane", last_name="", email="jane@example.com", pincode="110001")
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Last Name", ctx.exception.errors)

        c.last_name = "D"
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Last Name", ctx.exception.errors)

    def test_invalid_date_of_birth(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            date_of_birth="invalid-date", pincode="110001"
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Date of Birth", ctx.exception.errors)

        # Future date
        future_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        c.date_of_birth = future_date
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Date of Birth", ctx.exception.errors)

        # Under 18
        under_18 = (date.today() - timedelta(days=365 * 17)).strftime("%Y-%m-%d")
        c.date_of_birth = under_18
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Date of Birth", ctx.exception.errors)

    def test_invalid_gender(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            gender="InvalidGender", pincode="110001"
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Gender", ctx.exception.errors)

    def test_invalid_email(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="invalid_email", pincode="110001"
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Email", ctx.exception.errors)

    def test_invalid_phone(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            phone="12345", pincode="110001"
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Phone Number", ctx.exception.errors)

        # Invalid characters
        c.phone = "+9198765abc"
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Phone Number", ctx.exception.errors)

    def test_invalid_pan(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            pan="ABC1234", pincode="110001"
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid PAN", ctx.exception.errors)

    def test_invalid_account_number(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            account_number="1234567", pincode="110001" # too short (< 8)
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Account Number", ctx.exception.errors)

        c.account_number = "1234567890123456789", # too long (> 18)
        c.account_number = "1234567890123456789"
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Account Number", ctx.exception.errors)

        c.account_number = "1234567A90" # contains letter
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Account Number", ctx.exception.errors)

    def test_invalid_pincode(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            pincode="75102" # too short (< 6)
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Pincode", ctx.exception.errors)

        c.pincode = "7510245" # too long (> 6)
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Pincode", ctx.exception.errors)

        c.pincode = "75102A" # alphabetic
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Invalid Pincode", ctx.exception.errors)

    def test_invalid_address(self):
        c = Customer(
            customer_id=1, first_name="Jane", last_name="Doe", email="jane@example.com",
            address="Short", pincode="110001" # < 10 characters
        )
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Address too short", ctx.exception.errors)

        c.address = "A" * 201 # > 200 characters
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
        self.assertIn("Address too long", ctx.exception.errors)

    def test_pincode_auto_fetch(self):
        # Specific mappings test
        loc = PincodeService.fetch_location_from_pincode("751024")
        self.assertIsNotNone(loc)
        self.assertEqual(loc["city"], "Bhubaneswar")
        self.assertEqual(loc["state"], "Odisha")
        self.assertEqual(loc["country"], "India")

        # Specific mappings test
        loc = PincodeService.fetch_location_from_pincode("110001")
        self.assertIsNotNone(loc)
        self.assertEqual(loc["city"], "New Delhi")
        self.assertEqual(loc["state"], "Delhi")
        self.assertEqual(loc["country"], "India")

        # Generic fallback test
        loc = PincodeService.fetch_location_from_pincode("500099")
        self.assertIsNotNone(loc)
        self.assertEqual(loc["country"], "India")
        self.assertEqual(loc["state"], "Southern Region")

    def test_error_aggregation_formatting(self):
        # Create customer with multiple invalid fields:
        # Invalid email, invalid phone, invalid PAN, address too short
        c = Customer(
            customer_id=1,
            first_name="Jane",
            last_name="Doe",
            email="invalid_email",
            phone="12345",
            pan="ABC1234",
            pincode="ABC123", # invalid pincode
            address="Short"
        )
        
        with self.assertRaises(CustomerValidationException) as ctx:
            c.validate()
            
        ex = ctx.exception
        self.assertEqual(len(ex.errors), 5)
        self.assertIn("Invalid Email", ex.errors)
        self.assertIn("Invalid Phone Number", ex.errors)
        self.assertIn("Invalid PAN", ex.errors)
        self.assertIn("Invalid Pincode", ex.errors)
        self.assertIn("Address too short", ex.errors)
        
        # Verify str(ex) matches the expected aggregated format exactly
        expected_output = (
            "Validation Errors\n"
            "❌ Invalid Email\n"
            "❌ Invalid Phone Number\n"
            "❌ Invalid PAN\n"
            "❌ Invalid Pincode\n"
            "❌ Address too short\n"
            "Please correct the above fields."
        )
        self.assertEqual(str(ex), expected_output)

if __name__ == "__main__":
    unittest.main()
