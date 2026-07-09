"""TestGen — Feedback generator for test execution results (SPEC §3.6.1)."""

import re
from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity

_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")


def _parse_pytest_summary(output: str) -> tuple[int, int, int]:
    """Parse pytest summary line to extract (passed, failed, total)."""
    passed = 0
    failed = 0
    passed_m = _PASSED_RE.search(output)
    failed_m = _FAILED_RE.search(output)
    if passed_m:
        passed = int(passed_m.group(1))
    if failed_m:
        failed = int(failed_m.group(1))
    return passed, failed, passed + failed


class TestGen(FeedbackGenerator):
    """Generates Feedback from pytest execution results.

    raw_data must be a dict with:
        tool_result: ToolResult  — stdout contains pytest summary
    """

    def generate(self, raw_data: Any) -> Feedback:
        tool_result: Any = raw_data["tool_result"]
        stdout = tool_result.stdout or ""

        passed, failed, total = _parse_pytest_summary(stdout)
        severity = Severity.INFO if failed == 0 else Severity.ERROR

        return _build_feedback(
            source=FeedbackSource.TEST,
            severity=severity,
            payload={
                "passed": passed,
                "failed": failed,
                "total": total,
                "stdout": stdout,
                "stderr": tool_result.stderr,
            },
            duration_ms=tool_result.duration_ms,
        )
