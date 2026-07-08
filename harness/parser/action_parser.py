"""SPEC §3.3: ActionParser — classifies LLM responses into four categories.

Pure function: no side effects, no state.
"""

import json

from harness.models.action import Action
from harness.models.llm_response import LLMResponse
from harness.models.parse_error import ParseError
from harness.tools.registry import ToolRegistry


def parse(
    llm_response: LLMResponse,
    registry: ToolRegistry,
) -> str | Action | ParseError | list[Action | ParseError]:
    """Classify an LLM response into TextOnly, ToolCall(known),
    ToolCall(unknown), or Malformed.

    Args:
        llm_response: The standardized LLM response to classify.
        registry: The tool registry for validating tool names and
            required parameters.

    Returns:
        - str: TextOnly — the content string to append to message history.
        - Action: ToolCall(known) — a valid parsed action.
        - ParseError: ToolCall(unknown) or Malformed.
        - list[Action | ParseError]: Multiple tool calls, each independently
          classified.
    """
    tool_calls = llm_response.tool_calls or []

    # ------------------------------------------------------------------
    # TextOnly: content present, no tool_calls
    # ------------------------------------------------------------------
    if not tool_calls:
        if llm_response.content is not None:
            return llm_response.content

        # Empty response: no content, no tool_calls
        return ParseError(
            error_type="MALFORMED_CALL",
            raw_response={
                "content": llm_response.content,
                "tool_calls": llm_response.tool_calls,
                "finish_reason": llm_response.finish_reason,
            },
            detail="Empty response: no content and no tool_calls.",
        )

    # ------------------------------------------------------------------
    # Has tool_calls — classify each one
    # ------------------------------------------------------------------
    results: list[Action | ParseError] = []
    for tc in tool_calls:
        results.append(_classify_tool_call(tc, registry))

    if len(results) == 1:
        return results[0]
    return results


def _classify_tool_call(
    tc: dict,
    registry: ToolRegistry,
) -> Action | ParseError:
    """Classify a single tool_call dict."""
    tool_name = tc.get("name", "")

    # ------------------------------------------------------------------
    # ToolCall(unknown)
    # ------------------------------------------------------------------
    if not registry.is_registered(tool_name):
        return ParseError(
            error_type="UNKNOWN_TOOL",
            raw_response=tc,
            detail=f"Tool '{tool_name}' is not registered.",
        )

    # ------------------------------------------------------------------
    # Parse arguments
    # ------------------------------------------------------------------
    raw_args = tc.get("arguments", {})
    if isinstance(raw_args, str):
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError as e:
            return ParseError(
                error_type="MALFORMED_CALL",
                raw_response=tc,
                detail=f"Failed to parse tool call arguments as JSON: {e}",
            )
    elif isinstance(raw_args, dict):
        arguments = raw_args
    else:
        return ParseError(
            error_type="MALFORMED_CALL",
            raw_response=tc,
            detail="Tool call arguments must be a JSON string or dict.",
        )

    if not isinstance(arguments, dict):
        return ParseError(
            error_type="MALFORMED_CALL",
            raw_response=tc,
            detail="Parsed arguments must be a JSON object.",
        )

    # ------------------------------------------------------------------
    # Validate required parameters
    # ------------------------------------------------------------------
    definition = registry.get_tool(tool_name)
    required: list[str] = definition.parameters.get("required", [])
    for param in required:
        if param not in arguments:
            return ParseError(
                error_type="MALFORMED_CALL",
                raw_response=tc,
                detail=f"Missing required parameter '{param}' for tool '{tool_name}'.",
            )

    # ------------------------------------------------------------------
    # ToolCall(known)
    # ------------------------------------------------------------------
    return Action(
        tool_name=tool_name,
        parameters=arguments,
        raw_response=tc,
    )
