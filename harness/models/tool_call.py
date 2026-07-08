"""SPEC §6.2: ToolCall — raw tool call from LLM API response."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCall:
    """LLM-requested tool call as received from the API response.

    This is the raw form before parsing into an Action.
    """

    id: str
    name: str
    arguments: dict
