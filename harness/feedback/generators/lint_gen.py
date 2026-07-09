"""LintGen — Feedback generator for lint execution results (SPEC §3.6.1)."""

from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity


def _parse_lint_errors(stdout: str, stderr: str) -> list[str]:
    """Extract non-empty lines as lint issues."""
    combined = (stdout + "\n" + stderr).strip()
    if not combined:
        return []
    return [line for line in combined.split("\n") if line.strip()]


class LintGen(FeedbackGenerator):
    """Generates Feedback from flake8/mypy execution results.

    raw_data must be a dict with:
        tool_result: ToolResult  — stdout/stderr contains lint issues
    """

    def generate(self, raw_data: Any) -> Feedback:
        tool_result: Any = raw_data["tool_result"]
        stdout = tool_result.stdout or ""
        stderr = tool_result.stderr or ""

        errors = _parse_lint_errors(stdout, stderr)
        severity = Severity.INFO if len(errors) == 0 else Severity.WARNING

        return _build_feedback(
            source=FeedbackSource.LINT,
            severity=severity,
            payload={
                "errors": errors,
                "stdout": stdout,
                "stderr": stderr,
            },
            duration_ms=tool_result.duration_ms,
        )
