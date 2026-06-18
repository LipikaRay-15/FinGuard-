import logging
from typing import Any, List, Optional

from services.case_service import CaseService
from models import Case

logger = logging.getLogger("finguard.engines.case_manager")

class CaseManager:
    """
    Manager engine class that coordinates high-level operations for fraud cases
    and interacts with the underlying CaseService.
    """
    def __init__(self) -> None:
        self.case_service = CaseService()

    def create_case(
        self,
        alert_id: int,
        priority: str = "MEDIUM",
        notes: Optional[str] = None
    ) -> Case:
        """
        Creates a new case linked to a transaction alert.
        """
        return self.case_service.create_case(alert_id, priority, notes)

    def assign_case(self, case_id: int, analyst: str) -> None:
        """
        Assigns the case to an analyst.
        """
        self.case_service.assign_case(case_id, analyst)

    def change_status(self, case_id: int, new_status: str) -> None:
        """
        Transitions case status via State Pattern.
        """
        self.case_service.change_status(case_id, new_status)

    def add_remark(self, case_id: int, remark: str) -> None:
        """
        Adds comments/remarks to the case.
        """
        self.case_service.add_remark(case_id, remark)

    def add_analyst_note(self, case_id: int, note: str) -> None:
        """
        Adds detailed analyst notes to the case.
        """
        self.case_service.add_analyst_note(case_id, note)

    def resolve_case(self, case_id: int, resolution: str) -> None:
        """
        Resolves the case with resolution details.
        """
        self.case_service.resolve_case(case_id, resolution)

    def close_case(self, case_id: int) -> None:
        """
        Closes the case.
        """
        self.case_service.close_case(case_id)

    def get_case_history(self, case_id: int) -> List[Any]:
        """
        Fetches chronological Event history logs associated with the case.
        """
        return self.case_service.get_case_history(case_id)
