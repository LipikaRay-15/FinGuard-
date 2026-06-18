import logging
from typing import Any, Dict

from database import DatabaseConnection
from exceptions import DatabaseException
from engines.analytics_engine import AnalyticsEngine
from services.merchant_profile_service import MerchantProfileService

logger = logging.getLogger("finguard.services.analytics_service")

class AnalyticsService:
    """
    Service layer responsible for pulling raw logs and executing analytics metrics compilations.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.engine = AnalyticsEngine()
        self.merchant_service = MerchantProfileService()

    def get_system_analytics(self) -> Dict[str, Any]:
        """
        Retrieves raw transactional, alerts, and cases logs, compiles metrics,
        and returns a structured dashboard dictionary.
        """
        logger.info("Extracting raw database registers for system metrics compilation")
        try:
            # 1. Transactions
            tx_query = "SELECT amount, status, location_latitude, location_longitude, transaction_time FROM transactions"
            transactions = self.db.fetch_all(tx_query)

            # 2. Alerts
            alert_query = "SELECT status, severity, risk_score FROM alerts"
            alerts = self.db.fetch_all(alert_query)

            # 3. Cases
            case_query = "SELECT created_at, updated_at, status FROM cases"
            cases = self.db.fetch_all(case_query)

            # 4. Rules Logs
            rule_query = "SELECT rule_name, triggered FROM rule_execution_logs WHERE triggered = TRUE"
            rules_logs = self.db.fetch_all(rule_query)

            # 5. Customer Risk Profiles
            profile_query = """
                SELECT rp.customer_id, rp.current_risk_score, rp.risk_tier, 
                       CONCAT(c.first_name, ' ', c.last_name) AS customer_name 
                FROM risk_profiles rp 
                JOIN customers c ON rp.customer_id = c.customer_id
            """
            risk_profiles = self.db.fetch_all(profile_query)

            # 6. Merchant Analytics
            merchant_analytics = self.merchant_service.get_merchant_analytics()

            raw_data = {
                "transactions": transactions,
                "alerts": alerts,
                "cases": cases,
                "rules_logs": rules_logs,
                "risk_profiles": risk_profiles,
                "merchant_analytics": merchant_analytics
            }

            return self.engine.compile_analytics(raw_data)

        except Exception as e:
            logger.error(f"Failed to compile system diagnostics: {e}", exc_info=True)
            raise DatabaseException(f"Failed to compile system diagnostics: {e}")
