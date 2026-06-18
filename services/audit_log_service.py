import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import DatabaseException
from models import AuditLog
from repositories import AuditRepository

logger = logging.getLogger("finguard.services.audit_log_service")

class AuditLogService:
    """
    Service layer responsible for creating and retrieving system audit logs.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.audit_repo = AuditRepository()

    def log_audit(
        self,
        user_action: str,
        affected_table: Optional[str],
        record_id: Optional[int],
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        performed_by: str = "SYSTEM"
    ) -> AuditLog:
        """
        Creates and persists a new AuditLog record in the database.
        """
        logger.debug(f"Logging audit action '{user_action}' on table '{affected_table}' ID {record_id}")
        try:
            audit = AuditLog(
                audit_id=None,
                user_action=user_action,
                affected_table=affected_table,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                performed_by=performed_by,
                performed_at=datetime.now()
            )
            saved = self.audit_repo.create(audit)
            self.db.commit()
            return saved
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save audit log: {e}", exc_info=True)
            raise DatabaseException(f"Failed to log audit activity: {e}")

    def get_audit_logs(self, filters: Optional[Dict[str, Any]] = None) -> List[AuditLog]:
        """
        Retrieves audit logs filtered dynamically.
        """
        logger.debug(f"Searching audit logs with filters: {filters}")
        try:
            return self.audit_repo.search(filters or {})
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch audit logs: {e}")
