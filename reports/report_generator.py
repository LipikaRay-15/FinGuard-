import csv
import io
import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from decimal import Decimal

from database import DatabaseConnection
from exceptions import DatabaseException
from services.analytics_service import AnalyticsService

logger = logging.getLogger("finguard.reports.report_generator")

class ReportGenerator:
    """
    Reporting component responsible for compiling Daily/Weekly/Monthly metrics,
    case/alert statistics, high-risk customer ranks, and CSV data exports.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.analytics_service = AnalyticsService()

    def _get_time_boundary_stats(self, days: int) -> dict:
        """
        Helper method to aggregate transactions, fraud counts, alert counts, and averages for a given window of days.
        """
        try:
            query = """
                SELECT 
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN status = 'DECLINED' THEN 1 ELSE 0 END) AS fraud_count,
                    COALESCE(SUM(amount), 0.00) AS total_amount,
                    COALESCE(AVG(amount), 0.00) AS average_amount
                FROM transactions
                WHERE transaction_time >= NOW() - INTERVAL %s DAY
            """
            row = self.db.fetch_one(query, (days,))
            total_count = int(row["total_count"] or 0)
            fraud_count = int(row["fraud_count"] or 0)
            total_amount = float(row["total_amount"] or 0.0)
            average_amount = float(row["average_amount"] or 0.0)

            # Calculate fraud rate percentage
            fraud_rate = round((fraud_count / total_count) * 100, 2) if total_count > 0 else 0.0

            # Alert counts
            alert_row = self.db.fetch_one(
                "SELECT COUNT(*) AS alert_count FROM alerts WHERE created_at >= NOW() - INTERVAL %s DAY", 
                (days,)
            )
            alert_count = int(alert_row["alert_count"] or 0)

            return {
                "window_days": days,
                "total_transactions": total_count,
                "fraud_count": fraud_count,
                "fraud_rate_percentage": fraud_rate,
                "total_transaction_amount": round(total_amount, 2),
                "average_transaction_amount": round(average_amount, 2),
                "alerts_generated": alert_count
            }
        except Exception as e:
            logger.error(f"Failed to fetch time boundary statistics for window of {days} days: {e}", exc_info=True)
            raise DatabaseException(f"Failed to compute window aggregates: {e}")

    def generate_daily_report(self) -> dict:
        """
        Generates structured daily transactional report.
        """
        logger.info("Generating Daily Operations Report")
        return self._get_time_boundary_stats(1)

    def generate_weekly_report(self) -> dict:
        """
        Generates structured weekly operations report.
        """
        logger.info("Generating Weekly Operations Report")
        return self._get_time_boundary_stats(7)

    def generate_monthly_report(self) -> dict:
        """
        Generates structured monthly operations report.
        """
        logger.info("Generating Monthly Operations Report")
        return self._get_time_boundary_stats(30)

    def generate_high_risk_customer_report(self) -> List[dict]:
        """
        Generates a summary list of high-risk customers, sorted by risk score descending.
        """
        logger.info("Generating High Risk Customers Report")
        try:
            query = """
                SELECT rp.customer_id, 
                       CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                       c.email,
                       rp.current_risk_score, 
                       rp.risk_tier 
                FROM risk_profiles rp 
                JOIN customers c ON rp.customer_id = c.customer_id
                WHERE rp.current_risk_score >= 61
                ORDER BY rp.current_risk_score DESC
            """
            rows = self.db.fetch_all(query)
            results = []
            for r in rows:
                results.append({
                    "customer_id": r["customer_id"],
                    "customer_name": r["customer_name"],
                    "email": r["email"],
                    "risk_score": r["current_risk_score"],
                    "risk_tier": r["risk_tier"]
                })
            return results
        except Exception as e:
            logger.error(f"Failed to generate high risk customer report: {e}", exc_info=True)
            raise DatabaseException(f"Failed to query high risk customers: {e}")

    def generate_fraud_summary_report(self) -> dict:
        """
        Generates the consolidated Fraud Summary Report.
        """
        logger.info("Generating Fraud Summary Report")
        try:
            # Aggregate total count and total amount of fraud (status = 'DECLINED')
            query = """
                SELECT 
                    COUNT(*) AS fraud_count,
                    COALESCE(SUM(amount), 0.00) AS fraud_amount
                FROM transactions
                WHERE status = 'DECLINED'
            """
            row = self.db.fetch_one(query)
            fraud_count = int(row["fraud_count"] or 0)
            fraud_amount = float(row["fraud_amount"] or 0.0)

            # Top merchant categories by fraud counts
            mcc_query = """
                SELECT 
                    m.merchant_category_code AS merchant_category,
                    COUNT(*) AS fraud_count
                FROM transactions t
                JOIN merchant_profiles m ON t.merchant_id = m.merchant_id
                WHERE t.status = 'DECLINED'
                GROUP BY m.merchant_category_code
                ORDER BY fraud_count DESC
                LIMIT 5
            """
            mcc_rows = self.db.fetch_all(mcc_query)
            top_categories = [{"merchant_category": r["merchant_category"], "fraud_count": int(r["fraud_count"] or 0)} for r in mcc_rows]

            # Top cities by fraud counts (utilizing analytics coordinates translation)
            summary = self.analytics_service.get_system_analytics()
            top_cities = summary.get("top_risky_cities", [])

            return {
                "total_fraud_transactions": fraud_count,
                "total_fraud_amount": round(fraud_amount, 2),
                "top_merchant_categories": top_categories,
                "top_risky_cities": top_cities
            }
        except Exception as e:
            logger.error(f"Failed to generate fraud summary report: {e}", exc_info=True)
            raise DatabaseException(f"Failed to compile fraud report: {e}")

    def generate_case_statistics_report(self) -> dict:
        """
        Generates cases queues diagnostic report.
        """
        logger.info("Generating Case Statistics Report")
        try:
            summary = self.analytics_service.get_system_analytics()
            case_res_time = summary.get("case_resolution_time", 0.0)

            # Query detailed distributions
            status_rows = self.db.fetch_all("SELECT status, COUNT(*) AS count FROM cases GROUP BY status")
            status_dist = {str(r["status"]).upper(): int(r["count"]) for r in status_rows}

            priority_rows = self.db.fetch_all("SELECT priority, COUNT(*) AS count FROM cases GROUP BY priority")
            priority_dist = {str(r["priority"]).upper(): int(r["count"]) for r in priority_rows}

            total_row = self.db.fetch_one("SELECT COUNT(*) AS total FROM cases")
            total_cases = int(total_row["total"] or 0)

            return {
                "total_cases": total_cases,
                "status_distribution": status_dist,
                "priority_distribution": priority_dist,
                "average_resolution_time_seconds": case_res_time
            }
        except Exception as e:
            logger.error(f"Failed to generate case statistics report: {e}", exc_info=True)
            raise DatabaseException(f"Failed to compile case stats: {e}")

    def generate_alert_statistics_report(self) -> dict:
        """
        Generates alerts status diagnostic report.
        """
        logger.info("Generating Alert Statistics Report")
        try:
            summary = self.analytics_service.get_system_analytics()
            alert_dist = summary.get("alert_distribution", {"status_distribution": {}, "severity_distribution": {}})

            total_row = self.db.fetch_one("SELECT COUNT(*) AS total, COALESCE(AVG(risk_score), 0.0) AS avg_score FROM alerts")
            total_alerts = int(total_row["total"] or 0)
            avg_score = float(total_row["avg_score"] or 0.0)

            return {
                "total_alerts": total_alerts,
                "average_risk_score": round(avg_score, 2),
                "status_distribution": alert_dist.get("status_distribution", {}),
                "severity_distribution": alert_dist.get("severity_distribution", {})
            }
        except Exception as e:
            logger.error(f"Failed to generate alert statistics report: {e}", exc_info=True)
            raise DatabaseException(f"Failed to compile alert stats: {e}")

    def generate_csv_export(self, entity_type: str) -> str:
        """
        Renders system logs (TRANSACTIONS, ALERTS, or CASES) in comma-separated CSV string format.
        """
        logger.info(f"Generating CSV export for entity type: {entity_type}")
        entity_upper = entity_type.strip().upper()
        
        try:
            output = io.StringIO()
            writer = csv.writer(output)

            if entity_upper == "TRANSACTIONS":
                query = "SELECT * FROM transactions ORDER BY transaction_time DESC"
                rows = self.db.fetch_all(query)
                writer.writerow(["transaction_id", "customer_id", "merchant_id", "device_id", "amount", "currency", "transaction_type", "status", "location_latitude", "location_longitude", "transaction_time"])
                for r in rows:
                    writer.writerow([
                        r["transaction_id"], r["customer_id"], r["merchant_id"], r["device_id"],
                        float(r["amount"]), r["currency"], r["transaction_type"], r["status"],
                        float(r["location_latitude"]) if r["location_latitude"] is not None else None,
                        float(r["location_longitude"]) if r["location_longitude"] is not None else None,
                        r["transaction_time"]
                    ])

            elif entity_upper == "ALERTS":
                query = "SELECT * FROM alerts ORDER BY created_at DESC"
                rows = self.db.fetch_all(query)
                writer.writerow(["alert_id", "transaction_id", "customer_id", "risk_score", "severity", "status", "created_at"])
                for r in rows:
                    writer.writerow([
                        r["alert_id"], r["transaction_id"], r["customer_id"], r["risk_score"],
                        r["severity"], r["status"], r["created_at"]
                    ])

            elif entity_upper == "CASES":
                query = "SELECT * FROM cases ORDER BY created_at DESC"
                rows = self.db.fetch_all(query)
                writer.writerow(["case_id", "alert_id", "assigned_to", "status", "priority", "notes", "remarks", "analyst_notes", "resolution", "created_at", "updated_at"])
                for r in rows:
                    writer.writerow([
                        r["case_id"], r["alert_id"], r["assigned_to"], r["status"], r["priority"],
                        r["notes"], r["remarks"], r["analyst_notes"], r["resolution"],
                        r["created_at"], r["updated_at"]
                    ])
            else:
                raise ValueError(f"Invalid entity type for CSV export: '{entity_type}'. Expected TRANSACTIONS, ALERTS, or CASES.")

            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to generate CSV export for {entity_type}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to generate CSV export: {e}")
