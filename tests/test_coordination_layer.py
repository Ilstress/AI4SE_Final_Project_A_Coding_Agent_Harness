"""Tests for CoordinationLayer — SPEC §3.6.5, PLAN T8.8."""

from harness.feedback.controllers.governance import GovernanceState
from harness.feedback.controllers.recovery import RecoveryState
from harness.feedback.coordination import (
    CoordinationLayer,
    EscalationEvent,
    RecoverySignal,
)
from harness.feedback.fingerprint import FingerprintStrategy
from harness.models.approval import ApprovalOutcome
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)


def _make_feedback(
    source: FeedbackSource = FeedbackSource.SHELL,
    severity: Severity = Severity.ERROR,
    command: str = "rm -rf /",
) -> Feedback:
    fb = Feedback(
        fingerprint="",
        source=source,
        severity=severity,
        payload={"command": command},
        metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
        round=0,
        timestamp=0.0,
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
# Convergence detection
# ---------------------------------------------------------------------------


class TestConvergenceDetection:
    def test_three_same_fingerprints_trigger_convergence_failure(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(command="cmd_a")
        layer.record(fb)
        layer.record(fb)
        layer.record(fb)
        result = layer.check_convergence()
        assert result == EscalationEvent.CONVERGENCE_FAILURE

    def test_two_same_fingerprints_no_convergence(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(command="cmd_a")
        layer.record(fb)
        layer.record(fb)
        result = layer.check_convergence()
        assert result is None

    def test_three_different_fingerprints_no_convergence(self) -> None:
        layer = CoordinationLayer()
        fb1 = _make_feedback(command="cmd_a")
        fb2 = _make_feedback(command="cmd_b")
        fb3 = _make_feedback(command="cmd_c")
        layer.record(fb1)
        layer.record(fb2)
        layer.record(fb3)
        result = layer.check_convergence()
        assert result is None

    def test_three_same_with_interleaved_no_convergence(self) -> None:
        """Non-consecutive same fingerprints should NOT trigger convergence."""
        layer = CoordinationLayer()
        fb_a = _make_feedback(command="cmd_a")
        fb_b = _make_feedback(command="cmd_b")
        layer.record(fb_a)
        layer.record(fb_b)
        layer.record(fb_a)
        result = layer.check_convergence()
        assert result is None

    def test_four_same_triggers_convergence(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(command="cmd_a")
        layer.record(fb)
        layer.record(fb)
        layer.record(fb)
        layer.record(fb)
        result = layer.check_convergence()
        assert result == EscalationEvent.CONVERGENCE_FAILURE

    def test_reset_clears_history(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(command="cmd_a")
        layer.record(fb)
        layer.record(fb)
        layer.record(fb)
        assert layer.check_convergence() is not None
        layer.reset()
        assert layer.check_convergence() is None


# ---------------------------------------------------------------------------
# Escalation evaluation
# ---------------------------------------------------------------------------


class TestEscalationEvaluation:
    def test_guardrail_trigger_from_feedback(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(source=FeedbackSource.GUARDRAIL, severity=Severity.CRITICAL)
        result = layer.evaluate_escalation(
            recovery_state=RecoveryState.CONTINUE,
            feedback=fb,
        )
        assert result == EscalationEvent.GUARDRAIL_TRIGGER

    def test_privilege_escalation_explicit(self) -> None:
        layer = CoordinationLayer()
        result = layer.evaluate_escalation(
            recovery_state=RecoveryState.REPLAN,
            feedback=_make_feedback(),
        )
        assert result == EscalationEvent.PRIVILEGE_ESCALATION

    def test_no_escalation_for_normal_feedback(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(source=FeedbackSource.SHELL)
        result = layer.evaluate_escalation(
            recovery_state=RecoveryState.CONTINUE,
            feedback=fb,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Recovery signal evaluation
# ---------------------------------------------------------------------------


class TestRecoverySignal:
    def test_hitl_approved_from_ask_human(self) -> None:
        layer = CoordinationLayer()
        result = layer.evaluate_recovery(
            governance_state=GovernanceState.ASK_HUMAN,
            approval_outcome=ApprovalOutcome.APPROVED,
        )
        assert result == RecoverySignal.HITL_APPROVED

    def test_hitl_rejected_from_ask_human(self) -> None:
        layer = CoordinationLayer()
        result = layer.evaluate_recovery(
            governance_state=GovernanceState.ASK_HUMAN,
            approval_outcome=ApprovalOutcome.REJECTED,
        )
        assert result == RecoverySignal.HITL_REJECTED

    def test_no_signal_when_not_ask_human(self) -> None:
        layer = CoordinationLayer()
        result = layer.evaluate_recovery(
            governance_state=GovernanceState.IDLE,
            approval_outcome=ApprovalOutcome.APPROVED,
        )
        assert result is None

    def test_timeout_no_signal(self) -> None:
        layer = CoordinationLayer()
        result = layer.evaluate_recovery(
            governance_state=GovernanceState.ASK_HUMAN,
            approval_outcome=ApprovalOutcome.TIMEOUT,
        )
        assert result is None


# ---------------------------------------------------------------------------
# No controller internal state
# ---------------------------------------------------------------------------


class TestNoControllerState:
    def test_does_not_hold_recovery_controller(self) -> None:
        layer = CoordinationLayer()
        assert not hasattr(layer, "recovery_controller")
        assert not hasattr(layer, "_recovery_controller")

    def test_does_not_hold_governance_controller(self) -> None:
        layer = CoordinationLayer()
        assert not hasattr(layer, "governance_controller")
        assert not hasattr(layer, "_governance_controller")


# ---------------------------------------------------------------------------
# Fingerprint history
# ---------------------------------------------------------------------------


class TestFingerprintHistory:
    def test_history_is_initially_empty(self) -> None:
        layer = CoordinationLayer()
        assert layer.fingerprint_history == []

    def test_history_returns_copy(self) -> None:
        layer = CoordinationLayer()
        fb = _make_feedback(command="cmd_a")
        layer.record(fb)
        history = layer.fingerprint_history
        history.append("tampered")
        assert layer.fingerprint_history == [fb.fingerprint]
