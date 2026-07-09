"""GuardGen — Feedback generator for Guardrail evaluation results (SPEC §3.6.1)."""

from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity
from harness.models.guard_result import GuardVerdict

_VERDICT_SEVERITY = {
    GuardVerdict.BLOCKED: Severity.CRITICAL,
    GuardVerdict.APPROVAL_REQUIRED: Severity.WARNING,
    GuardVerdict.ALLOWED: Severity.INFO,
}


class GuardGen(FeedbackGenerator):
    """Generates Feedback from Guardrail evaluation results.

    raw_data must be a dict with:
        guard_result: GuardResult  — the result of guardrail evaluation
    """

    def generate(self, raw_data: Any) -> Feedback:
        guard_result: Any = raw_data["guard_result"]

        severity = _VERDICT_SEVERITY.get(
            guard_result.verdict, Severity.CRITICAL
        )

        return _build_feedback(
            source=FeedbackSource.GUARDRAIL,
            severity=severity,
            payload={
                "verdict": guard_result.verdict.value,
                "triggered_rules": [
                    r.rule_name for r in guard_result.rule_results
                ],
            },
            duration_ms=0,
        )
