"""SPEC §6.1: Action — parsed tool call the agent intends to execute."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Action:
    """Represents a parsed tool call that the agent intends to execute.

    Constraints:
        - tool_name must be registered in ToolRegistry at parse time.
        - parameters must contain all required fields for the specified tool.
    """

    tool_name: str
    parameters: dict[str, Any]
    raw_response: dict
