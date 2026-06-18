import logging
from typing import List, Optional

from database import DatabaseConnection
from exceptions import DatabaseException
from repositories import RiskHistoryRepository

logger = logging.getLogger("finguard.services.risk_history_service")

class RiskHistoryService:
    """
    Service layer responsible for managing and projecting risk change history audits.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.history_repo = RiskHistoryRepository()

    def _determine_risk_level(self, score: int) -> str:
        """
        Helper method to map a numeric score to its risk level category.
        """
        if score >= 100:
            return "CRITICAL"
        elif score >= 61:
            return "HIGH"
        elif score >= 31:
            return "MEDIUM"
        else:
            return "LOW"

    def get_risk_history(self, customer_id: Optional[int] = None) -> List[dict]:
        """
        Retrieves the list of risk histories, optionally filtered by customer_id.
        Returns:
            List of dicts: [
                {
                    "customer_id": int,
                    "score": int,
                    "risk_level": str,
                    "timestamp": datetime
                }
            ]
        """
        logger.debug(f"Fetching risk history details (customer_id filter: {customer_id})")
        try:
            if customer_id is not None:
                histories = self.history_repo.search({"customer_id": customer_id})
            else:
                histories = self.history_repo.find_all()
            
            # Sort chronologically by recorded_at descending (newest first for analytics)
            histories.sort(key=lambda x: x.recorded_at, reverse=True)

            results = []
            for h in histories:
                results.append({
                    "customer_id": h.customer_id,
                    "score": h.new_risk_score,
                    "risk_level": self._determine_risk_level(h.new_risk_score),
                    "timestamp": h.recorded_at
                })
            return results
        except Exception as e:
            logger.error(f"Failed to fetch risk history details: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch risk history details: {e}")
