"""SPEC §3.5: execute_shell tool handler.

Executes a shell command in the workspace and returns exit_code, stdout,
and stderr.
"""

import asyncio
import time

from harness.models.tool_result import ToolResult

_DEFAULT_TIMEOUT = 60.0


async def execute_shell(
    workspace_root: str,
    command: str,
    cwd: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> ToolResult:
    """Execute a shell command and return its output.

    Args:
        workspace_root: Absolute path to the workspace root directory.
        command: The shell command to execute.
        cwd: Working directory for the command. Defaults to workspace_root.
        timeout: Maximum time in seconds for the command to run.

    Returns:
        ToolResult with exit_code, stdout, stderr, and duration_ms.
    """
    start = time.monotonic()
    working_dir = cwd if cwd is not None else workspace_root

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                success=False,
                exit_code=None,
                stdout=None,
                stderr=None,
                error="TIMEOUT",
                duration_ms=duration_ms,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        exit_code = process.returncode
        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

        return ToolResult(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            error=None,
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
