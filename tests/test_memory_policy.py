"""Tests for MemoryPolicy — SPEC §3.7, PLAN T9.3."""

from harness.memory.policy import MemoryPolicy
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)
from harness.models.persist_decision import PersistDecision, PersistOutcome


def _make_feedback(
    source: FeedbackSource,
    severity: Severity = Severity.INFO,
) -> Feedback:
    return Feedback(
        fingerprint="abc123",
        source=source,
        severity=severity,
        payload={},
        metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
        round=0,
        timestamp=0.0,
        tool_call=None,
        correlation_id=None,
    )


# ---------------------------------------------------------------------------
# Deterministic PERSIST rules
# ---------------------------------------------------------------------------


class TestPersistRules:
    def test_memory_source_persists(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.MEMORY)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.PERSIST
        assert result.category is not None
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0

    def test_memory_persist_returns_summary_category(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.MEMORY)
        result = policy.evaluate(fb)
        assert result.category == "SUMMARY"


# ---------------------------------------------------------------------------
# Deterministic DISCARD rules
# ---------------------------------------------------------------------------


class TestDiscardRules:
    def test_shell_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.SHELL)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD
        assert result.category is None

    def test_test_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.TEST)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_lint_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.LINT)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_diff_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.DIFF)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_guardrail_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.GUARDRAIL)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_parser_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.PARSER)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_tool_executor_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.TOOL_EXECUTOR)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_system_source_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.SYSTEM)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.MEMORY)
        result1 = policy.evaluate(fb)
        result2 = policy.evaluate(fb)
        assert result1 == result2

    def test_shell_always_discards(self) -> None:
        policy = MemoryPolicy()
        for _ in range(10):
            fb = _make_feedback(FeedbackSource.SHELL)
            result = policy.evaluate(fb)
            assert result.decision == PersistOutcome.DISCARD


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_persist_decision(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.SHELL)
        result = policy.evaluate(fb)
        assert isinstance(result, PersistDecision)

    def test_decision_is_enum(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.MEMORY)
        result = policy.evaluate(fb)
        assert isinstance(result.decision, PersistOutcome)


# ---------------------------------------------------------------------------
# Severity does not affect DISCARD rules
# ---------------------------------------------------------------------------


class TestSeverityIndependent:
    def test_shell_critical_still_discards(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.SHELL, Severity.CRITICAL)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.DISCARD

    def test_memory_info_still_persists(self) -> None:
        policy = MemoryPolicy()
        fb = _make_feedback(FeedbackSource.MEMORY, Severity.INFO)
        result = policy.evaluate(fb)
        assert result.decision == PersistOutcome.PERSIST
