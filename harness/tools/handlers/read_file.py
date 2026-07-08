"""SPEC §3.5: read_file tool handler.

Reads file content from the workspace. All paths are relative to the
workspace root.
"""

import time
from pathlib import Path

from harness.models.tool_result import ToolResult


async def read_file(
    workspace_root: str,
    path: str,
    timeout: float = 10.0,
) -> ToolResult:
    """Read the contents of a file at the given path.

    Args:
        workspace_root: Absolute path to the workspace root directory.
        path: File path relative to the workspace root.
        timeout: Maximum time in seconds for the I/O operation.

    Returns:
        ToolResult with content in stdout on success, or error on failure.
    """
    start = time.monotonic()
    target = Path(workspace_root) / path

    try:
        # Resolve to catch path traversal attempts
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
            error="FILE_NOT_FOUND",
            duration_ms=duration_ms,
        )

    try:
        content = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ToolResult(
            success=False,
            exit_code=None,
            stdout=None,
            stderr=None,
            error="FILE_NOT_FOUND",
            duration_ms=duration_ms,
        )
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
        stdout=content,
        stderr=None,
        error=None,
        duration_ms=duration_ms,
    )
