"""ShellGen — Feedback generator for shell command executions (SPEC §3.6.1)."""

from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity


class ShellGen(FeedbackGenerator):
    """Generates Feedback from shell command execution results.

    raw_data must be a dict with:
        command: str      — the shell command that was executed
        tool_result: ToolResult  — the result of the execution
    """

    def generate(self, raw_data: Any) -> Feedback:
        command: str = raw_data["command"]
        tool_result: Any = raw_data["tool_result"]

        severity = Severity.INFO if tool_result.success else Severity.ERROR

        return _build_feedback(
            source=FeedbackSource.SHELL,
            severity=severity,
            payload={
                "command": command,
                "exit_code": tool_result.exit_code,
                "stdout": tool_result.stdout,
                "stderr": tool_result.stderr,
                "error": tool_result.error,
            },
            duration_ms=tool_result.duration_ms,
        )
