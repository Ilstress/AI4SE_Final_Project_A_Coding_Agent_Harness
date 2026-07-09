"""GovernanceController — table-driven state machine for safety events (SPEC §3.6.4, PLAN T8.7)."""

import time
from enum import Enum

from harness.models.approval import ApprovalRequest
from harness.models.feedback import Feedback, FeedbackSource, Severity


class GovernanceState(Enum):
    """States of the GovernanceController state machine."""

    IDLE = "IDLE"
    BLOCK = "BLOCK"
    ASK_HUMAN = "ASK_HUMAN"
    FORCE_STOP = "FORCE_STOP"
    AUDIT = "AUDIT"


class GovernanceEvent(Enum):
    """Events that trigger state transitions."""

    GUARD_BLOCKED = "GUARD_BLOCKED"
    GUARD_FLAGGED = "GUARD_FLAGGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERGENCE_FAILURE = "CONVERGENCE_FAILURE"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"


class GovernanceDecision(Enum):
    """Decisions produced by the GovernanceController."""

    BLOCK = "BLOCK"
    ASK_HUMAN = "ASK_HUMAN"
    FORCE_STOP = "FORCE_STOP"
    AUDIT = "AUDIT"
    IDLE = "IDLE"


# Transition: (current_state, event, next_state, decision)
_Transition = tuple[GovernanceState, GovernanceEvent, GovernanceState, GovernanceDecision]

_TRANSITIONS: list[_Transition] = [
    (GovernanceState.IDLE, GovernanceEvent.GUARD_BLOCKED, GovernanceState.BLOCK, GovernanceDecision.BLOCK),
    (GovernanceState.IDLE, GovernanceEvent.GUARD_FLAGGED, GovernanceState.ASK_HUMAN, GovernanceDecision.ASK_HUMAN),
    (GovernanceState.ASK_HUMAN, GovernanceEvent.APPROVED, GovernanceState.IDLE, GovernanceDecision.IDLE),
    (GovernanceState.ASK_HUMAN, GovernanceEvent.REJECTED, GovernanceState.IDLE, GovernanceDecision.IDLE),
    (GovernanceState.IDLE, GovernanceEvent.CONVERGENCE_FAILURE, GovernanceState.FORCE_STOP, GovernanceDecision.FORCE_STOP),
    (GovernanceState.IDLE, GovernanceEvent.PRIVILEGE_ESCALATION, GovernanceState.ASK_HUMAN, GovernanceDecision.ASK_HUMAN),
]


class GovernanceController:
    """Table-driven state machine for safety-critical governance.

    Does NOT perform approval interaction — only produces ApprovalRequest.
    Main Loop handles actual human interaction via HumanApprovalProvider.
    """

    def __init__(self) -> None:
        self._state = GovernanceState.IDLE
        self._pending_approval: ApprovalRequest | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> GovernanceState:
        return self._state

    @property
    def pending_approval(self) -> ApprovalRequest | None:
        return self._pending_approval

    def process(self, feedback: Feedback) -> GovernanceDecision:
        """Process a Feedback event routed to the Governance track."""
        event = self._feedback_to_event(feedback)
        return self._apply_transition(event, feedback)

    def process_event(self, event: GovernanceEvent) -> GovernanceDecision:
        """Process a coordination-layer event (APPROVED, REJECTED, etc.)."""
        return self._apply_transition(event, None)

    # ------------------------------------------------------------------
    # Event detection from Feedback
    # ------------------------------------------------------------------

    @staticmethod
    def _feedback_to_event(feedback: Feedback) -> GovernanceEvent:
        if feedback.source == FeedbackSource.GUARDRAIL:
            if feedback.severity == Severity.CRITICAL:
                return GovernanceEvent.GUARD_BLOCKED
            if feedback.severity == Severity.WARNING:
                return GovernanceEvent.GUARD_FLAGGED
        # Fallback: treat as guard blocked
        return GovernanceEvent.GUARD_BLOCKED

    # ------------------------------------------------------------------
    # Transition lookup & side effects
    # ------------------------------------------------------------------

    def _apply_transition(
        self,
        event: GovernanceEvent,
        feedback: Feedback | None,
    ) -> GovernanceDecision:
        for current_state, evt, next_state, decision in _TRANSITIONS:
            if current_state == self._state and evt == event:
                self._execute_side_effects(event, next_state, feedback)
                self._state = next_state
                return decision

        # No matching transition: stay in current state, return current decision
        return self._current_decision()

    def _current_decision(self) -> GovernanceDecision:
        """Infer the decision that corresponds to the current state."""
        state_to_decision = {
            GovernanceState.IDLE: GovernanceDecision.IDLE,
            GovernanceState.BLOCK: GovernanceDecision.BLOCK,
            GovernanceState.ASK_HUMAN: GovernanceDecision.ASK_HUMAN,
            GovernanceState.FORCE_STOP: GovernanceDecision.FORCE_STOP,
            GovernanceState.AUDIT: GovernanceDecision.AUDIT,
        }
        return state_to_decision.get(self._state, GovernanceDecision.IDLE)

    def _execute_side_effects(
        self,
        event: GovernanceEvent,
        next_state: GovernanceState,
        feedback: Feedback | None,
    ) -> None:
        # Produce ApprovalRequest when entering ASK_HUMAN
        if next_state == GovernanceState.ASK_HUMAN:
            description = self._build_approval_description(event, feedback)
            self._pending_approval = ApprovalRequest(
                description=description,
                evidence=self._build_evidence(feedback),
                timestamp=time.time(),
            )
        # Clear pending approval when leaving ASK_HUMAN
        if self._state == GovernanceState.ASK_HUMAN and next_state == GovernanceState.IDLE:
            self._pending_approval = None

    @staticmethod
    def _build_approval_description(
        event: GovernanceEvent, feedback: Feedback | None
    ) -> str:
        if event == GovernanceEvent.GUARD_FLAGGED:
            return "Guardrail flagged this action for human review."
        if event == GovernanceEvent.PRIVILEGE_ESCALATION:
            return "Privilege escalation detected — requires human approval."
        return "Action requires human approval."

    @staticmethod
    def _build_evidence(feedback: Feedback | None) -> list[dict]:
        if feedback is not None:
            return [{"source": feedback.source.value, "severity": feedback.severity.value, **feedback.payload}]
        return []
