"""SPEC §3.5: write_file tool handler.

Writes content to a file in the workspace. All paths are relative to the
workspace root.
"""

import time
from pathlib import Path

from harness.models.tool_result import ToolResult


async def write_file(
    workspace_root: str,
    path: str,
    content: str,
    timeout: float = 10.0,
) -> ToolResult:
    """Write content to a file at the given path.

    Creates parent directories if they do not exist.

    Args:
        workspace_root: Absolute path to the workspace root directory.
        path: File path relative to the workspace root.
        content: Content to write to the file.
        timeout: Maximum time in seconds for the I/O operation.

    Returns:
        ToolResult indicating success or failure.
    """
    start = time.monotonic()
    target = Path(workspace_root) / path

    # Resolve to catch path traversal attempts
    try:
        resolved = target.resolve()
        workspace = Path(workspace_root).resolve()
        if not str(resolved).startswith(str(workspace)):
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                success=False,
                exit_code=None,
                stdout=None,
                stderr=None,
                error="PERMISSION_DENIED",
                duration_ms=duration_ms,
            )
    except OSError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ToolResult(
            success=False,
            exit_code=None,
            stdout=None,
            stderr=None,
            error="PERMISSION_DENIED",
            duration_ms=duration_ms,
        )

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except PermissionError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ToolResult(
            success=False,
            exit_code=None,
            stdout=None,
            stderr=None,
            error="PERMISSION_DENIED",
            duration_ms=duration_ms,
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    return ToolResult(
        success=True,
        exit_code=None,
        stdout=None,
        stderr=None,
        error=None,
        duration_ms=duration_ms,
    )
