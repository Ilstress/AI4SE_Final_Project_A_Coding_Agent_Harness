"""SPEC §6.10: ExecutionOutcome — union type for Feedback Pipeline input."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionOutcome:
    """Represents any result from the execution pipeline, as unified input to Feedback Pipeline.

    Variants: ToolResult, GuardResult, ParseError.
    Exactly one of the three fields should be non-None.
    """

    tool_result: Any | None = None  # ToolResult | None
    guard_result: Any | None = None  # GuardResult | None
    parse_error: Any | None = None  # ParseError | None
