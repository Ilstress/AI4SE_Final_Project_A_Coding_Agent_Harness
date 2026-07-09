"""Tests for RecoveryController — SPEC §3.6.3, PLAN T8.6."""

from harness.feedback.controllers.recovery import (
    RecoveryController,
    RecoveryDecision,
    RecoveryEvent,
    RecoveryState,
)
from harness.feedback.fingerprint import FingerprintStrategy
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
    # Generate the fingerprint so SAME_ERROR detection works
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
        ctrl = RecoveryController()
        assert ctrl.state == RecoveryState.IDLE

    def test_consecutive_count_starts_at_zero(self) -> None:
        ctrl = RecoveryController()
        assert ctrl.consecutive_count == 0


# ---------------------------------------------------------------------------
# IDLE transitions
# ---------------------------------------------------------------------------


class TestIdleTransitions:
    def test_idle_feedback_received_goes_to_continue(self) -> None:
        ctrl = RecoveryController()
        fb = _make_feedback()
        decision = ctrl.process(fb)
        assert ctrl.state == RecoveryState.CONTINUE
        assert decision == RecoveryDecision.CONTINUE


# ---------------------------------------------------------------------------
# CONTINUE transitions
# ---------------------------------------------------------------------------


class TestContinueTransitions:
    def test_continue_feedback_received_stays_in_continue(self) -> None:
        ctrl = RecoveryController()
        fb1 = _make_feedback(command="cmd_a")
        fb2 = _make_feedback(command="cmd_b")  # different → FEEDBACK_RECEIVED
        ctrl.process(fb1)  # IDLE → CONTINUE
        assert ctrl.state == RecoveryState.CONTINUE
        decision = ctrl.process(fb2)  # CONTINUE + FEEDBACK_RECEIVED
        assert ctrl.state == RecoveryState.CONTINUE
        assert decision == RecoveryDecision.CONTINUE

    def test_continue_same_error_goes_to_retry(self) -> None:
        ctrl = RecoveryController()
        fb1 = _make_feedback(command="cmd_a")
        fb2 = _make_feedback(command="cmd_a")  # same → SAME_ERROR
        ctrl.process(fb1)  # IDLE → CONTINUE
        assert ctrl.state == RecoveryState.CONTINUE
        decision = ctrl.process(fb2)  # CONTINUE + SAME_ERROR → RETRY
        assert ctrl.state == RecoveryState.RETRY  # type: ignore[comparison-overlap]
        assert decision == RecoveryDecision.RETRY
        assert ctrl.consecutive_count == 2


# ---------------------------------------------------------------------------
# RETRY transitions
# ---------------------------------------------------------------------------


class TestRetryTransitions:
    def test_retry_same_error_stays_in_retry(self) -> None:
        ctrl = RecoveryController()
        fb = _make_feedback(command="cmd_a")
        ctrl.process(fb)  # IDLE → CONTINUE
        ctrl.process(fb)  # CONTINUE + SAME_ERROR → RETRY, count=2
        assert ctrl.state == RecoveryState.RETRY
        decision = ctrl.process(fb)  # RETRY + SAME_ERROR → RETRY (count=3, but < threshold at check time)
        assert ctrl.state == RecoveryState.RETRY
        assert decision == RecoveryDecision.RETRY

    def test_retry_feedback_resolved_goes_to_continue(self) -> None:
        ctrl = RecoveryController()
        fb1 = _make_feedback(command="cmd_a")
        fb2 = _make_feedback(command="cmd_b")  # different
        ctrl.process(fb1)  # IDLE → CONTINUE
        ctrl.process(fb1)  # CONTINUE + SAME_ERROR → RETRY
        assert ctrl.state == RecoveryState.RETRY
        decision = ctrl.process(fb2)  # RETRY + FEEDBACK_RESOLVED → CONTINUE
        assert ctrl.state == RecoveryState.CONTINUE  # type: ignore[comparison-overlap]
        assert decision == RecoveryDecision.CONTINUE
        assert ctrl.consecutive_count == 1  # reset for new fingerprint

    def test_retry_threshold_goes_to_replan(self) -> None:
        ctrl = RecoveryController()
        fb = _make_feedback(command="cmd_a")
        ctrl.process(fb)  # IDLE → CONTINUE, count=1
        ctrl.process(fb)  # CONTINUE + SAME_ERROR → RETRY, count=2
        ctrl.process(fb)  # RETRY + SAME_ERROR → RETRY, count=3
        assert ctrl.state == RecoveryState.RETRY
        assert ctrl.consecutive_count == 3
        # 4th same error → threshold reached
        decision = ctrl.process(fb)  # RETRY + RETRY_THRESHOLD → REPLAN
        assert ctrl.state == RecoveryState.REPLAN  # type: ignore[comparison-overlap]
        assert decision == RecoveryDecision.REPLAN


