"""SPEC §3.1.1: ContextBuilder — assembles LLM message list.

Pure function: no state, no side effects, no modification of inputs.
"""

import json

from harness.models.memory_entry import MemoryEntry
from harness.models.tool_definition import ToolDefinition


def build(
    system_prompt: str,
    tool_definitions: list[ToolDefinition],
    memory_entries: list[MemoryEntry],
    message_history: list[dict],
    user_task: str,
) -> list[dict]:
    """Assemble a complete message list for the LLM.

    Args:
        system_prompt: Fixed behavioural constraint text from the Main Loop.
        tool_definitions: JSON Schema definitions of all registered tools.
        memory_entries: Memory entries retrieved for the current session.
        message_history: All previously exchanged messages in order.
            Dicts from this list are added to the returned list **by reference**
            (not deep-copied).  If the caller later mutates a history dict
            inside the returned list, the original message_history is also
            affected.  This is a performance-conscious design choice —
            build() itself never modifies any input, so the pure-function
            contract is still upheld.
        user_task: The original user task string.

    Returns:
        A list of message dicts in OpenAI-compatible format.
        Does not modify any input arguments.
    """
    messages: list[dict] = []

    # ------------------------------------------------------------------
    # System message: prompt + tools + memory
    # ------------------------------------------------------------------
    system_parts: list[str] = [system_prompt]

    if tool_definitions:
        tools_json = _format_tool_definitions(tool_definitions)
        system_parts.append(f"## Available Tools\n{tools_json}")

    if memory_entries:
        memory_text = _format_memory_entries(memory_entries)
        system_parts.append(f"## Memory\n{memory_text}")

    messages.append({"role": "system", "content": "\n\n".join(system_parts)})

    # ------------------------------------------------------------------
    # Message history
    # ------------------------------------------------------------------
    messages.extend(message_history)

    # ------------------------------------------------------------------
    # User task — appended only in the first round
    # ------------------------------------------------------------------
    if not message_history:
        messages.append({"role": "user", "content": user_task})

    return messages


def _format_tool_definitions(
    tools: list[ToolDefinition],
) -> str:
    """Format tool definitions as a JSON block for the system prompt."""
    formatted = []
    for td in tools:
        formatted.append(
            {
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters,
            }
        )
    return json.dumps(formatted, indent=2, ensure_ascii=False)


def _format_memory_entries(
    entries: list[MemoryEntry],
) -> str:
    """Format memory entries as bullet points for the system prompt."""
    lines = []
    for entry in entries:
        lines.append(f"- [{entry.category}] {entry.content}")
    return "\n".join(lines)
