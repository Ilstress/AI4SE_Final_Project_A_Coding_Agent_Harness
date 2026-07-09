"""DiffGen — Feedback generator for git diff execution results (SPEC §3.6.1)."""

import re
from typing import Any

from harness.feedback.generators._helpers import _build_feedback
from harness.feedback.generators.base import FeedbackGenerator
from harness.models.feedback import Feedback, FeedbackSource, Severity

_SHORTSTAT_RE = re.compile(
    r"(\d+)\s+files?\s+changed"
    r"(?:,\s*(\d+)\s+insertions?\(\+\))?"
    r"(?:,\s*(\d+)\s+deletions?\(\-\))?"
)


def _parse_diff_stats(output: str) -> tuple[int, int, int]:
    """Parse git diff --shortstat to extract (files, additions, deletions)."""
    m = _SHORTSTAT_RE.search(output)
    if not m:
        return 0, 0, 0
    files = int(m.group(1))
    additions = int(m.group(2)) if m.group(2) else 0
    deletions = int(m.group(3)) if m.group(3) else 0
    return files, additions, deletions


class DiffGen(FeedbackGenerator):
    """Generates Feedback from git diff execution results.

    raw_data must be a dict with:
        tool_result: ToolResult  — stdout contains diff / shortstat
    """

    def generate(self, raw_data: Any) -> Feedback:
        tool_result: Any = raw_data["tool_result"]
        stdout = tool_result.stdout or ""

        files_changed, additions, deletions = _parse_diff_stats(stdout)

        return _build_feedback(
            source=FeedbackSource.DIFF,
            severity=Severity.INFO,
            payload={
                "patch": stdout,
                "files_changed": files_changed,
                "additions": additions,
                "deletions": deletions,
            },
            duration_ms=tool_result.duration_ms,
        )
