import logging
from typing import List, Set
from faker import Faker

from models import Customer
from services.customer_service import CustomerService
from exceptions import DuplicateCustomerException, InvalidCustomerException

logger = logging.getLogger("finguard.simulator.customer_generator")


class CustomerGenerator:
    """
    Generates synthetic customer entities using Faker and inserts them via CustomerService.
    Ensures uniqueness constraints are satisfied using in-memory caches of PAN, email, phone, and account.
    """
    def __init__(self) -> None:
        self.fake = Faker()
        self.customer_service = CustomerService()

    def generate_customers(self, count: int) -> List[Customer]:
        """
        Generates and saves `count` unique customer records in MySQL.
        
        Returns:
            List of successfully persisted Customer models.
        """
        logger.info(f"Generating {count} synthetic customers...")
        generated_customers: List[Customer] = []
        
        # Track generated values in memory to avoid duplicate errors in loop
        generated_emails: Set[str] = set()
        generated_phones: Set[str] = set()
        generated_pans: Set[str] = set()
        generated_accounts: Set[str] = set()

        # Pre-populate sets with existing database values to prevent unique key violations
        try:
            existing = self.customer_service.search_customer({})
            for c in existing:
                if c.email:
                    generated_emails.add(c.email.lower())
                if c.phone:
                    generated_phones.add(c.phone)
                if c.pan:
                    generated_pans.add(c.pan.upper())
                if c.account_number:
                    generated_accounts.add(c.account_number)
        except Exception as e:
            logger.warning(f"Could not load existing customers to seed uniqueness sets: {e}")

        success_count = 0
        attempts = 0
        max_attempts = count * 3

        while success_count < count and attempts < max_attempts:
            attempts += 1
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            
            # Generate unique email
            email = self.fake.email().lower()
            while email in generated_emails:
                email = self.fake.email().lower()
                
            # Generate unique phone (matching validation: + prefix and 10 to 15 digits)
            phone_digits = "".join([str(self.fake.random_int(0, 9)) for _ in range(11)])
            phone = f"+1{phone_digits}"
            while phone in generated_phones:
                phone_digits = "".join([str(self.fake.random_int(0, 9)) for _ in range(11)])
                phone = f"+1{phone_digits}"

            # Generate unique PAN (5 letters, 4 digits, 1 letter)
            pan_letters1 = "".join([self.fake.random_element("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5)])
            pan_digits = "".join([str(self.fake.random_int(0, 9)) for _ in range(4)])
            pan_letter2 = self.fake.random_element("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            pan = f"{pan_letters1}{pan_digits}{pan_letter2}".upper()
            while pan in generated_pans:
                pan_letters1 = "".join([self.fake.random_element("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5)])
                pan_digits = "".join([str(self.fake.random_int(0, 9)) for _ in range(4)])
                pan_letter2 = self.fake.random_element("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                pan = f"{pan_letters1}{pan_digits}{pan_letter2}".upper()

            # Generate unique account number (10 to 15 digits)
            acct_len = self.fake.random_int(10, 15)
            account_number = "".join([str(self.fake.random_int(0, 9)) for _ in range(acct_len)])
            while account_number in generated_accounts:
                acct_len = self.fake.random_int(10, 15)
                account_number = "".join([str(self.fake.random_int(0, 9)) for _ in range(acct_len)])

            # Generate a 6-digit pincode
            pincode = str(self.fake.random_int(100000, 999999))

            try:
                cust = self.customer_service.create_customer(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    status="ACTIVE",
                    pan=pan,
                    account_number=account_number,
                    pincode=pincode
                )
                
                # Add to sets
                generated_emails.add(email)
                generated_phones.add(phone)
                generated_pans.add(pan)
                generated_accounts.add(account_number)
                
                generated_customers.append(cust)
                success_count += 1
                
                if success_count % 500 == 0:
                    logger.info(f"Generated {success_count}/{count} customers...")
            except (DuplicateCustomerException, InvalidCustomerException) as e:
                # Collision/validation error, retry
                logger.debug(f"Collision or validation error during generation (attempt {attempts}): {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error creating customer in generator: {e}", exc_info=True)
                raise

        logger.info(f"Customer generation completed. Target: {count}, Generated: {success_count}, Attempts: {attempts}")
        return generated_customers