# ---------------------------------------------------------------------------
# REPLAN transitions
# ---------------------------------------------------------------------------


class TestReplanTransitions:
    def test_replan_feedback_received_goes_to_continue(self) -> None:
        ctrl = RecoveryController()
        fb_same = _make_feedback(command="cmd_a")
        fb_diff = _make_feedback(command="cmd_b")
        # Reach REPLAN state
        ctrl.process(fb_same)  # IDLE → CONTINUE
        ctrl.process(fb_same)  # CONTINUE + SAME_ERROR → RETRY
        ctrl.process(fb_same)  # RETRY + SAME_ERROR → RETRY, count=3
        ctrl.process(fb_same)  # RETRY + RETRY_THRESHOLD → REPLAN
        assert ctrl.state == RecoveryState.REPLAN
        # Now different feedback → FEEDBACK_RECEIVED
        decision = ctrl.process(fb_diff)
        assert ctrl.state == RecoveryState.CONTINUE  # type: ignore[comparison-overlap]
        assert decision == RecoveryDecision.CONTINUE
        assert ctrl.consecutive_count == 1  # reset

    def test_replan_same_error_upgrades(self) -> None:
        ctrl = RecoveryController()
        fb = _make_feedback(command="cmd_a")
        # Reach REPLAN state
        ctrl.process(fb)  # IDLE → CONTINUE
        ctrl.process(fb)  # CONTINUE + SAME_ERROR → RETRY
        ctrl.process(fb)  # RETRY + SAME_ERROR → RETRY, count=3
        ctrl.process(fb)  # RETRY + RETRY_THRESHOLD → REPLAN
        assert ctrl.state == RecoveryState.REPLAN
        # Same error in REPLAN → UPGRADE
        decision = ctrl.process(fb)
        assert decision == RecoveryDecision.UPGRADE
        assert ctrl.state == RecoveryState.IDLE  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------------------
# Table-driven design
# ---------------------------------------------------------------------------


class TestTableDriven:
    def test_transition_table_is_data_structure(self) -> None:
        """Verify the transition table is defined as a data structure, not if-else."""
        from harness.feedback.controllers.recovery import _TRANSITIONS
        assert isinstance(_TRANSITIONS, (list, tuple))
        assert len(_TRANSITIONS) == 8
        for entry in _TRANSITIONS:
            assert len(entry) == 4
            current_state, event, next_state, decision = entry
            assert isinstance(current_state, RecoveryState)
            assert isinstance(event, RecoveryEvent)
            assert isinstance(next_state, RecoveryState)
            assert isinstance(decision, RecoveryDecision)


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------


class TestEventClassification:
    def test_different_severity_different_fingerprint(self) -> None:
        """Different severity → different fingerprint → FEEDBACK_RECEIVED, not SAME_ERROR."""
        ctrl = RecoveryController()
        fb_error = _make_feedback(severity=Severity.ERROR, command="cmd_a")
        fb_info = _make_feedback(severity=Severity.INFO, command="cmd_a")
        ctrl.process(fb_error)  # IDLE → CONTINUE
        decision = ctrl.process(fb_info)  # different fingerprint → FEEDBACK_RECEIVED
        assert ctrl.state == RecoveryState.CONTINUE
        assert decision == RecoveryDecision.CONTINUE

    def test_different_source_different_fingerprint(self) -> None:
        """Different source → different fingerprint → FEEDBACK_RECEIVED."""
        ctrl = RecoveryController()
        fb_shell = _make_feedback(source=FeedbackSource.SHELL, command="cmd_a")
        fb_test = Feedback(
            fingerprint=FingerprintStrategy.generate(
                _make_feedback(source=FeedbackSource.TEST, severity=Severity.ERROR)
            ),
            source=FeedbackSource.TEST,
            severity=Severity.ERROR,
            payload={"failed": 1, "passed": 9, "total": 10},
            metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
            round=0,
            timestamp=0.0,
            tool_call=None,
            correlation_id=None,
        )
        ctrl.process(fb_shell)  # IDLE → CONTINUE
        decision = ctrl.process(fb_test)  # different fingerprint → FEEDBACK_RECEIVED
        assert ctrl.state == RecoveryState.CONTINUE
        assert decision == RecoveryDecision.CONTINUE
