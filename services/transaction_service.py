import logging
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from database import DatabaseConnection
from exceptions import (
    TransactionException,
    InvalidTransactionException,
    TransactionNotFoundException,
    CustomerNotFoundException
)
from models import Transaction, MerchantProfile, Device
from repositories import TransactionRepository, CustomerRepository, MerchantRepository
from services.device_service import DeviceService
from engines.transaction_engine import TransactionEngine


class TransactionService:
    """
    Service class responsible for coordinating transaction creation, validation,
    saving, querying, and risk check executions.
    """
    
    # Static coordinate mapping for common cities to support latitude/longitude translation
    CITY_COORDINATES = {
        "NEW YORK": (Decimal("40.7128"), Decimal("-74.0060")),
        "LONDON": (Decimal("51.5074"), Decimal("-0.1278")),
        "LAS VEGAS": (Decimal("36.1716"), Decimal("-115.1398")),
        "PARIS": (Decimal("48.8566"), Decimal("2.3522")),
        "TOKYO": (Decimal("35.6762"), Decimal("139.6503")),
        "MUMBAI": (Decimal("19.0760"), Decimal("72.8777")),
    }

    # Static category mapping to MCC code, default merchant names, and default risk levels
    CATEGORY_MCC_MAP = {
        "GAMBLING": ("7995", "Vegas Crypto Casino", "HIGH"),
        "CASINO": ("7995", "Vegas Crypto Casino", "HIGH"),
        "CRYPTOCURRENCY": ("7995", "Vegas Crypto Casino", "HIGH"),
        "PAWNSHOP": ("5933", "Golden Pawn Shop", "MEDIUM"),
        "SUPERMARKET": ("5411", "Supermarket Mall", "LOW"),
        "GROCERY": ("5411", "Supermarket Mall", "LOW"),
    }

    def __init__(self) -> None:
        self.tx_repo = TransactionRepository()
        self.customer_repo = CustomerRepository()
        self.merchant_repo = MerchantRepository()
        self.device_service = DeviceService()
        self.engine = TransactionEngine()
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.services.transaction_service")

    def create_transaction(
        self,
        customer_id: int,
        amount: Union[float, Decimal, str],
        merchant_id: Optional[int] = None,
        device_id: Optional[int] = None,
        city: Optional[str] = None,
        merchant_category: Optional[str] = None,
        currency: str = "USD",
        transaction_type: str = "PURCHASE",
        status: str = "PENDING",
        transaction_time: Optional[datetime] = None,
        location_latitude: Optional[Union[float, Decimal]] = None,
        location_longitude: Optional[Union[float, Decimal]] = None,
        device_fingerprint: Optional[str] = None
    ) -> Transaction:
        """
        Creates a Transaction domain model. Automatically generates/maps coordinates 
        from the city name, resolves the device fingerprint to an ID, and maps 
        the merchant category to a database merchant record.
        """
        self.logger.info(f"Creating transaction object for customer {customer_id}")
        
        # 1. Resolve City to Coordinates if latitude/longitude are not passed
        if city and location_latitude is None and location_longitude is None:
            normalized_city = city.strip().upper()
            if normalized_city in self.CITY_COORDINATES:
                location_latitude, location_longitude = self.CITY_COORDINATES[normalized_city]
                self.logger.debug(f"Resolved city '{city}' to ({location_latitude}, {location_longitude})")

        # 2. Resolve Device (by ID or device fingerprint hash)
        if device_fingerprint and device_id is None:
            try:
                device_obj = self.device_service.register_device(
                    device_fingerprint=device_fingerprint,
                    ip_address="127.0.0.1",
                    operating_system="Unknown OS",
                    user_agent="Unknown UserAgent"
                )
                device_id = device_obj.device_id
                self.logger.debug(f"Resolved device fingerprint to ID {device_id}")
            except Exception as e:
                self.logger.warning(f"Could not register device fingerprint: {e}")

        # 3. Resolve Merchant Category to Merchant ID
        if merchant_category and merchant_id is None:
            norm_category = merchant_category.strip().upper()
            # Map category name to MCC parameters
            mcc, name, risk = self.CATEGORY_MCC_MAP.get(
                norm_category, 
                ("5411", f"Default Merchant ({merchant_category})", "LOW")
            )
            
            # Find existing matching merchant profile or create one
            existing_merchants = self.merchant_repo.search({"merchant_category_code": mcc})
            if existing_merchants:
                merchant_id = existing_merchants[0].merchant_id
                self.logger.debug(f"Resolved merchant category '{merchant_category}' to ID {merchant_id}")
            else:
                try:
                    new_merchant = MerchantProfile(
                        merchant_id=None,
                        merchant_name=name,
                        merchant_category_code=mcc,
                        risk_level=risk,
                        trust_score=100
                    )
                    created_merchant = self.merchant_repo.create(new_merchant)
                    self.db.commit()
                    merchant_id = created_merchant.merchant_id
                    self.logger.info(f"Created new merchant profile for category '{merchant_category}', ID: {merchant_id}")
                except Exception as e:
                    self.db.rollback()
                    self.logger.warning(f"Failed to auto-create merchant profile: {e}")

        # 4. Construct Transaction model instance
        tx = Transaction(
            transaction_id=None,
            customer_id=customer_id,
            merchant_id=merchant_id,
            device_id=device_id,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            status=status,
            location_latitude=location_latitude,
            location_longitude=location_longitude,
            transaction_time=transaction_time
        )
        
        # Attach dynamic properties for service layer use
        tx.city = city
        tx.merchant_category = merchant_category
        return tx

    def validate_transaction(self, transaction: Transaction) -> None:
        """
        Validates transaction field properties and checks customer status validity.
        
        Raises:
            InvalidTransactionException: If validation fails or the customer status is not ACTIVE.
            CustomerNotFoundException: If the customer does not exist in the database.
        """
        # Validate baseline model constraints (raises ValidationException)
        try:
            transaction.validate()
        except Exception as ve:
            raise InvalidTransactionException(f"Transaction validation failed: {ve}")

        # Check customer existence and status checks
        customer = self.customer_repo.find_by_id(transaction.customer_id)
        if not customer:
            raise CustomerNotFoundException(f"Customer with ID {transaction.customer_id} not found.")

        if customer.status in ("SUSPENDED", "BLOCKED"):
            raise InvalidTransactionException(
                f"Transaction rejected: customer {customer.customer_id} status is {customer.status}."
            )

    def save_transaction(self, transaction: Transaction) -> Transaction:
        """
        Validates the transaction, saves it to the database with a PENDING status,
        triggers risk evaluation via the TransactionEngine, and commits.
        
        Returns:
            The fully evaluated, updated Transaction instance.
            
        Raises:
            TransactionException: For database or processing failures.
        """
        from engines.event_manager import EventManager
        # Run validations (Customer status and basic constraints)
        try:
            self.validate_transaction(transaction)
        except Exception as e:
            EventManager().log_event(
                event_type="TRANSACTION_FAILED",
                entity_type="TRANSACTION",
                entity_id=None,
                details={
                    "customer_id": transaction.customer_id,
                    "amount": str(transaction.amount),
                    "error": str(e)
                }
            )
            raise

        try:
            # Force status to PENDING for new saves
            transaction.status = "PENDING"
            
            # Save the transaction record to generate automatic transaction ID
            saved_tx = self.tx_repo.create(transaction)
            self.db.commit()
            
            self.logger.info(f"Saved transaction ID {saved_tx.transaction_id} successfully. Running fraud checks...")
            
            # Run the risk assessment stored procedure via TransactionEngine
            risk_score, decision = self.engine.evaluate_transaction_risk(saved_tx.transaction_id)
            self.db.commit()
            
            # Retrieve the updated transaction status and parameters
            evaluated_tx = self.tx_repo.find_by_id(saved_tx.transaction_id)
            if not evaluated_tx:
                raise TransactionNotFoundException(f"Transaction ID {saved_tx.transaction_id} not found after assessment.")

            # Copy dynamic values back to the refreshed object
            evaluated_tx.city = getattr(transaction, "city", None)
            evaluated_tx.merchant_category = getattr(transaction, "merchant_category", None)
            
            # Log Events
            # 1. TRANSACTION_CREATED or TRANSACTION_FAILED
            if evaluated_tx.status == "DECLINED":
                EventManager().log_event(
                    event_type="TRANSACTION_FAILED",
                    entity_type="TRANSACTION",
                    entity_id=evaluated_tx.transaction_id,
                    details={
                        "customer_id": evaluated_tx.customer_id,
                        "amount": str(evaluated_tx.amount),
                        "reason": "Risk score evaluated above threshold or blacklisted"
                    }
                )
            else:
                EventManager().log_event(
                    event_type="TRANSACTION_CREATED",
                    entity_type="TRANSACTION",
                    entity_id=evaluated_tx.transaction_id,
                    details={
                        "customer_id": evaluated_tx.customer_id,
                        "amount": str(evaluated_tx.amount),
                        "status": evaluated_tx.status
                    }
                )

            # 2. RULE_TRIGGERED
            rules_query = """
                SELECT rel.execution_id, fr.rule_name, rel.risk_score_awarded 
                FROM rule_execution_logs rel 
                JOIN fraud_rules fr ON rel.rule_id = fr.rule_id 
                WHERE rel.transaction_id = %s AND rel.triggered = TRUE
            """
            triggered_rules = self.db.fetch_all(rules_query, (evaluated_tx.transaction_id,))
            for rule in triggered_rules:
                EventManager().log_event(
                    event_type="RULE_TRIGGERED",
                    entity_type="RULE",
                    entity_id=rule["rule_name"],
                    details={
                        "transaction_id": evaluated_tx.transaction_id,
                        "risk_score_awarded": rule["risk_score_awarded"]
                    }
                )

            # 3. ALERT_GENERATED
            alert_row = self.db.fetch_one(
                "SELECT alert_id, risk_score, status FROM alerts WHERE transaction_id = %s",
                (evaluated_tx.transaction_id,)
            )
            if alert_row:
                EventManager().log_event(
                    event_type="ALERT_GENERATED",
                    entity_type="ALERT",
                    entity_id=alert_row["alert_id"],
                    details={
                        "transaction_id": evaluated_tx.transaction_id,
                        "customer_id": evaluated_tx.customer_id,
                        "risk_score": alert_row["risk_score"],
                        "status": alert_row["status"]
                    }
                )
                
                # 4. CASE_CREATED
                case_row = self.db.fetch_one(
                    "SELECT case_id, assigned_to, priority, status FROM cases WHERE alert_id = %s",
                    (alert_row["alert_id"],)
                )
                if case_row:
                    EventManager().log_event(
                        event_type="CASE_CREATED",
                        entity_type="CASE",
                        entity_id=case_row["case_id"],
                        details={
                            "alert_id": alert_row["alert_id"],
                            "assigned_to": case_row["assigned_to"],
                            "priority": case_row["priority"],
                            "status": case_row["status"]
                        }
                    )

            # Audit log transaction creation
            try:
                from services.audit_log_service import AuditLogService
                AuditLogService().log_audit(
                    user_action="CREATE_TRANSACTION",
                    affected_table="transactions",
                    record_id=evaluated_tx.transaction_id,
                    old_values=None,
                    new_values=evaluated_tx.to_dict(),
                    performed_by="SYSTEM"
                )
            except Exception as audit_err:
                self.logger.error(f"Failed to log transaction creation audit: {audit_err}")

            return evaluated_tx

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to process and save transaction: {e}", exc_info=True)
            EventManager().log_event(
                event_type="TRANSACTION_FAILED",
                entity_type="TRANSACTION",
                entity_id=getattr(transaction, 'transaction_id', None),
                details={
                    "customer_id": transaction.customer_id,
                    "amount": str(transaction.amount),
                    "error": str(e)
                }
            )
            if isinstance(e, (InvalidTransactionException, CustomerNotFoundException, TransactionNotFoundException)):
                raise e
            raise TransactionException(f"Failed to process transaction: {e}")

    def get_transaction(self, transaction_id: int) -> Transaction:
        """
        Retrieves a transaction by ID.
        
        Raises:
            TransactionNotFoundException: If the transaction does not exist.
        """
        tx = self.tx_repo.find_by_id(transaction_id)
        if not tx:
            raise TransactionNotFoundException(f"Transaction with ID {transaction_id} not found.")

        # Re-attach dynamic details for transparency if available
        self._populate_dynamic_properties(tx)
        return tx

    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """
        Retrieves the most recent transactions sorted by time descending.
        """
        if limit <= 0:
            return []
            
        query = "SELECT * FROM transactions ORDER BY transaction_time DESC LIMIT %s"
        rows = self.db.fetch_all(query, (limit,))
        
        transactions = []
        for r in rows:
            tx = Transaction.from_dict(r)
            self._populate_dynamic_properties(tx)
            transactions.append(tx)
        return transactions

    def get_customer_transactions(self, customer_id: int) -> List[Transaction]:
        """
        Retrieves all transactions associated with a customer.
        """
        rows = self.tx_repo.search({"customer_id": customer_id})
        for tx in rows:
            self._populate_dynamic_properties(tx)
        return rows

    def check_transaction_status(self, transaction_id: int) -> str:
        """
        Retrieves and returns the status of a specific transaction.
        
        Raises:
            TransactionNotFoundException: If the transaction does not exist.
        """
        tx = self.tx_repo.find_by_id(transaction_id)
        if not tx:
            raise TransactionNotFoundException(f"Transaction with ID {transaction_id} not found.")
        return tx.status

    def _populate_dynamic_properties(self, tx: Transaction) -> None:
        """
        Helper method to populate city name and merchant category code dynamically.
        """
        tx.city = None
        tx.merchant_category = None
        
        # 1. Map city from coordinates if possible
        if tx.location_latitude is not None and tx.location_longitude is not None:
            for city_name, coords in self.CITY_COORDINATES.items():
                if abs(tx.location_latitude - coords[0]) < Decimal("0.0001") and \
                   abs(tx.location_longitude - coords[1]) < Decimal("0.0001"):
                    tx.city = city_name.title()
                    break

        # 2. Retrieve merchant category
        if tx.merchant_id is not None:
            merchant = self.merchant_repo.find_by_id(tx.merchant_id)
            if merchant:
                tx.merchant_category = merchant.merchant_category_code
                # Check mapping for text name
                for cat_name, info in self.CATEGORY_MCC_MAP.items():
                    if info[0] == merchant.merchant_category_code:
                        tx.merchant_category = cat_name.title()
                        break
