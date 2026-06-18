import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from models import Customer, Device, Transaction, Alert, Case, RiskProfile, RiskHistory, Event
from repositories import (
    CustomerRepository,
    TransactionRepository,
    AlertRepository,
    CaseRepository,
    RiskHistoryRepository
)
from services.device_service import DeviceService
from services.risk_profile_service import RiskProfileService
from services.event_service import EventService
from engines.investigation_engine import InvestigationEngine
from exceptions import CustomerNotFoundException, DatabaseException

logger = logging.getLogger("finguard.services.investigation_service")

class InvestigationService:
    """
    Service layer coordinating data collection for customer fraud investigations.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.customer_repo = CustomerRepository()
        self.tx_repo = TransactionRepository()
        self.alert_repo = AlertRepository()
        self.case_repo = CaseRepository()
        self.device_service = DeviceService()
        self.risk_profile_service = RiskProfileService()
        self.event_service = EventService()
        self.engine = InvestigationEngine()

    def get_customer_profile(self, customer_id: int) -> dict:
        """
        Retrieves the profile of a customer.
        Raises:
            CustomerNotFoundException: If the customer does not exist.
        """
        logger.debug(f"Fetching customer profile for ID {customer_id}")
        customer = self.customer_repo.find_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundException(f"Customer with ID {customer_id} not found.")
        return customer.to_dict()

    def get_last_transactions(self, customer_id: int, limit: int = 10) -> List[Transaction]:
        """
        Retrieves the last N transactions for a customer, sorted descending.
        """
        logger.debug(f"Fetching last {limit} transactions for customer {customer_id}")
        try:
            query = "SELECT * FROM transactions WHERE customer_id = %s ORDER BY transaction_time DESC LIMIT %s"
            rows = self.db.fetch_all(query, (customer_id, limit))
            return [Transaction.from_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch last transactions for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch transactions: {e}")

    def get_alert_history(self, customer_id: int) -> List[Alert]:
        """
        Retrieves all alerts generated for a customer.
        """
        logger.debug(f"Fetching alert history for customer {customer_id}")
        try:
            return self.alert_repo.search({"customer_id": customer_id})
        except Exception as e:
            logger.error(f"Failed to fetch alert history for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch alert history: {e}")

    def get_case_history(self, customer_id: int) -> List[Case]:
        """
        Retrieves all cases linked to the customer's alerts.
        """
        logger.debug(f"Fetching case history for customer {customer_id}")
        try:
            query = """
                SELECT c.* FROM cases c
                JOIN alerts a ON c.alert_id = a.alert_id
                WHERE a.customer_id = %s
            """
            rows = self.db.fetch_all(query, (customer_id,))
            return [Case.from_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch case history for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch case history: {e}")

    def get_known_devices(self, customer_id: int) -> List[Device]:
        """
        Retrieves all devices registered or used by the customer.
        """
        logger.debug(f"Fetching known devices for customer {customer_id}")
        try:
            return self.device_service.get_customer_devices(customer_id)
        except Exception as e:
            logger.error(f"Failed to fetch known devices for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch devices: {e}")

    def get_rule_history(self, customer_id: int) -> List[Any]:
        """
        Retrieves all rule executions triggered for the customer's transactions.
        """
        logger.debug(f"Fetching rule execution history for customer {customer_id}")
        try:
            query = """
                SELECT r.* FROM rule_execution_logs r
                JOIN transactions t ON r.transaction_id = t.transaction_id
                WHERE t.customer_id = %s
            """
            rows = self.db.fetch_all(query, (customer_id,))
            from models.rule_execution_log import RuleExecutionLog
            return [RuleExecutionLog.from_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch rule history for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch rule history: {e}")

    def get_risk_history(self, customer_id: int) -> List[RiskHistory]:
        """
        Retrieves risk history logs for a customer.
        """
        logger.debug(f"Fetching risk history for customer {customer_id}")
        return self.risk_profile_service.get_risk_history(customer_id)

    def generate_timeline(self, customer_id: int) -> List[str]:
        """
        Fetches timeline events, sorts them chronologically, and returns formatted logs.
        """
        logger.debug(f"Generating timeline for customer {customer_id}")
        try:
            # Fetch events matching customer entity or transactions, alerts, cases, devices
            query = """
                SELECT * FROM events
                WHERE (entity_type = 'CUSTOMER' AND entity_id = %s)
                   OR (entity_type = 'TRANSACTION' AND entity_id IN (SELECT CAST(transaction_id AS CHAR) COLLATE utf8mb4_unicode_ci FROM transactions WHERE customer_id = %s))
                   OR (entity_type = 'ALERT' AND entity_id IN (SELECT CAST(alert_id AS CHAR) COLLATE utf8mb4_unicode_ci FROM alerts WHERE customer_id = %s))
                   OR (entity_type = 'CASE' AND entity_id IN (SELECT CAST(c.case_id AS CHAR) COLLATE utf8mb4_unicode_ci FROM cases c JOIN alerts a ON c.alert_id = a.alert_id WHERE a.customer_id = %s))
                   OR (entity_type = 'DEVICE' AND entity_id IN (SELECT CAST(device_id AS CHAR) COLLATE utf8mb4_unicode_ci FROM transactions WHERE customer_id = %s AND device_id IS NOT NULL))
            """
            rows = self.db.fetch_all(query, (customer_id, customer_id, customer_id, customer_id, customer_id))
            events = [Event.from_dict(row) for row in rows]

            # Fetch rule triggered events and filter by customer transactions in python
            rule_rows = self.db.fetch_all("SELECT * FROM events WHERE entity_type = 'RULE' AND event_type = 'RULE_TRIGGERED'")
            tx_rows = self.db.fetch_all("SELECT transaction_id FROM transactions WHERE customer_id = %s", (customer_id,))
            tx_ids = {int(r["transaction_id"]) for r in tx_rows}

            for row in rule_rows:
                ev = Event.from_dict(row)
                tx_id_val = ev.details.get("transaction_id")
                if tx_id_val is not None:
                    try:
                        if int(tx_id_val) in tx_ids:
                            events.append(ev)
                    except (ValueError, TypeError):
                        pass

            # Deduplicate by event_id
            seen_event_ids = set()
            unique_events = []
            for ev in events:
                if ev.event_id not in seen_event_ids:
                    seen_event_ids.add(ev.event_id)
                    unique_events.append(ev)

            # Sort chronologically ascending
            unique_events.sort(key=lambda x: x.created_at)

            # Format timeline strings
            timeline_strings = []
            for ev in unique_events:
                formatted = self.engine.format_timeline_event(ev.event_type, ev.entity_id, ev.details, ev.created_at)
                timeline_strings.append(formatted)

            return timeline_strings

        except Exception as e:
            logger.error(f"Failed to generate timeline for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to generate timeline: {e}")

    def investigate_customer(self, customer_id: int) -> dict:
        """
        Assembles all investigative profiles, scores, timeline events, and behavioral diagnostics.
        Also dispatches an INVESTIGATION_STARTED event.
        """
        logger.info(f"Starting investigation for customer {customer_id}")
        
        # 1. Fetch profiles and verify existence
        profile_dict = self.get_customer_profile(customer_id)
        
        risk_profile = self.risk_profile_service.get_risk_profile(customer_id)
        risk_score = risk_profile.current_risk_score if risk_profile else 0
        risk_tier = risk_profile.risk_tier if risk_profile else "LOW"
        
        # 2. Retrieve history and metrics
        risk_history = self.get_risk_history(customer_id)
        devices = self.get_known_devices(customer_id)
        all_txs = self.get_last_transactions(customer_id, limit=1000)
        
        # 3. Compute metrics using InvestigationEngine
        trust_score = self.engine.calculate_trust_score(risk_score)
        fraud_attempts = self.engine.count_fraud_attempts(all_txs)
        most_frequent_city = self.engine.find_most_frequent_city(all_txs)
        average_amount = self.engine.calculate_average_amount(all_txs)
        
        behaviour_summary = self.engine.generate_behaviour_summary(
            risk_level=risk_tier,
            avg_amount=average_amount,
            city=most_frequent_city,
            fraud_attempts=fraud_attempts
        )
        
        timeline = self.generate_timeline(customer_id)
        
        # 4. Dispatch Event
        try:
            self.event_service.create_event(
                event_type="INVESTIGATION_STARTED",
                entity_type="CUSTOMER",
                entity_id=str(customer_id),
                details={"investigated_at": datetime.now().isoformat()}
            )
        except Exception as event_err:
            logger.error(f"Failed to dispatch INVESTIGATION_STARTED event: {event_err}")

        # Log Audit Activity
        try:
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="INVESTIGATE_CUSTOMER",
                affected_table="customers",
                record_id=customer_id,
                old_values=None,
                new_values={
                    "trust_score": trust_score,
                    "risk_tier": risk_tier,
                    "fraud_attempts": fraud_attempts,
                    "most_frequent_city": most_frequent_city
                },
                performed_by="SYSTEM"
            )
        except Exception as audit_err:
            logger.error(f"Failed to log audit activity for investigation: {audit_err}")

        return {
            "customer_profile": profile_dict,
            "risk_profile": risk_profile.to_dict() if risk_profile else None,
            "trust_score": trust_score,
            "risk_history": [rh.to_dict() for rh in risk_history],
            "devices_used": [dev.to_dict() for dev in devices],
            "fraud_attempts": fraud_attempts,
            "most_frequent_city": most_frequent_city,
            "average_amount": average_amount,
            "behaviour_summary": behaviour_summary,
            "timeline": timeline
        }
