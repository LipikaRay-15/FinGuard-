import logging
from collections import Counter, defaultdict
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Union, Optional

logger = logging.getLogger("finguard.engines.analytics_engine")

CITY_COORDINATES = {
    "NEW YORK": (40.7128, -74.0060),
    "LONDON": (51.5074, -0.1278),
    "LAS VEGAS": (36.1716, -115.1398),
    "PARIS": (48.8566, 2.3522),
    "TOKYO": (35.6762, 139.6503),
    "MUMBAI": (19.0760, 72.8777),
}

class AnalyticsEngine:
    """
    Pure logical engine that performs analytical computations and formatting for FinGuard dashboards.
    """
    def _resolve_city(self, lat: Optional[Union[float, Decimal]], lon: Optional[Union[float, Decimal]]) -> str:
        """
        Translates coordinate values back to registered city names.
        """
        if lat is None or lon is None:
            return "Unknown"
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            for city, coords in CITY_COORDINATES.items():
                if abs(lat_f - coords[0]) < 0.01 and abs(lon_f - coords[1]) < 0.01:
                    return city
        except (ValueError, TypeError):
            pass
        return "Unknown"

    def calculate_fraud_percentage(self, total_count: int, fraud_count: int) -> float:
        """
        Calculates ratio of fraudulent transactions compared to total volume.
        """
        if total_count <= 0:
            return 0.0
        return round((fraud_count / total_count) * 100, 2)

    def calculate_false_positive_ratio(self, total_alerts: int, fp_count: int) -> float:
        """
        Calculates ratio of false positive alerts.
        """
        if total_alerts <= 0:
            return 0.0
        return round((fp_count / total_alerts) * 100, 2)

    def calculate_average_amount(self, amounts: List[float]) -> float:
        """
        Calculates arithmetic mean of transaction amounts.
        """
        if not amounts:
            return 0.0
        return round(sum(amounts) / len(amounts), 2)

    def calculate_case_resolution_time(self, cases: List[Dict[str, Any]]) -> float:
        """
        Computes the average resolution duration of cases in seconds.
        Expects keys: 'created_at', 'updated_at', 'status' (RESOLVED or CLOSED).
        """
        resolved_durations = []
        for c in cases:
            status = str(c.get("status", "")).upper()
            if status in ("RESOLVED", "CLOSED"):
                created = c.get("created_at")
                updated = c.get("updated_at")
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except ValueError:
                        created = None
                if isinstance(updated, str):
                    try:
                        updated = datetime.fromisoformat(updated)
                    except ValueError:
                        updated = None
                
                if isinstance(created, datetime) and isinstance(updated, datetime):
                    duration = (updated - created).total_seconds()
                    if duration >= 0:
                        resolved_durations.append(duration)

        if not resolved_durations:
            return 0.0
        return round(sum(resolved_durations) / len(resolved_durations), 2)

    def group_by_city(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups transactions by resolved city name and ranks cities by fraud counts.
        """
        city_stats = defaultdict(lambda: {"total": 0, "fraud": 0})
        for tx in transactions:
            lat = tx.get("location_latitude")
            lon = tx.get("location_longitude")
            city = self._resolve_city(lat, lon)
            
            city_stats[city]["total"] += 1
            if str(tx.get("status", "")).upper() == "DECLINED":
                city_stats[city]["fraud"] += 1

        results = []
        for city, stats in city_stats.items():
            results.append({
                "city": city,
                "total_count": stats["total"],
                "fraud_count": stats["fraud"]
            })
            
        # Rank by fraud count descending, then total count descending
        results.sort(key=lambda x: (x["fraud_count"], x["total_count"]), reverse=True)
        return results

    def aggregate_hourly_trends(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregates transaction frequencies hourly (0 to 23).
        """
        hourly_counts = Counter()
        for tx in transactions:
            tx_time = tx.get("transaction_time")
            if isinstance(tx_time, str):
                try:
                    tx_time = datetime.fromisoformat(tx_time)
                except ValueError:
                    tx_time = None
            
            if isinstance(tx_time, datetime):
                hourly_counts[tx_time.hour] += 1
            elif isinstance(tx_time, dict) and "hour" in tx_time:
                # support fallback if dict timestamp parsed
                hourly_counts[tx_time["hour"]] += 1

        results = []
        for hour in range(24):
            results.append({
                "hour": hour,
                "transaction_count": hourly_counts[hour]
            })
        return results

    def aggregate_daily_trends(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups transaction counts and fraud spikes day-by-day.
        """
        daily_stats = defaultdict(lambda: {"total": 0, "fraud": 0})
        for tx in transactions:
            tx_time = tx.get("transaction_time")
            tx_date_str = None
            
            if isinstance(tx_time, datetime):
                tx_date_str = tx_time.date().isoformat()
            elif isinstance(tx_time, date):
                tx_date_str = tx_time.isoformat()
            elif isinstance(tx_time, str):
                try:
                    dt = datetime.fromisoformat(tx_time)
                    tx_date_str = dt.date().isoformat()
                except ValueError:
                    # try date format directly
                    tx_date_str = tx_time[:10]
            
            if not tx_date_str:
                continue
                
            daily_stats[tx_date_str]["total"] += 1
            if str(tx.get("status", "")).upper() == "DECLINED":
                daily_stats[tx_date_str]["fraud"] += 1

        results = []
        for date_str, stats in daily_stats.items():
            results.append({
                "date": date_str,
                "transaction_count": stats["total"],
                "fraud_count": stats["fraud"]
            })
            
        # Sort chronologically by date string
        results.sort(key=lambda x: x["date"])
        return results

    def compile_analytics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregates raw system lists and builds the final metrics summary block.
        """
        transactions = raw_data.get("transactions", [])
        alerts = raw_data.get("alerts", [])
        cases = raw_data.get("cases", [])
        rules_logs = raw_data.get("rules_logs", [])
        risk_profiles = raw_data.get("risk_profiles", [])
        merchant_analytics = raw_data.get("merchant_analytics", [])

        # 1. Total & Fraud counts
        total_tx = len(transactions)
        fraud_tx = sum(1 for tx in transactions if str(tx.get("status", "")).upper() == "DECLINED")
        fraud_percentage = self.calculate_fraud_percentage(total_tx, fraud_tx)

        # 2. Top Risky Customers
        # Rank customer profiles by risk score descending
        sorted_profiles = sorted(risk_profiles, key=lambda x: x.get("current_risk_score", 0), reverse=True)
        top_risky_customers = []
        for p in sorted_profiles[:5]: # top 5
            top_risky_customers.append({
                "customer_id": p.get("customer_id"),
                "customer_name": p.get("customer_name", f"Customer {p.get('customer_id')}"),
                "risk_score": p.get("current_risk_score", 0),
                "risk_tier": p.get("risk_tier", "LOW")
            })

        # 3. Top Risky Cities
        top_risky_cities = self.group_by_city(transactions)[:5] # top 5

        # 4. Top Risky Merchant Categories
        # Mapped from merchant_analytics list
        sorted_merchants = sorted(merchant_analytics, key=lambda x: (x.get("fraud_count", 0), x.get("average_score", 0.0)), reverse=True)
        top_risky_merchant_categories = []
        for m in sorted_merchants[:5]:
            top_risky_merchant_categories.append({
                "merchant_category": m.get("merchant_category"),
                "fraud_count": m.get("fraud_count", 0),
                "average_score": m.get("average_score", 0.0),
                "risk_level": m.get("risk_level", "LOW")
            })

        # 5. Average Transaction Amount
        amounts = [float(tx.get("amount") or 0.0) for tx in transactions]
        avg_amount = self.calculate_average_amount(amounts)

        # 6. False Positive Ratio
        total_alerts = len(alerts)
        fp_count = sum(1 for a in alerts if str(a.get("status", "")).upper() == "FALSE_POSITIVE")
        false_positive_ratio = self.calculate_false_positive_ratio(total_alerts, fp_count)

        # 7. Alert Distribution
        status_counts = Counter(str(a.get("status", "")).upper() for a in alerts)
        severity_counts = Counter(str(a.get("severity", "")).upper() for a in alerts)
        alert_distribution = {
            "status_distribution": dict(status_counts),
            "severity_distribution": dict(severity_counts)
        }

        # 8. Case Resolution Time
        case_res_time = self.calculate_case_resolution_time(cases)

        # 9. Most Triggered Rules
        triggered_rules_counts = Counter()
        for log in rules_logs:
            if log.get("triggered"):
                triggered_rules_counts[log.get("rule_name")] += 1
        most_triggered_rules = []
        for rule_name, count in triggered_rules_counts.most_common(5):
            most_triggered_rules.append({
                "rule_name": rule_name,
                "trigger_count": count
            })

        # 10. Daily and Hourly Trends
        daily_trends = self.aggregate_daily_trends(transactions)
        hourly_trends = self.aggregate_hourly_trends(transactions)

        return {
            "fraud_percentage": fraud_percentage,
            "top_risky_customers": top_risky_customers,
            "top_risky_cities": top_risky_cities,
            "top_risky_merchant_categories": top_risky_merchant_categories,
            "average_transaction_amount": avg_amount,
            "false_positive_ratio": false_positive_ratio,
            "alert_distribution": alert_distribution,
            "case_resolution_time": case_res_time,
            "most_triggered_rules": most_triggered_rules,
            "daily_trends": daily_trends,
            "hourly_trends": hourly_trends
        }
