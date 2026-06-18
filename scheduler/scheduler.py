import os
import time
import json
import logging
import threading
from datetime import datetime
from decimal import Decimal
from typing import Optional

import schedule

from database import DatabaseConnection
from reports.report_generator import ReportGenerator
from services.analytics_service import AnalyticsService

logger = logging.getLogger("finguard.scheduler")

class Scheduler:
    """
    Task Scheduler executing background cron tasks for reports compilation,
    logs cleanups, and transaction record archiving.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.report_gen = ReportGenerator()
        self.analytics_service = AnalyticsService()
        self.running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        Starts the background thread managing execution loops.
        """
        if self.running:
            logger.warning("Scheduler background thread is already running.")
            return

        self.running = True
        self._stop_event.clear()

        # Clear any prior schedules
        schedule.clear()
        
        # Schedule cron jobs
        schedule.every().day.at("00:00").do(self.run_daily_reports)
        schedule.every().day.at("01:00").do(self.run_monthly_analytics_check)
        schedule.every().day.at("02:00").do(self.run_cleanup_logs)
        schedule.every().day.at("03:00").do(self.run_archive_old_records)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler task executor thread started.")

    def stop(self) -> None:
        """
        Stops the execution loop thread.
        """
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Scheduler task executor thread stopped.")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)

    def run_daily_reports(self) -> None:
        """
        Runs the daily report generator and writes the results to reports/ directory.
        """
        logger.info("Initiating scheduled task: Daily Reports Generation")
        try:
            report = self.report_gen.generate_daily_report()
            os.makedirs("reports", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join("reports", f"daily_report_{ts}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4)
            logger.info(f"Daily Report archived successfully: {filepath}")
        except Exception as e:
            logger.error(f"Scheduled Daily Report failed: {e}", exc_info=True)

    def run_monthly_analytics_check(self) -> None:
        if datetime.now().day == 1:
            self.run_monthly_analytics()

    def run_monthly_analytics(self) -> None:
        """
        Compiles monthly system analytics and logs statistics to reports/ directory.
        """
        logger.info("Initiating scheduled task: Monthly Analytics Generation")
        try:
            analytics = self.analytics_service.get_system_analytics()
            os.makedirs("reports", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join("reports", f"monthly_analytics_{ts}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(analytics, f, indent=4)
            logger.info(f"Monthly Analytics archived successfully: {filepath}")
        except Exception as e:
            logger.error(f"Scheduled Monthly Analytics failed: {e}", exc_info=True)

    def run_cleanup_logs(self) -> None:
        """
        Cleans logs (audit, rule execution, events) older than 90 days.
        """
        logger.info("Initiating scheduled task: Logs Cleanups (90 Days retention policy)")
        try:
            c1 = self.db.execute("DELETE FROM audit_logs WHERE performed_at < NOW() - INTERVAL 90 DAY")
            c1.close()
            c2 = self.db.execute("DELETE FROM rule_execution_logs WHERE execution_time < NOW() - INTERVAL 90 DAY")
            c2.close()
            c3 = self.db.execute("DELETE FROM events WHERE created_at < NOW() - INTERVAL 90 DAY")
            c3.close()
            
            self.db.commit()
            logger.info("Scheduled Logs Cleanup completed successfully.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Scheduled Logs Cleanup task failed: {e}", exc_info=True)

    def run_archive_old_records(self) -> None:
        """
        Archives records older than 180 days into local JSON files and deletes them from live tables.
        """
        logger.info("Initiating scheduled task: Archive Old Records (180 Days policy)")
        try:
            archive_dir = os.path.join("reports", "archive")
            os.makedirs(archive_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. Cases
            cases = self.db.fetch_all("SELECT * FROM cases WHERE created_at < NOW() - INTERVAL 180 DAY")
            if cases:
                for c in cases:
                    for k, v in c.items():
                        if isinstance(v, datetime):
                            c[k] = v.isoformat()
                filepath = os.path.join(archive_dir, f"cases_archive_{ts}.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(cases, f, indent=4)
                logger.info(f"Archived {len(cases)} case registers.")

            # 2. Alerts
            alerts = self.db.fetch_all("SELECT * FROM alerts WHERE created_at < NOW() - INTERVAL 180 DAY")
            if alerts:
                for a in alerts:
                    for k, v in a.items():
                        if isinstance(v, datetime):
                            a[k] = v.isoformat()
                filepath = os.path.join(archive_dir, f"alerts_archive_{ts}.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(alerts, f, indent=4)
                logger.info(f"Archived {len(alerts)} alert registers.")

            # 3. Transactions
            txs = self.db.fetch_all("SELECT * FROM transactions WHERE transaction_time < NOW() - INTERVAL 180 DAY")
            if txs:
                for tx in txs:
                    for k, v in tx.items():
                        if isinstance(v, (datetime, Decimal)):
                            tx[k] = str(v)
                filepath = os.path.join(archive_dir, f"transactions_archive_{ts}.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(txs, f, indent=4)
                logger.info(f"Archived {len(txs)} transaction registers.")

            # Delete in constraint order (cases, then alerts, then transactions)
            dc = self.db.execute("DELETE FROM cases WHERE created_at < NOW() - INTERVAL 180 DAY")
            dc.close()
            da = self.db.execute("DELETE FROM alerts WHERE created_at < NOW() - INTERVAL 180 DAY")
            da.close()
            dt = self.db.execute("DELETE FROM transactions WHERE transaction_time < NOW() - INTERVAL 180 DAY")
            dt.close()

            self.db.commit()
            logger.info("Live data purge of archived records completed successfully.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Scheduled Records Archive task failed: {e}", exc_info=True)
