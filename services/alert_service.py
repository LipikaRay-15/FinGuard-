import logging
from typing import List, Optional
from datetime import datetime

from database import DatabaseConnection
from models import Alert
from repositories import AlertRepository
from services.event_service import EventService
from exceptions import DatabaseException, ValidationException

logger = logging.getLogger("finguard.services.alert_service")

class AlertService:
    """
    Service layer handling lifecycle of transaction security alerts.
    Dispatches audit events for alerts generation, updates, resolutions, and escalations.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.alert_repo = AlertRepository()
        self.event_service = EventService()

    def generate_alert(
        self,
        transaction_id: int,
        customer_id: int,
        risk_score: int,
        severity: str,
        status: str = "OPEN"
    ) -> Alert:
        """
        Creates, validates, and persists a new transaction alert in the database.
        """
        logger.info(f"Generating alert: transaction={transaction_id}, risk={risk_score}, severity={severity}")
        try:
            alert = Alert(
                alert_id=None,
                transaction_id=transaction_id,
                customer_id=customer_id,
                risk_score=risk_score,
                severity=severity,
                status=status,
                created_at=datetime.now()
            )
            saved = self.alert_repo.create(alert)
            self.db.commit()

            # Dispatch Event
            self.event_service.create_event(
                event_type="ALERT_GENERATED",
                entity_type="ALERT",
                entity_id=str(saved.alert_id),
                details={
                    "transaction_id": transaction_id,
                    "customer_id": customer_id,
                    "risk_score": risk_score,
                    "severity": saved.severity,
                    "status": saved.status
                }
            )
            return saved
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to generate alert for tx {transaction_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to generate alert: {e}")

    def update_alert_status(self, alert_id: int, status: str) -> None:
        """
        Updates the status of an existing alert.
        """
        logger.info(f"Updating alert status for Alert {alert_id} to {status}")
        try:
            alert = self.alert_repo.find_by_id(alert_id)
            if not alert:
                raise ValidationException(f"Alert with ID {alert_id} not found.")

            alert.status = status.upper()
            alert.validate()
            self.alert_repo.update(alert)
            self.db.commit()

            self.event_service.create_event(
                event_type="ALERT_UPDATED",
                entity_type="ALERT",
                entity_id=str(alert_id),
                details={"status": alert.status}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update alert status for Alert {alert_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to update alert status: {e}")

    def close_alert(self, alert_id: int, resolution: str) -> None:
        """
        Closes an alert with a matching resolution status.
        Supports status mappings: RESOLVED, FALSE_POSITIVE, or CLOSED.
        """
        logger.info(f"Closing alert {alert_id} with resolution: {resolution}")
        try:
            alert = self.alert_repo.find_by_id(alert_id)
            if not alert:
                raise ValidationException(f"Alert with ID {alert_id} not found.")

            res_upper = resolution.upper().strip()
            if "FALSE_POSITIVE" in res_upper or "FALSE POSITIVE" in res_upper:
                alert.status = "FALSE_POSITIVE"
            elif "RESOLVED" in res_upper or "TRUE_POSITIVE" in res_upper:
                alert.status = "RESOLVED"
            else:
                alert.status = "CLOSED"

            alert.validate()
            self.alert_repo.update(alert)
            self.db.commit()

            self.event_service.create_event(
                event_type="ALERT_CLOSED",
                entity_type="ALERT",
                entity_id=str(alert_id),
                details={"status": alert.status, "resolution": resolution}
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to close alert {alert_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to close alert: {e}")

    def escalate_alert(self, alert_id: int, notes: str) -> None:
        """
        Escalates an alert by bumping its severity tier and setting status to UNDER_REVIEW.
        """
        logger.info(f"Escalating alert {alert_id}: {notes}")
        try:
            alert = self.alert_repo.find_by_id(alert_id)
            if not alert:
                raise ValidationException(f"Alert with ID {alert_id} not found.")

            severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            curr_idx = severity_order.index(alert.severity)
            if curr_idx < len(severity_order) - 1:
                alert.severity = severity_order[curr_idx + 1]

            alert.status = "UNDER_REVIEW"
            alert.validate()
            self.alert_repo.update(alert)
            self.db.commit()

            self.event_service.create_event(
                event_type="ALERT_UPDATED",
                entity_type="ALERT",
                entity_id=str(alert_id),
                details={
                    "status": alert.status,
                    "severity": alert.severity,
                    "notes": notes
                }
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to escalate alert {alert_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to escalate alert: {e}")

    def get_open_alerts(self) -> List[Alert]:
        """
        Retrieves all currently active alerts (status OPEN or UNDER_REVIEW).
        """
        try:
            query = "SELECT * FROM alerts WHERE status IN ('OPEN', 'UNDER_REVIEW')"
            rows = self.db.fetch_all(query)
            return [Alert.from_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve open alerts: {e}", exc_info=True)
            raise DatabaseException(f"Failed to retrieve open alerts: {e}")

    def get_alert_history(self, customer_id: int) -> List[Alert]:
        """
        Retrieves the complete historical list of alerts triggered for a customer.
        """
        try:
            return self.alert_repo.search({"customer_id": customer_id})
        except Exception as e:
            logger.error(f"Failed to retrieve alert history for customer {customer_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to retrieve alert history: {e}")
