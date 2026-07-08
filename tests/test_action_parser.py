"""Tests for ActionParser — SPEC §3.3, PLAN T5.1."""


from harness.models.action import Action
from harness.models.llm_response import LLMResponse
from harness.models.parse_error import ParseError
from harness.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(
    llm_response: LLMResponse, registry: ToolRegistry | None = None
) -> str | Action | ParseError | list[Action | ParseError]:
    from harness.parser.action_parser import parse

    if registry is None:
        registry = ToolRegistry()
    return parse(llm_response, registry)


# ---------------------------------------------------------------------------
# TextOnly
# ---------------------------------------------------------------------------


class TestTextOnly:
    def test_content_without_tool_calls_returns_string(self) -> None:
        response = LLMResponse(
            content="Just thinking...",
            tool_calls=None,
            finish_reason="stop",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, str)
        assert result == "Just thinking..."

    def test_content_with_empty_tool_calls_returns_string(self) -> None:
        response = LLMResponse(
            content="Still thinking...",
            tool_calls=[],
            finish_reason="stop",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, str)
        assert result == "Still thinking..."


# ---------------------------------------------------------------------------
# ToolCall(known)
# ---------------------------------------------------------------------------


class TestToolCallKnown:
    def test_registered_tool_returns_action(self) -> None:
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "read_file",
                    "arguments": {"path": "src/main.py"},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, Action)
        assert result.tool_name == "read_file"
        assert result.parameters == {"path": "src/main.py"}

    def test_task_complete_is_known_tool(self) -> None:
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_2",
                    "name": "task_complete",
                    "arguments": {"summary": "Done"},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, Action)
        assert result.tool_name == "task_complete"

    def test_arguments_as_json_string(self) -> None:
        """Arguments may arrive as a JSON string instead of a dict."""
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_3",
                    "name": "write_file",
                    "arguments": '{"path": "out.txt", "content": "hello"}',
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, Action)
        assert result.parameters == {"path": "out.txt", "content": "hello"}

    def test_tool_calls_override_content(self) -> None:
        """When both content and tool_calls are present, tool_calls wins."""
        response = LLMResponse(
            content="I will read the file",
            tool_calls=[
                {
                    "id": "call_4",
                    "name": "read_file",
                    "arguments": {"path": "test.py"},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, Action)


# ---------------------------------------------------------------------------
# ToolCall(unknown)
# ---------------------------------------------------------------------------


class TestToolCallUnknown:
    def test_unregistered_tool_returns_parse_error(self) -> None:
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_5",
                    "name": "delete_all_files",
                    "arguments": {},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, ParseError)
        assert result.error_type == "UNKNOWN_TOOL"
        assert "delete_all_files" in result.detail


# ---------------------------------------------------------------------------
# Malformed
# ---------------------------------------------------------------------------


class TestMalformed:
    def test_empty_response_returns_parse_error(self) -> None:
        response = LLMResponse(
            content=None,
            tool_calls=None,
            finish_reason="stop",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, ParseError)
        assert result.error_type == "MALFORMED_CALL"

    def test_invalid_json_arguments_returns_parse_error(self) -> None:
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_6",
                    "name": "read_file",
                    "arguments": "not valid json {{{",
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, ParseError)
        assert result.error_type == "MALFORMED_CALL"

    def test_missing_required_parameter_returns_parse_error(self) -> None:
        """read_file requires 'path' — missing it should be MALFORMED_CALL."""
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_7",
                    "name": "read_file",
                    "arguments": {},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response)

        assert isinstance(result, ParseError)
        assert result.error_type == "MALFORMED_CALL"
        assert "path" in result.detail.lower()


# ---------------------------------------------------------------------------
# Tool Registry Integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_disabled_tool_becomes_unknown(self) -> None:
        """When a tool is disabled in config, it becomes ToolCall(unknown)."""
        registry = ToolRegistry(enabled=["read_file", "execute_shell"])

        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_8",
                    "name": "write_file",
                    "arguments": {"path": "x", "content": "y"},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response, registry=registry)

        assert isinstance(result, ParseError)
        assert result.error_type == "UNKNOWN_TOOL"

    def test_enabled_tool_still_known(self) -> None:
        registry = ToolRegistry(enabled=["read_file"])

        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "call_9",
                    "name": "read_file",
                    "arguments": {"path": "x"},
                }
            ],
            finish_reason="tool_calls",
            usage={},
        )

        result = _parse(response, registry=registry)

        assert isinstance(result, Action)


# ---------------------------------------------------------------------------
# Multiple Tool Calls
# ---------------------------------------------------------------------------


class TestMultipleToolCalls:
    def test_each_tool_call_classified_independently(self) -> None:
        """Multiple tool_calls are each independently classified."""
        response = LLMResponse(
            content=None,
            tool_calls=[
                {
                    "id": "c1",
                    "name": "read_file",
                    "arguments": {"path": "a.py"},
                },
                {
                    "id": "c2",
                    "name": "unknown_tool",
                    "arguments": {},
                },
                {
                    "id": "c3",
                    "name": "write_file",
                    "arguments": "bad json {{{",
                },
            ],
            finish_reason="tool_calls",
            usage={},
        )

        # Parse should process all tool_calls
        result = _parse(response)

        # Should return a list when multiple tool_calls present
        assert isinstance(result, list)
        assert len(result) == 3

        assert isinstance(result[0], Action)
        assert result[0].tool_name == "read_file"

        assert isinstance(result[1], ParseError)
        assert result[1].error_type == "UNKNOWN_TOOL"

        assert isinstance(result[2], ParseError)
        assert result[2].error_type == "MALFORMED_CALL"
