"""SPEC §6.11: ParseError — failure to parse LLM response into a valid action."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParseError:
    """Represents a failure to parse an LLM response into a valid Action.

    error_type: 'UNKNOWN_TOOL' or 'MALFORMED_CALL'
    raw_response: the raw LLM response that failed to parse
    detail: human-readable parse error detail for injecting into LLM context
    """

    error_type: str
    raw_response: dict
    detail: str
