"""Tests for GovernanceController — SPEC §3.6.4, PLAN T8.7."""

import time

from harness.feedback.controllers.governance import (
    GovernanceController,
    GovernanceDecision,
    GovernanceEvent,
    GovernanceState,
)
from harness.feedback.fingerprint import FingerprintStrategy
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)


def _make_guard_feedback(
    severity: Severity = Severity.CRITICAL,
    verdict: str = "BLOCKED",
    triggered_rules: list[str] | None = None,
) -> Feedback:
    if triggered_rules is None:
        triggered_rules = ["RuleA"]
    fb = Feedback(
        fingerprint="",
        source=FeedbackSource.GUARDRAIL,
        severity=severity,
        payload={"verdict": verdict, "triggered_rules": triggered_rules},
        metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
        round=0,
        timestamp=float(time.time()),
        tool_call=None,
        correlation_id=None,
    )
    return Feedback(
        fingerprint=FingerprintStrategy.generate(fb),
        source=fb.source,
        severity=fb.severity,
        payload=fb.payload,
        metadata=fb.metadata,
        round=fb.round,
        timestamp=fb.timestamp,
        tool_call=fb.tool_call,
        correlation_id=fb.correlation_id,
    )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_starts_in_idle(self) -> None:
        ctrl = GovernanceController()
        assert ctrl.state == GovernanceState.IDLE

    def test_no_pending_approval_initially(self) -> None:
        ctrl = GovernanceController()
        assert ctrl.pending_approval is None


# ---------------------------------------------------------------------------
# IDLE + GUARD_BLOCKED → BLOCK
# ---------------------------------------------------------------------------


class TestGuardBlocked:
    def test_idle_guard_blocked_goes_to_block(self) -> None:
        ctrl = GovernanceController()
        decision = ctrl.process_event(GovernanceEvent.GUARD_BLOCKED)
        assert ctrl.state == GovernanceState.BLOCK
        assert decision == GovernanceDecision.BLOCK

    def test_process_feedback_detects_guard_blocked(self) -> None:
        ctrl = GovernanceController()
        fb = _make_guard_feedback(severity=Severity.CRITICAL, verdict="BLOCKED")
        decision = ctrl.process(fb)
        assert ctrl.state == GovernanceState.BLOCK
        assert decision == GovernanceDecision.BLOCK


# ---------------------------------------------------------------------------
# IDLE + GUARD_FLAGGED → ASK_HUMAN
# ---------------------------------------------------------------------------


class TestGuardFlagged:
    def test_idle_guard_flagged_goes_to_ask_human(self) -> None:
        ctrl = GovernanceController()
        decision = ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.state == GovernanceState.ASK_HUMAN
        assert decision == GovernanceDecision.ASK_HUMAN

    def test_produces_approval_request(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.pending_approval is not None
        assert ctrl.pending_approval.description != ""

    def test_process_feedback_detects_guard_flagged(self) -> None:
        ctrl = GovernanceController()
        fb = _make_guard_feedback(
            severity=Severity.WARNING, verdict="APPROVAL_REQUIRED"
        )
        decision = ctrl.process(fb)
        assert ctrl.state == GovernanceState.ASK_HUMAN
        assert decision == GovernanceDecision.ASK_HUMAN


# ---------------------------------------------------------------------------
# ASK_HUMAN + APPROVED → IDLE
# ---------------------------------------------------------------------------


class TestAskHumanApproved:
    def test_ask_human_approved_goes_to_idle(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.state == GovernanceState.ASK_HUMAN
        decision = ctrl.process_event(GovernanceEvent.APPROVED)
        assert ctrl.state == GovernanceState.IDLE  # type: ignore[comparison-overlap]
        assert decision == GovernanceDecision.IDLE

    def test_pending_approval_cleared_after_approved(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.pending_approval is not None
        ctrl.process_event(GovernanceEvent.APPROVED)
        assert ctrl.pending_approval is None


# ---------------------------------------------------------------------------
# ASK_HUMAN + REJECTED → IDLE
# ---------------------------------------------------------------------------


class TestAskHumanRejected:
    def test_ask_human_rejected_goes_to_idle(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.state == GovernanceState.ASK_HUMAN
        decision = ctrl.process_event(GovernanceEvent.REJECTED)
        assert ctrl.state == GovernanceState.IDLE  # type: ignore[comparison-overlap]
        assert decision == GovernanceDecision.IDLE

    def test_pending_approval_cleared_after_rejected(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.pending_approval is not None
        ctrl.process_event(GovernanceEvent.REJECTED)
        assert ctrl.pending_approval is None


# ---------------------------------------------------------------------------
# IDLE + CONVERGENCE_FAILURE → FORCE_STOP
# ---------------------------------------------------------------------------


class TestConvergenceFailure:
    def test_idle_convergence_failure_goes_to_force_stop(self) -> None:
        ctrl = GovernanceController()
        decision = ctrl.process_event(GovernanceEvent.CONVERGENCE_FAILURE)
        assert ctrl.state == GovernanceState.FORCE_STOP
        assert decision == GovernanceDecision.FORCE_STOP


# ---------------------------------------------------------------------------
# IDLE + PRIVILEGE_ESCALATION → ASK_HUMAN
# ---------------------------------------------------------------------------


class TestPrivilegeEscalation:
    def test_idle_privilege_escalation_goes_to_ask_human(self) -> None:
        ctrl = GovernanceController()
        decision = ctrl.process_event(GovernanceEvent.PRIVILEGE_ESCALATION)
        assert ctrl.state == GovernanceState.ASK_HUMAN
        assert decision == GovernanceDecision.ASK_HUMAN

    def test_produces_approval_request(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.PRIVILEGE_ESCALATION)
        assert ctrl.pending_approval is not None


# ---------------------------------------------------------------------------
# Table-driven design
# ---------------------------------------------------------------------------


class TestTableDriven:
    def test_transition_table_is_data_structure(self) -> None:
        from harness.feedback.controllers.governance import _TRANSITIONS
        assert isinstance(_TRANSITIONS, (list, tuple))
        assert len(_TRANSITIONS) == 6
        for entry in _TRANSITIONS:
            assert len(entry) == 4
            current_state, event, next_state, decision = entry
            assert isinstance(current_state, GovernanceState)
            assert isinstance(event, GovernanceEvent)
            assert isinstance(next_state, GovernanceState)
            assert isinstance(decision, GovernanceDecision)


# ---------------------------------------------------------------------------
# No transitions from BLOCK / FORCE_STOP / AUDIT
# ---------------------------------------------------------------------------


class TestTerminalStates:
    def test_block_has_no_exit_transition(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.GUARD_BLOCKED)
        assert ctrl.state == GovernanceState.BLOCK
        # Trying to process another event should stay in BLOCK
        decision = ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.state == GovernanceState.BLOCK
        assert decision == GovernanceDecision.BLOCK

    def test_force_stop_has_no_exit_transition(self) -> None:
        ctrl = GovernanceController()
        ctrl.process_event(GovernanceEvent.CONVERGENCE_FAILURE)
        assert ctrl.state == GovernanceState.FORCE_STOP
        decision = ctrl.process_event(GovernanceEvent.GUARD_FLAGGED)
        assert ctrl.state == GovernanceState.FORCE_STOP
        assert decision == GovernanceDecision.FORCE_STOP
