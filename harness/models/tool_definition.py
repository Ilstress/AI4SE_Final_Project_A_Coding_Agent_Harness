"""SPEC §6.15: ToolDefinition — JSON Schema definition of a tool."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    """JSON Schema definition of a tool for LLM function calling.

    Constraints:
        - parameters must conform to JSON Schema specification.
        - Each registered tool has a unique ToolDefinition in ToolRegistry.
    """

    name: str
    description: str
    parameters: dict
