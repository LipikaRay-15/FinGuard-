import logging
from typing import Optional

from database import DatabaseConnection
from models import Alert
from services.alert_service import AlertService
from services.blacklist_service import BlacklistService
from services.whitelist_service import WhitelistService
from repositories import TransactionRepository
from exceptions import DatabaseException, ValidationException

logger = logging.getLogger("finguard.engines.alert_manager")

class AlertManager:
    """
    Manager engine responsible for coordinating whitelist and blacklist checks
    and enforcing transaction alert generation thresholds.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.tx_repo = TransactionRepository()
        self.alert_service = AlertService()
        self.blacklist_service = BlacklistService()
        self.whitelist_service = WhitelistService()

    def process_transaction_risk(
        self,
        transaction_id: int,
        risk_score: int,
        risk_level: str
    ) -> Optional[Alert]:
        """
        Processes transaction risk outcomes. Enforces blacklist priority,
        respects whitelist exemptions, and generates alerts for suspicious activity.
        
        Args:
            transaction_id: The evaluated transaction ID.
            risk_score: Calculated risk points.
            risk_level: Calculated risk level.
            
        Returns:
            The created Alert entity if generated, otherwise None.
        """
        logger.info(f"AlertManager processing risk for transaction {transaction_id} (Score: {risk_score}, Level: {risk_level})")
        
        try:
            # 1. Fetch transaction metadata
            tx = self.tx_repo.find_by_id(transaction_id)
            if not tx:
                logger.warning(f"Transaction {transaction_id} not found in AlertManager.")
                return None

            # Fetch customer details to check PAN / Account blocks
            customer_row = self.db.fetch_one(
                "SELECT pan, account_number FROM customers WHERE customer_id = %s",
                (tx.customer_id,)
            )
            pan = customer_row["pan"] if customer_row else None
            account_number = customer_row["account_number"] if customer_row else None

            # 2. Check Blacklist (Highest Priority)
            is_blacklisted, bl_reason = self.blacklist_service.check_blacklist(
                customer_id=tx.customer_id,
                device_id=tx.device_id,
                pan=pan,
                account_number=account_number
            )
            if is_blacklisted:
                logger.info(f"Bypassing normal alert criteria: Transaction {transaction_id} matches blacklist. Reason: {bl_reason}")
                # Blacklist triggers an automatic CRITICAL severity alert
                return self.alert_service.generate_alert(
                    transaction_id=transaction_id,
                    customer_id=tx.customer_id,
                    risk_score=100,
                    severity="CRITICAL",
                    status="OPEN"
                )

            # 3. Check Whitelist (Bypasses Alert Generation)
            is_whitelisted, wl_reason = self.whitelist_service.check_whitelist(
                customer_id=tx.customer_id,
                device_id=tx.device_id
            )
            if is_whitelisted:
                logger.info(f"Bypassing alert generation: Customer/Device is whitelisted. Reason: {wl_reason}")
                return None

            # 4. Enforce suspicious alert threshold (Risk Score >= 50 or Level is Medium/High/Critical)
            level_upper = risk_level.upper().strip()
            if risk_score >= 50 or level_upper in ("MEDIUM", "HIGH", "CRITICAL"):
                # Map risk level to alert severity
                severity = "MEDIUM"
                if level_upper in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                    severity = level_upper
                
                return self.alert_service.generate_alert(
                    transaction_id=transaction_id,
                    customer_id=tx.customer_id,
                    risk_score=risk_score,
                    severity=severity,
                    status="OPEN"
                )

            return None
        except Exception as e:
            logger.error(f"Error processing alert checks for transaction {transaction_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Error processing alert rules: {e}")
