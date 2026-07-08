"""SPEC §6.14: LLMResponse — standardized response from LLM adapter."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Standardized response returned by the LLM adapter.

    Constraints:
        - When content is None, tool_calls MUST be non-empty (and vice versa).
        - Each element in tool_calls is a dict with id, name, arguments.
    """

    content: str | None
    tool_calls: list[dict] | None
    finish_reason: str
    usage: dict
