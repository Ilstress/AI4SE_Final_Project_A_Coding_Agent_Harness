"""ToolExecGen — Feedback generator for tool execution errors (SPEC §3.6.1)."""

from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity


class ToolExecGen(FeedbackGenerator):
    """Generates Feedback from tool execution I/O errors.

    raw_data must be a dict with:
        tool_result: ToolResult  — the result of tool execution
    """

    def generate(self, raw_data: Any) -> Feedback:
        tool_result: Any = raw_data["tool_result"]

        severity = (
            Severity.ERROR if tool_result.error is not None else Severity.INFO
        )

        return _build_feedback(
            source=FeedbackSource.TOOL_EXECUTOR,
            severity=severity,
            payload={
                "error": tool_result.error,
                "success": tool_result.success,
            },
            duration_ms=tool_result.duration_ms,
        )
