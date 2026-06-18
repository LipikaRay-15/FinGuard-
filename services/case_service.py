import logging
from typing import List, Optional, Any
from datetime import datetime

from database import DatabaseConnection
from models import Case
from repositories import CaseRepository
from services.event_service import EventService
from engines.case_state_machine import CaseStateMachine
from exceptions import DatabaseException, ValidationException

logger = logging.getLogger("finguard.services.case_service")

class CaseService:
    """
    Service layer orchestrating the lifecycle, assignment, remarks,
    and state pattern workflow transitions of fraud investigation cases.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.case_repo = CaseRepository()
        self.event_service = EventService()

    def create_case(
        self,
        alert_id: int,
        priority: str = "MEDIUM",
        notes: Optional[str] = None
    ) -> Case:
        """
        Creates a new case linked to a transaction alert with initial status OPEN.
        """
        logger.info(f"Creating case for alert {alert_id} (Priority: {priority})")
        try:
            case = Case(
                case_id=None,
                alert_id=alert_id,
                assigned_to=None,
                status="OPEN",
                priority=priority,
                notes=notes,
                remarks=None,
                analyst_notes=None,
                resolution=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            saved = self.case_repo.create(case)
            self.db.commit()

            # Dispatch Event
            self.event_service.create_event(
                event_type="CASE_CREATED",
                entity_type="CASE",
                entity_id=str(saved.case_id),
                details={
                    "alert_id": alert_id,
                    "priority": saved.priority,
                    "status": saved.status,
                    "notes": notes
                }
            )
            return saved
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create case for alert {alert_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to create case: {e}")

    def assign_case(self, case_id: int, analyst: str) -> None:
        """
        Assigns the case to a specific analyst investigator.
        """
        logger.info(f"Assigning case {case_id} to analyst '{analyst}'")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            old_values = case.to_dict()
            case.assigned_to = analyst
            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            self.event_service.create_event(
                event_type="CASE_UPDATED",
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "ASSIGNED",
                    "assigned_to": analyst
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="ASSIGN_CASE",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign case {case_id} to {analyst}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to assign case: {e}")

    def change_status(self, case_id: int, new_status: str) -> None:
        """
        Transitions the case status utilizing the State Pattern.
        """
        logger.info(f"Requesting status change for case {case_id} to {new_status}")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            # Apply State Pattern logic
            sm = CaseStateMachine(case.status)
            sm.transition_to(new_status)
            
            old_values = case.to_dict()
            case.status = sm.get_status()
            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            # Determine matching event type
            event_type = "CASE_CLOSED" if case.status == "CLOSED" else "CASE_UPDATED"
            self.event_service.create_event(
                event_type=event_type,
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "STATUS_CHANGED",
                    "status": case.status
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="CHANGE_CASE_STATUS",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to transition status for case {case_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to transition case status: {e}")

    def add_remark(self, case_id: int, remark: str) -> None:
        """
        Appends a remark to the case history.
        """
        logger.info(f"Adding remark to case {case_id}")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            old_values = case.to_dict()
            if case.remarks:
                case.remarks += f"\n{remark}"
            else:
                case.remarks = remark

            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            self.event_service.create_event(
                event_type="CASE_UPDATED",
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "ADD_REMARK",
                    "remark": remark
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="ADD_CASE_REMARK",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add remark to case {case_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to add remark: {e}")

    def add_analyst_note(self, case_id: int, note: str) -> None:
        """
        Appends notes from the investigating analyst.
        """
        logger.info(f"Adding analyst note to case {case_id}")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            old_values = case.to_dict()
            if case.analyst_notes:
                case.analyst_notes += f"\n{note}"
            else:
                case.analyst_notes = note

            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            self.event_service.create_event(
                event_type="CASE_UPDATED",
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "ADD_NOTE",
                    "note": note
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="ADD_CASE_NOTE",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add analyst note to case {case_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to add analyst note: {e}")

    def resolve_case(self, case_id: int, resolution: str) -> None:
        """
        Transitions status to RESOLVED and stores resolution metadata.
        """
        logger.info(f"Resolving case {case_id}: {resolution}")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            sm = CaseStateMachine(case.status)
            sm.transition_to("RESOLVED")

            old_values = case.to_dict()
            case.status = sm.get_status()
            case.resolution = resolution
            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            self.event_service.create_event(
                event_type="CASE_UPDATED",
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "RESOLVED",
                    "resolution": resolution
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="RESOLVE_CASE",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to resolve case {case_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to resolve case: {e}")

    def close_case(self, case_id: int) -> None:
        """
        Transitions status to CLOSED and commits the terminal state.
        """
        logger.info(f"Closing case {case_id}")
        try:
            case = self.case_repo.find_by_id(case_id)
            if not case:
                raise ValidationException(f"Case with ID {case_id} not found.")

            sm = CaseStateMachine(case.status)
            sm.transition_to("CLOSED")

            old_values = case.to_dict()
            case.status = sm.get_status()
            case.validate()
            self.case_repo.update(case)
            self.db.commit()

            self.event_service.create_event(
                event_type="CASE_CLOSED",
                entity_type="CASE",
                entity_id=str(case_id),
                details={
                    "action": "CLOSED"
                }
            )
            
            # Log Audit Activity
            from services.audit_log_service import AuditLogService
            AuditLogService().log_audit(
                user_action="CLOSE_CASE",
                affected_table="cases",
                record_id=case_id,
                old_values=old_values,
                new_values=case.to_dict(),
                performed_by="SYSTEM"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to close case {case_id}: {e}", exc_info=True)
            if isinstance(e, ValidationException):
                raise
            raise DatabaseException(f"Failed to close case: {e}")

    def get_case_history(self, case_id: int) -> List[Any]:
        """
        Retrieves chronological Event history logs associated with the case.
        """
        try:
            return self.event_service.get_timeline("CASE", str(case_id))
        except Exception as e:
            logger.error(f"Failed to retrieve case history for Case {case_id}: {e}", exc_info=True)
            raise DatabaseException(f"Failed to retrieve case history: {e}")
