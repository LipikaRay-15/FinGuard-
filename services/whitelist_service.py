import logging
from typing import Optional, Tuple

from database import DatabaseConnection
from services.event_service import EventService
from exceptions import DatabaseException

logger = logging.getLogger("finguard.services.whitelist_service")

class WhitelistService:
    """
    Service layer handling whitelist management for customers and devices.
    Dispatches audit events for every whitelist update.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.event_service = EventService()

    def whitelist_customer(self, customer_id: int, reason: str) -> None:
        """
        Whitelists a customer in the database.
        """
        logger.info(f"Whitelisting customer {customer_id}: {reason}")
        try:
            query = """
                INSERT INTO whitelisted_customers (customer_id, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (customer_id, reason, reason)).close()
            self.db.commit()

            self.event_service.create_event(
                event_type="CUSTOMER_WHITELISTED",
                entity_type="CUSTOMER",
                entity_id=str(customer_id),
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to whitelist customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to whitelist customer: {e}")

    def whitelist_device(self, device_id: int, reason: str) -> None:
        """
        Whitelists a device in the database.
        """
        logger.info(f"Whitelisting device {device_id}: {reason}")
        try:
            query = """
                INSERT INTO whitelisted_devices (device_id, reason)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reason = %s
            """
            self.db.execute(query, (device_id, reason, reason)).close()
            self.db.commit()

            self.event_service.create_event(
                event_type="DEVICE_WHITELISTED",
                entity_type="DEVICE",
                entity_id=str(device_id),
                details={"reason": reason}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to whitelist device {device_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to whitelist device: {e}")

    def check_whitelist(
        self,
        customer_id: Optional[int] = None,
        device_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates input parameters against whitelist database tables.
        Returns:
            (is_whitelisted, reason)
        """
        try:
            # 1. Check customer ID
            if customer_id is not None:
                row = self.db.fetch_one("SELECT reason FROM whitelisted_customers WHERE customer_id = %s", (customer_id,))
                if row:
                    return True, f"Customer {customer_id} is whitelisted: {row['reason']}"

            # 2. Check device ID
            if device_id is not None:
                row = self.db.fetch_one("SELECT reason FROM whitelisted_devices WHERE device_id = %s", (device_id,))
                if row:
                    return True, f"Device {device_id} is whitelisted: {row['reason']}"

            return False, ""
        except Exception as e:
            logger.error(f"Error checking whitelist status: {e}", exc_info=True)
            raise DatabaseException(f"Error checking whitelist status: {e}")
