"""FeedbackRouter — stateless feedback routing (SPEC §3.6.2, PLAN T8.5)."""

from enum import Enum

from harness.models.feedback import Feedback, FeedbackSource, Severity


class Track(Enum):
    """Routing destination for a Feedback event."""

    RECOVERY = "RECOVERY"
    GOVERNANCE = "GOVERNANCE"


class FeedbackRouter:
    """Stateless router that assigns Feedback to a Track based on source + severity.

    Pure function — no mutable state, no side effects.
    """

    @staticmethod
    def route(feedback: Feedback) -> Track:
        source = feedback.source
        severity = feedback.severity

        # GUARDRAIL + (ERROR|CRITICAL) → GOVERNANCE
        if source == FeedbackSource.GUARDRAIL and severity in (
            Severity.ERROR,
            Severity.CRITICAL,
        ):
            return Track.GOVERNANCE

        # GUARDRAIL + (INFO|WARNING) → RECOVERY (audit only)
        if source == FeedbackSource.GUARDRAIL:
            return Track.RECOVERY

        # SYSTEM + CRITICAL → GOVERNANCE
        if source == FeedbackSource.SYSTEM and severity == Severity.CRITICAL:
            return Track.GOVERNANCE

        # SYSTEM + other → RECOVERY
        if source == FeedbackSource.SYSTEM:
            return Track.RECOVERY

        # Everything else → RECOVERY
        # (SHELL, TEST, LINT, DIFF, TOOL_EXECUTOR, PARSER, MEMORY, PERMISSION)
        return Track.RECOVERY
