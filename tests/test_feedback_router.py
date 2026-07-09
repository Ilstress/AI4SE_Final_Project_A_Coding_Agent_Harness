"""Tests for FeedbackRouter — SPEC §3.6.2, PLAN T8.5."""

import pytest

from harness.feedback.router import FeedbackRouter, Track
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)


def _make_feedback(source: FeedbackSource, severity: Severity) -> Feedback:
    return Feedback(
        fingerprint="",
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
# Recovery track — source-based
# ---------------------------------------------------------------------------


class TestRecoveryTrack:
    """SHELL / TEST / LINT / DIFF / TOOL_EXECUTOR / PARSER → RECOVERY regardless of severity."""

    @pytest.mark.parametrize("source", [
        FeedbackSource.SHELL,
        FeedbackSource.TEST,
        FeedbackSource.LINT,
        FeedbackSource.DIFF,
        FeedbackSource.TOOL_EXECUTOR,
        FeedbackSource.PARSER,
    ])
    @pytest.mark.parametrize("severity", [
        Severity.INFO,
        Severity.WARNING,
        Severity.ERROR,
        Severity.CRITICAL,
    ])
    def test_always_routes_to_recovery(self, source: FeedbackSource, severity: Severity) -> None:
        fb = _make_feedback(source, severity)
        assert FeedbackRouter.route(fb) == Track.RECOVERY


# ---------------------------------------------------------------------------
# GUARDRAIL routing
# ---------------------------------------------------------------------------


class TestGuardrailRouting:
    def test_guardrail_error_goes_to_governance(self) -> None:
        fb = _make_feedback(FeedbackSource.GUARDRAIL, Severity.ERROR)
        assert FeedbackRouter.route(fb) == Track.GOVERNANCE

    def test_guardrail_critical_goes_to_governance(self) -> None:
        fb = _make_feedback(FeedbackSource.GUARDRAIL, Severity.CRITICAL)
        assert FeedbackRouter.route(fb) == Track.GOVERNANCE

    def test_guardrail_info_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.GUARDRAIL, Severity.INFO)
        assert FeedbackRouter.route(fb) == Track.RECOVERY

    def test_guardrail_warning_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.GUARDRAIL, Severity.WARNING)
        assert FeedbackRouter.route(fb) == Track.RECOVERY


# ---------------------------------------------------------------------------
# SYSTEM routing
# ---------------------------------------------------------------------------


class TestSystemRouting:
    def test_system_critical_goes_to_governance(self) -> None:
        fb = _make_feedback(FeedbackSource.SYSTEM, Severity.CRITICAL)
        assert FeedbackRouter.route(fb) == Track.GOVERNANCE

    def test_system_error_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.SYSTEM, Severity.ERROR)
        assert FeedbackRouter.route(fb) == Track.RECOVERY

    def test_system_warning_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.SYSTEM, Severity.WARNING)
        assert FeedbackRouter.route(fb) == Track.RECOVERY

    def test_system_info_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.SYSTEM, Severity.INFO)
        assert FeedbackRouter.route(fb) == Track.RECOVERY


# ---------------------------------------------------------------------------
# MEMORY — default fallback → RECOVERY
# ---------------------------------------------------------------------------


class TestMemoryRouting:
    def test_memory_goes_to_recovery(self) -> None:
        fb = _make_feedback(FeedbackSource.MEMORY, Severity.INFO)
        assert FeedbackRouter.route(fb) == Track.RECOVERY


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


class TestOutputType:
    def test_returns_track_enum(self) -> None:
        fb = _make_feedback(FeedbackSource.SHELL, Severity.ERROR)
        result = FeedbackRouter.route(fb)
        assert isinstance(result, Track)
