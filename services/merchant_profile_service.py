import logging
from typing import List

from database import DatabaseConnection
from exceptions import DatabaseException
from repositories import MerchantRepository

logger = logging.getLogger("finguard.services.merchant_profile_service")

class MerchantProfileService:
    """
    Service layer responsible for extracting and aggregating merchant category analytics.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.merchant_repo = MerchantRepository()

    def get_merchant_analytics(self) -> List[dict]:
        """
        Retrieves aggregated analytics grouped by merchant category code.
        Returns:
            List of dicts: [
                {
                    "merchant_category": str,
                    "fraud_count": int,
                    "average_score": float,
                    "risk_level": str
                }
            ]
        """
        logger.debug("Fetching merchant category analytics aggregates")
        try:
            query = """
                SELECT 
                    m.merchant_category_code AS merchant_category,
                    COUNT(CASE WHEN t.status = 'DECLINED' THEN 1 END) AS fraud_count,
                    COALESCE(AVG(a.risk_score), 0.0) AS average_score,
                    m.risk_level
                FROM merchant_profiles m
                LEFT JOIN transactions t ON m.merchant_id = t.merchant_id
                LEFT JOIN alerts a ON t.transaction_id = a.transaction_id
                GROUP BY m.merchant_category_code, m.risk_level
                ORDER BY fraud_count DESC, average_score DESC
            """
            rows = self.db.fetch_all(query)
            # Map average_score to float and round to 2 decimal places
            results = []
            for r in rows:
                results.append({
                    "merchant_category": r["merchant_category"],
                    "fraud_count": int(r["fraud_count"] or 0),
                    "average_score": round(float(r["average_score"] or 0.0), 2),
                    "risk_level": r["risk_level"]
                })
            return results
        except Exception as e:
            logger.error(f"Failed to fetch merchant analytics: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch merchant analytics: {e}")
