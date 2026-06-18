import logging
from typing import Optional, Tuple

from database import DatabaseConnection
from services.event_service import EventService
from exceptions import DatabaseException

logger = logging.getLogger("finguard.services.blacklist_service")

class BlacklistService:
    """
    Service layer handling blacklist management for customers, devices, PANs, and bank accounts.
    Dispatches audit events for every blocklist update.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.event_service = EventService()

    def blacklist_customer(self, customer_id: int, reason: str) -> None:
        """
        Blacklists a customer in the database and updates their customer profile status to BLOCKED.
        """
        logger.info(f"Blacklisting customer {customer_id}: {reason}")
        try:
            # 1. Insert/Update blacklisted_customers
            query = """
                INSERT INTO blacklisted_customers (customer_id, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (customer_id, reason, reason)).close()

            # 2. Update customer status to BLOCKED
            self.db.execute("UPDATE customers SET status = 'BLOCKED' WHERE customer_id = %s", (customer_id,)).close()
            self.db.commit()

            # 3. Create Event
            self.event_service.create_event(
                event_type="CUSTOMER_BLACKLISTED",
                entity_type="CUSTOMER",
                entity_id=str(customer_id),
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to blacklist customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to blacklist customer: {e}")

    def blacklist_device(self, device_id: int, reason: str) -> None:
        """
        Blacklists a device fingerprint in the database.
        """
        logger.info(f"Blacklisting device {device_id}: {reason}")
        try:
            query = """
                INSERT INTO blacklisted_devices (device_id, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (device_id, reason, reason)).close()
            self.db.commit()

            self.event_service.create_event(
                event_type="DEVICE_BLACKLISTED",
                entity_type="DEVICE",
                entity_id=str(device_id),
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to blacklist device {device_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to blacklist device: {e}")

    def block_pan(self, pan: str, reason: str) -> None:
        """
        Adds a card PAN to the blocked list.
        """
        logger.info(f"Blocking card PAN (suffix: {pan[-4:] if len(pan) >= 4 else pan}): {reason}")
        try:
            query = """
                INSERT INTO blocked_pans (pan, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (pan, reason, reason)).close()
            self.db.commit()

            self.event_service.create_event(
                event_type="PAN_BLOCKED",
                entity_type="PAN",
                entity_id=pan,
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to block PAN: {e}", exc_info=True)
            raise DatabaseException(f"Failed to block PAN: {e}")

    def block_account(self, account_number: str, reason: str) -> None:
        """
        Adds a bank account number to the blocked list.
        """
        logger.info(f"Blocking bank account {account_number}: {reason}")
        try:
            query = """
                INSERT INTO blocked_accounts (account_number, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (account_number, reason, reason)).close()
            self.db.commit()

            self.event_service.create_event(
                event_type="ACCOUNT_BLOCKED",
                entity_type="ACCOUNT",
                entity_id=account_number,
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to block account: {e}", exc_info=True)
            raise DatabaseException(f"Failed to block account: {e}")

    def check_blacklist(
        self,
        customer_id: Optional[int] = None,
        device_id: Optional[int] = None,
        pan: Optional[str] = None,
        account_number: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates input parameters against all blocklist criteria.
        Returns:
            (is_blacklisted, reason)
        """
        try:
            # 1. Check customer ID
            if customer_id is not None:
                row = self.db.fetch_one("SELECT reason FROM blacklisted_customers WHERE customer_id = %s", (customer_id,))
                if row:
                    return True, f"Customer {customer_id} is blacklisted: {row['reason']}"

            # 2. Check device ID
            if device_id is not None:
                row = self.db.fetch_one("SELECT reason FROM blacklisted_devices WHERE device_id = %s", (device_id,))
                if row:
                    return True, f"Device {device_id} is blacklisted: {row['reason']}"

            # 3. Check PAN
            if pan is not None:
                row = self.db.fetch_one("SELECT reason FROM blocked_pans WHERE pan = %s", (pan,))
                if row:
                    return True, f"Card PAN is blocked: {row['reason']}"

            # 4. Check account number
            if account_number is not None:
                row = self.db.fetch_one("SELECT reason FROM blocked_accounts WHERE account_number = %s", (account_number,))
                if row:
                    return True, f"Bank Account is blocked: {row['reason']}"

            return False, ""
        except Exception as e:
            logger.error(f"Error checking blacklist status: {e}", exc_info=True)
            raise DatabaseException(f"Error checking blacklist status: {e}")
