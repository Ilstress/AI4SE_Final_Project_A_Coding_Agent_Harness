"""SPEC §3.5: task_complete tool handler.

Signals that the task has been completed successfully. The halt signal
is handled by the Main Loop, not by this handler.
"""

import time

from harness.models.tool_result import ToolResult


async def task_complete(summary: str) -> ToolResult:
    """Return a successful ToolResult with the task summary.

    Args:
        summary: A human-readable summary of what was accomplished.

    Returns:
        ToolResult with success=True and the summary in stdout.
    """
    start = time.monotonic()
    duration_ms = int((time.monotonic() - start) * 1000)
    return ToolResult(
        success=True,
        exit_code=None,
        stdout=summary,
        stderr=None,
        error=None,
        duration_ms=duration_ms,
    )
