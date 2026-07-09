"""Tests for FingerprintStrategy — SPEC §3.6.1, PLAN T8.4."""

from harness.feedback.fingerprint import FingerprintStrategy
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)


def _make_feedback(
    source: FeedbackSource,
    severity: Severity,
    payload: dict,
) -> Feedback:
    return Feedback(
        fingerprint="",
        source=source,
        severity=severity,
        payload=payload,
        metadata=FeedbackMetadata(provider="", latency_ms=10, retry_count=0, trace_id=None),
        round=0,
        timestamp=1234567890.0,
        tool_call=None,
        correlation_id=None,
    )


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------


class TestDeterministic:
    def test_same_input_same_fingerprint(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.SHELL,
            Severity.ERROR,
            {"command": "rm -rf /", "exit_code": 1},
        )
        fb2 = _make_feedback(
            FeedbackSource.SHELL,
            Severity.ERROR,
            {"command": "rm -rf /", "exit_code": 1},
        )
        assert FingerprintStrategy.generate(fb1) == FingerprintStrategy.generate(fb2)

    def test_different_source_different_fingerprint(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "rm -rf /"}
        )
        fb2 = _make_feedback(
            FeedbackSource.TEST, Severity.ERROR, {"command": "rm -rf /"}
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_different_severity_different_fingerprint(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "rm -rf /"}
        )
        fb2 = _make_feedback(
            FeedbackSource.SHELL, Severity.WARNING, {"command": "rm -rf /"}
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_same_command_different_params_different_fingerprint(self) -> None:
        """PLAN: same command different params → different fingerprint."""
        fb1 = _make_feedback(
            FeedbackSource.SHELL,
            Severity.ERROR,
            {"command": "rm -rf /tmp/a"},
        )
        fb2 = _make_feedback(
            FeedbackSource.SHELL,
            Severity.ERROR,
            {"command": "rm -rf /tmp/b"},
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)


# ---------------------------------------------------------------------------
# Timestamp / round do not affect fingerprint
# ---------------------------------------------------------------------------


class TestExcludesVolatileFields:
    def test_different_timestamp_same_fingerprint(self) -> None:
        payload = {"command": "rm -rf /"}
        fb1 = _make_feedback(FeedbackSource.SHELL, Severity.ERROR, payload)
        fb2 = Feedback(
            fingerprint="",
            source=FeedbackSource.SHELL,
            severity=Severity.ERROR,
            payload=payload,
            metadata=FeedbackMetadata(provider="", latency_ms=10, retry_count=0, trace_id=None),
            round=0,
            timestamp=9999999999.0,  # different
            tool_call=None,
            correlation_id=None,
        )
        assert FingerprintStrategy.generate(fb1) == FingerprintStrategy.generate(fb2)

    def test_different_round_same_fingerprint(self) -> None:
        payload = {"command": "rm -rf /"}
        fb1 = _make_feedback(FeedbackSource.SHELL, Severity.ERROR, payload)
        fb2 = Feedback(
            fingerprint="",
            source=FeedbackSource.SHELL,
            severity=Severity.ERROR,
            payload=payload,
            metadata=FeedbackMetadata(provider="", latency_ms=10, retry_count=0, trace_id=None),
            round=5,  # different
            timestamp=1234567890.0,
            tool_call=None,
            correlation_id=None,
        )
        assert FingerprintStrategy.generate(fb1) == FingerprintStrategy.generate(fb2)

    def test_different_latency_same_fingerprint(self) -> None:
        payload = {"command": "rm -rf /"}
        fb1 = _make_feedback(FeedbackSource.SHELL, Severity.ERROR, payload)
        fb2 = Feedback(
            fingerprint="",
            source=FeedbackSource.SHELL,
            severity=Severity.ERROR,
            payload=payload,
            metadata=FeedbackMetadata(provider="", latency_ms=999, retry_count=0, trace_id=None),
            round=0,
            timestamp=1234567890.0,
            tool_call=None,
            correlation_id=None,
        )
        assert FingerprintStrategy.generate(fb1) == FingerprintStrategy.generate(fb2)


# ---------------------------------------------------------------------------
# Per-source key_params
# ---------------------------------------------------------------------------


class TestPerSourceKeyParams:
    def test_shell_uses_command(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "cmd_a"}
        )
        fb2 = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "cmd_b"}
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_test_uses_failed_count(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.TEST, Severity.ERROR, {"failed": 1, "passed": 9, "total": 10}
        )
        fb2 = _make_feedback(
            FeedbackSource.TEST, Severity.ERROR, {"failed": 2, "passed": 8, "total": 10}
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_lint_uses_errors(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.LINT, Severity.WARNING, {"errors": ["E501"]}
        )
        fb2 = _make_feedback(
            FeedbackSource.LINT, Severity.WARNING, {"errors": ["F401"]}
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_guardrail_uses_triggered_rules(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.GUARDRAIL,
            Severity.CRITICAL,
            {"verdict": "BLOCKED", "triggered_rules": ["RuleA"]},
        )
        fb2 = _make_feedback(
            FeedbackSource.GUARDRAIL,
            Severity.CRITICAL,
            {"verdict": "BLOCKED", "triggered_rules": ["RuleB"]},
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_parser_uses_error_type(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.PARSER,
            Severity.WARNING,
            {"error_type": "UNKNOWN_TOOL", "detail": "x"},
        )
        fb2 = _make_feedback(
            FeedbackSource.PARSER,
            Severity.ERROR,
            {"error_type": "MALFORMED_CALL", "detail": "x"},
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)

    def test_tool_exec_uses_error(self) -> None:
        fb1 = _make_feedback(
            FeedbackSource.TOOL_EXECUTOR,
            Severity.ERROR,
            {"error": "FILE_NOT_FOUND", "success": False},
        )
        fb2 = _make_feedback(
            FeedbackSource.TOOL_EXECUTOR,
            Severity.ERROR,
            {"error": "PERMISSION_DENIED", "success": False},
        )
        assert FingerprintStrategy.generate(fb1) != FingerprintStrategy.generate(fb2)


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------


class TestOutputFormat:
    def test_returns_string(self) -> None:
        fb = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "rm -rf /"}
        )
        result = FingerprintStrategy.generate(fb)
        assert isinstance(result, str)

    def test_fingerprint_is_16_hex_chars(self) -> None:
        fb = _make_feedback(
            FeedbackSource.SHELL, Severity.ERROR, {"command": "rm -rf /"}
        )
        result = FingerprintStrategy.generate(fb)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)
