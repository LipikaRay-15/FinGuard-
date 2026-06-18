import logging
from typing import List, Optional

from database import DatabaseConnection
from models import RiskProfile, RiskHistory
from repositories import RiskProfileRepository, RiskHistoryRepository
from exceptions import DatabaseException

logger = logging.getLogger("finguard.services.risk_profile_service")

class RiskProfileService:
    """
    Service layer responsible for managing customer risk profiles and risk score histories.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.profile_repo = RiskProfileRepository()
        self.history_repo = RiskHistoryRepository()

    def get_risk_profile(self, customer_id: int) -> Optional[RiskProfile]:
        """
        Retrieves the current risk profile for a given customer.
        """
        logger.debug(f"Fetching risk profile for customer {customer_id}")
        try:
            profiles = self.profile_repo.search({"customer_id": customer_id})
            return profiles[0] if profiles else None
        except Exception as e:
            logger.error(f"Failed to fetch risk profile for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch risk profile: {e}")

    def get_risk_history(self, customer_id: int) -> List[RiskHistory]:
        """
        Retrieves the chronological list of risk changes for a customer.
        """
        logger.debug(f"Fetching risk history for customer {customer_id}")
        try:
            history = self.history_repo.search({"customer_id": customer_id})
            # Sort by recorded_at ascending
            history.sort(key=lambda x: x.recorded_at)
            return history
        except Exception as e:
            logger.error(f"Failed to fetch risk history for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch risk history: {e}")
