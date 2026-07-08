"""SPEC §6.3: ToolResult — result of executing a tool action."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolResult:
    """Result of executing a tool action.

    Constraints:
        - exit_code is only populated for execute_shell actions.
        - error is only populated when success=False.
    """

    success: bool
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    error: str | None
    duration_ms: int
