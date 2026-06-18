import logging
from abc import ABC
from exceptions import ValidationException

logger = logging.getLogger("finguard.engines.case_state_machine")

class CaseState(ABC):
    """
    Abstract State base class in the State Pattern.
    Declares transition operations and defines a default invalid behavior.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    def to_open(self, context: "CaseStateMachine") -> None:
        raise ValidationException(f"Invalid transition from state {self.name} to OPEN.")

    def to_under_review(self, context: "CaseStateMachine") -> None:
        raise ValidationException(f"Invalid transition from state {self.name} to UNDER_REVIEW.")

    def to_escalated(self, context: "CaseStateMachine") -> None:
        raise ValidationException(f"Invalid transition from state {self.name} to ESCALATED.")

    def to_resolved(self, context: "CaseStateMachine") -> None:
        raise ValidationException(f"Invalid transition from state {self.name} to RESOLVED.")

    def to_closed(self, context: "CaseStateMachine") -> None:
        raise ValidationException(f"Invalid transition from state {self.name} to CLOSED.")


class OpenState(CaseState):
    """
    State representing an OPEN case.
    Can transition to: UNDER_REVIEW.
    """
    def __init__(self) -> None:
        super().__init__("OPEN")

    def to_under_review(self, context: "CaseStateMachine") -> None:
        logger.debug("Transitioning case state: OPEN -> UNDER_REVIEW")
        context.set_state(UnderReviewState())


class UnderReviewState(CaseState):
    """
    State representing a case UNDER_REVIEW.
    Can transition to: ESCALATED or RESOLVED.
    """
    def __init__(self) -> None:
        super().__init__("UNDER_REVIEW")

    def to_escalated(self, context: "CaseStateMachine") -> None:
        logger.debug("Transitioning case state: UNDER_REVIEW -> ESCALATED")
        context.set_state(EscalatedState())

    def to_resolved(self, context: "CaseStateMachine") -> None:
        logger.debug("Transitioning case state: UNDER_REVIEW -> RESOLVED")
        context.set_state(ResolvedState())


class EscalatedState(CaseState):
    """
    State representing an ESCALATED case.
    Can transition to: RESOLVED.
    """
    def __init__(self) -> None:
        super().__init__("ESCALATED")

    def to_resolved(self, context: "CaseStateMachine") -> None:
        logger.debug("Transitioning case state: ESCALATED -> RESOLVED")
        context.set_state(ResolvedState())


class ResolvedState(CaseState):
    """
    State representing a RESOLVED case.
    Can transition to: CLOSED.
    """
    def __init__(self) -> None:
        super().__init__("RESOLVED")

    def to_closed(self, context: "CaseStateMachine") -> None:
        logger.debug("Transitioning case state: RESOLVED -> CLOSED")
        context.set_state(ClosedState())


class ClosedState(CaseState):
    """
    State representing a CLOSED case.
    Terminal state. No transitions allowed.
    """
    def __init__(self) -> None:
        super().__init__("CLOSED")


class CaseStateMachine:
    """
    Context class in the State Pattern.
    Manages current state transitions and parses target status strings.
    """
    def __init__(self, initial_status: str) -> None:
        status_upper = initial_status.upper().strip()
        self.state = self._map_status_to_state(status_upper)

    def _map_status_to_state(self, status: str) -> CaseState:
        if status == "OPEN":
            return OpenState()
        elif status == "UNDER_REVIEW":
            return UnderReviewState()
        elif status == "ESCALATED":
            return EscalatedState()
        elif status == "RESOLVED":
            return ResolvedState()
        elif status == "CLOSED":
            return ClosedState()
        else:
            raise ValidationException(f"Unknown initial status for case state machine: {status}")

    def set_state(self, state: CaseState) -> None:
        self.state = state

    def get_status(self) -> str:
        return self.state.name

    def to_open(self) -> None:
        self.state.to_open(self)

    def to_under_review(self) -> None:
        self.state.to_under_review(self)

    def to_escalated(self) -> None:
        self.state.to_escalated(self)

    def to_resolved(self) -> None:
        self.state.to_resolved(self)

    def to_closed(self) -> None:
        self.state.to_closed(self)

    def transition_to(self, new_status: str) -> None:
        """
        Orchestrates transition to a target status string by invoking the matching method.
        """
        target = new_status.upper().strip()
        if target == "OPEN":
            self.to_open()
        elif target == "UNDER_REVIEW":
            self.to_under_review()
        elif target == "ESCALATED":
            self.to_escalated()
        elif target == "RESOLVED":
            self.to_resolved()
        elif target == "CLOSED":
            self.to_closed()
        else:
            raise ValidationException(f"Unknown target state: {new_status}")
