import random
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple
from faker import Faker

from models import Customer, Transaction
from services import TransactionService, DeviceService
from repositories import TransactionRepository, MerchantRepository
from database import DatabaseConnection
from exceptions import TransactionException

logger = logging.getLogger("finguard.simulator.transaction_generator")


class TransactionGenerator:
    """
    Generates realistic transactions, distributing normal and fraud patterns across customers.
    """
    CITIES = ["NEW YORK", "LONDON", "LAS VEGAS", "PARIS", "TOKYO", "MUMBAI"]
    MERCHANT_CATEGORIES = ["SUPERMARKET", "GROCERY", "GAMBLING", "CASINO", "CRYPTOCURRENCY", "PAWNSHOP"]

    def __init__(self) -> None:
        self.fake = Faker()
        self.transaction_service = TransactionService()
        self.device_service = DeviceService()
        self.tx_repo = TransactionRepository()
        self.merchant_repo = MerchantRepository()
        self.db = DatabaseConnection()

    def _get_or_create_merchant(self, category: str) -> int:
        """
        Ensures a merchant profile exists for the given category and returns its ID.
        """
        norm_cat = category.strip().upper()
        mcc, name, risk = self.transaction_service.CATEGORY_MCC_MAP.get(
            norm_cat, 
            ("5411", f"Default Merchant ({category})", "LOW")
        )
        
        existing = self.merchant_repo.search({"merchant_category_code": mcc})
        if existing:
            return existing[0].merchant_id
        
        # Create new profile
        from models import MerchantProfile
        merchant = MerchantProfile(
            merchant_id=None,
            merchant_name=name,
            merchant_category_code=mcc,
            risk_level=risk,
            trust_score=20 if risk == "HIGH" else (70 if risk == "MEDIUM" else 100)
        )
        created = self.merchant_repo.create(merchant)
        self.db.commit()
        return created.merchant_id

    def generate_transactions(
        self, 
        customers: List[Customer], 
        count: int = 100000, 
        fraud_ratio: float = 0.05
    ) -> List[Transaction]:
        """
        Orchestrates transaction generation, sorting them chronologically to guarantee window-based rules trigger correctly.
        """
        logger.info(f"Preparing base simulation environment for {len(customers)} customers...")
        
        # Ensure we have merchants seeded
        merchant_ids = {}
        for cat in self.MERCHANT_CATEGORIES:
            merchant_ids[cat] = self._get_or_create_merchant(cat)

        # Generate a small pool of standard device fingerprints for each customer
        customer_devices: Dict[int, List[str]] = {}
        for cust in customers:
            customer_devices[cust.customer_id] = [
                self.fake.sha256() for _ in range(random.randint(1, 3))
            ]

        # Calculate time boundaries
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        # Define fraud and normal counts
        fraud_count = int(count * fraud_ratio)
        normal_count = count - fraud_count

        logger.info(f"Generating synthetic schedules: {normal_count} normal, {fraud_count} fraud...")
        
        raw_tx_configs = []

        # 1. Generate normal transactions
        for _ in range(normal_count):
            cust = random.choice(customers)
            device_fingerprint = random.choice(customer_devices[cust.customer_id])
            city = random.choice(self.CITIES)
            category = random.choice(["SUPERMARKET", "GROCERY"])
            amount = round(random.uniform(5.00, 800.00), 2)
            
            # Timestamp generation (avoiding late night hour spikes for normal transacting)
            ts = self.fake.date_time_between(start_date=start_time, end_date=end_time)
            # 85% transactions during day hours
            if random.random() < 0.85 and (ts.hour < 6 or ts.hour >= 22):
                ts = ts.replace(hour=random.randint(7, 21))

            raw_tx_configs.append({
                "type": "NORMAL",
                "customer_id": cust.customer_id,
                "amount": amount,
                "city": city,
                "category": category,
                "device_fingerprint": device_fingerprint,
                "timestamp": ts,
                "status": "PENDING"
            })

        # 2. Generate fraud scenarios (balanced across the 8 requested types)
        fraud_types = [
            "HIGH_AMOUNT", "VELOCITY", "NIGHT", "DORMANT", 
            "FAILED_ATTEMPTS", "MERCHANT_RISK", "LOCATION_JUMP", "DIFFERENT_DEVICES"
        ]

        for i in range(fraud_count):
            ftype = fraud_types[i % len(fraud_types)]
            cust = random.choice(customers)
            ts = self.fake.date_time_between(start_date=start_time, end_date=end_time)
            device_fingerprint = random.choice(customer_devices[cust.customer_id])
            city = random.choice(self.CITIES)

            if ftype == "HIGH_AMOUNT":
                raw_tx_configs.append({
                    "type": "HIGH_AMOUNT",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(11000.00, 50000.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts,
                    "status": "PENDING"
                })

            elif ftype == "VELOCITY":
                # Generate 4 transactions within 15 minutes
                base_ts = ts
                for j in range(4):
                    raw_tx_configs.append({
                        "type": "VELOCITY",
                        "customer_id": cust.customer_id,
                        "amount": round(random.uniform(100.00, 500.00), 2),
                        "city": city,
                        "category": "GROCERY",
                        "device_fingerprint": device_fingerprint,
                        "timestamp": base_ts + timedelta(minutes=j * 2),
                        "status": "PENDING"
                    })

            elif ftype == "NIGHT":
                # Night hours 22:00 to 06:00
                night_hour = random.choice([22, 23, 0, 1, 2, 3, 4, 5])
                ts = ts.replace(hour=night_hour, minute=random.randint(0, 59))
                raw_tx_configs.append({
                    "type": "NIGHT",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(50.00, 300.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts,
                    "status": "PENDING"
                })

            elif ftype == "DORMANT":
                # Create a transaction 100 days before this one
                past_ts = ts - timedelta(days=95)
                raw_tx_configs.append({
                    "type": "NORMAL",  # Baseline approved transaction
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(20.00, 150.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": past_ts,
                    "status": "APPROVED" # Force APPROVED status to make it active history
                })
                # The dormant triggering transaction
                raw_tx_configs.append({
                    "type": "DORMANT",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(100.00, 500.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts,
                    "status": "PENDING"
                })

            elif ftype == "FAILED_ATTEMPTS":
                # Create 4 declined transactions in the past hour
                base_ts = ts
                for j in range(4):
                    raw_tx_configs.append({
                        "type": "NORMAL",
                        "customer_id": cust.customer_id,
                        "amount": round(random.uniform(200.00, 800.00), 2),
                        "city": city,
                        "category": "SUPERMARKET",
                        "device_fingerprint": device_fingerprint,
                        "timestamp": base_ts - timedelta(minutes=(5 - j) * 5),
                        "status": "DECLINED" # Force DECLINED status to build history
                    })
                # The triggering transaction
                raw_tx_configs.append({
                    "type": "FAILED_ATTEMPTS",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(50.00, 200.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": base_ts,
                    "status": "PENDING"
                })

            elif ftype == "MERCHANT_RISK":
                category = random.choice(["GAMBLING", "CASINO", "PAWNSHOP"])
                raw_tx_configs.append({
                    "type": "MERCHANT_RISK",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(500.00, 2000.00), 2),
                    "city": "LAS VEGAS",
                    "category": category,
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts,
                    "status": "PENDING"
                })

            elif ftype == "LOCATION_JUMP":
                # First transaction in London
                raw_tx_configs.append({
                    "type": "NORMAL",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(50.00, 200.00), 2),
                    "city": "LONDON",
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts - timedelta(minutes=15),
                    "status": "APPROVED"
                })
                # Immediate second transaction in Tokyo (impossible jump)
                raw_tx_configs.append({
                    "type": "LOCATION_JUMP",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(100.00, 300.00), 2),
                    "city": "TOKYO",
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts,
                    "status": "PENDING"
                })

            elif ftype == "DIFFERENT_DEVICES":
                # Ensure customer has historical transaction on base device
                raw_tx_configs.append({
                    "type": "NORMAL",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(10.00, 100.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": device_fingerprint,
                    "timestamp": ts - timedelta(days=1),
                    "status": "APPROVED"
                })
                # Transaction on brand new device
                new_device = self.fake.sha256()
                raw_tx_configs.append({
                    "type": "DIFFERENT_DEVICES",
                    "customer_id": cust.customer_id,
                    "amount": round(random.uniform(20.00, 150.00), 2),
                    "city": city,
                    "category": "SUPERMARKET",
                    "device_fingerprint": new_device,
                    "timestamp": ts,
                    "status": "PENDING"
                })

        # Sort chronologically to simulate authentic transaction streaming
        raw_tx_configs.sort(key=lambda x: x["timestamp"])

        logger.info(f"Executing and evaluating {len(raw_tx_configs)} transactions in historical sequence...")
        
        saved_transactions: List[Transaction] = []
        success_count = 0

        for i, config in enumerate(raw_tx_configs, 1):
            try:
                # Construct transaction model
                tx = self.transaction_service.create_transaction(
                    customer_id=config["customer_id"],
                    amount=config["amount"],
                    city=config["city"],
                    merchant_category=config["category"],
                    transaction_type="PURCHASE",
                    status=config["status"],
                    transaction_time=config["timestamp"],
                    device_fingerprint=config["device_fingerprint"]
                )

                if config["status"] in ("APPROVED", "DECLINED"):
                    # Directly insert historical data rows into the DB
                    saved = self.tx_repo.create(tx)
                    self.db.commit()
                else:
                    # Run through live risk check validation pipeline (PENDING evaluation)
                    saved = self.transaction_service.save_transaction(tx)
                
                saved_transactions.append(saved)
                success_count += 1
                
                if success_count % 1000 == 0:
                    logger.info(f"Processed {success_count}/{len(raw_tx_configs)} transactions...")
            except Exception as e:
                # Rollback and log warning, continue simulation flow
                self.db.rollback()
                logger.warning(f"Error processing simulated transaction index {i} ({config['type']}): {e}")

        logger.info(f"Transaction simulation completed. Total processed: {success_count}/{len(raw_tx_configs)}")
        return saved_transactions
