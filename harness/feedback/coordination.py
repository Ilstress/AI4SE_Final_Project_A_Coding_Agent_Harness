"""CoordinationLayer — cross-controller coordination (SPEC §3.6.5, PLAN T8.8)."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from harness.models.approval import ApprovalOutcome
from harness.models.feedback import Feedback, FeedbackSource

if TYPE_CHECKING:
    from harness.feedback.controllers.governance import GovernanceState
    from harness.feedback.controllers.recovery import RecoveryState


class EscalationEvent(Enum):
    """Events emitted by CoordinationLayer to escalate Recovery → Governance."""

    CONVERGENCE_FAILURE = "CONVERGENCE_FAILURE"
    GUARDRAIL_TRIGGER = "GUARDRAIL_TRIGGER"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"


class RecoverySignal(Enum):
    """Signals emitted by CoordinationLayer to resume Governance → Recovery."""

    HITL_APPROVED = "HITL_APPROVED"
    HITL_REJECTED = "HITL_REJECTED"


class CoordinationLayer:
    """Pure observer + event emitter that coordinates Recovery and Governance.

    Does NOT hold controller internal state — only reads state and emits events.
    Tracks fingerprint history for convergence detection.
    """

    CONVERGENCE_THRESHOLD = 3

    def __init__(self) -> None:
        self._fingerprint_history: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def fingerprint_history(self) -> list[str]:
        """Return a copy of the fingerprint history (read-only)."""
        return list(self._fingerprint_history)

    def record(self, feedback: Feedback) -> None:
        """Record a feedback fingerprint for convergence tracking."""
        self._fingerprint_history.append(feedback.fingerprint)

    def check_convergence(self) -> EscalationEvent | None:
        """Check whether the last N fingerprints are all identical.

        Returns CONVERGENCE_FAILURE if the convergence threshold is reached.
        """
        if len(self._fingerprint_history) < self.CONVERGENCE_THRESHOLD:
            return None
        last_n = self._fingerprint_history[-self.CONVERGENCE_THRESHOLD :]
        if len(set(last_n)) == 1:
            return EscalationEvent.CONVERGENCE_FAILURE
        return None

    def evaluate_escalation(
        self,
        recovery_state: RecoveryState,
        feedback: Feedback,
    ) -> EscalationEvent | None:
        """Evaluate whether escalation from Recovery to Governance is needed.

        Checks (in priority order):
          1. Convergence failure (same fingerprint N consecutive times)
          2. Guardrail trigger (feedback source is GUARDRAIL)
          3. Privilege escalation (recovery state is REPLAN)
        """
        # Check convergence first
        convergence = self.check_convergence()
        if convergence is not None:
            return convergence

        # Guardrail trigger
        if feedback.source == FeedbackSource.GUARDRAIL:
            return EscalationEvent.GUARDRAIL_TRIGGER

        # Privilege escalation when recovery has exhausted its options
        if recovery_state.value == "REPLAN":
            return EscalationEvent.PRIVILEGE_ESCALATION

        return None

    def evaluate_recovery(
        self,
        governance_state: GovernanceState,
        approval_outcome: ApprovalOutcome,
    ) -> RecoverySignal | None:
        """Evaluate whether recovery from Governance back to Recovery is needed.

        Returns HITL_APPROVED or HITL_REJECTED when governance is in ASK_HUMAN.
        """
        if governance_state.value == "ASK_HUMAN":
            if approval_outcome == ApprovalOutcome.APPROVED:
                return RecoverySignal.HITL_APPROVED
            if approval_outcome == ApprovalOutcome.REJECTED:
                return RecoverySignal.HITL_REJECTED
        return None

    def reset(self) -> None:
        """Clear fingerprint history (e.g., after a successful recovery)."""
        self._fingerprint_history.clear()
