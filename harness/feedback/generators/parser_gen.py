"""ParserGen — Feedback generator for parse errors (SPEC §3.6.1)."""

from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity

_ERROR_SEVERITY = {
    "UNKNOWN_TOOL": Severity.WARNING,
    "MALFORMED_CALL": Severity.ERROR,
}


class ParserGen(FeedbackGenerator):
    """Generates Feedback from ActionParser parse errors.

    raw_data must be a dict with:
        parse_error: ParseError  — the parse error
    """

    def generate(self, raw_data: Any) -> Feedback:
        parse_error: Any = raw_data["parse_error"]

        severity = _ERROR_SEVERITY.get(
            parse_error.error_type, Severity.ERROR
        )

        return _build_feedback(
            source=FeedbackSource.PARSER,
            severity=severity,
            payload={
                "error_type": parse_error.error_type,
                "detail": parse_error.detail,
                "raw_response": parse_error.raw_response,
            },
            duration_ms=0,
        )
