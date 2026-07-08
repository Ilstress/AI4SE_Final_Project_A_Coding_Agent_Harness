"""Tests for ContextBuilder — SPEC §3.1.1, PLAN T6.1."""

from harness.models.memory_entry import MemoryEntry
from harness.models.tool_definition import ToolDefinition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build(
    system_prompt: str = "You are a coding agent.",
    tool_definitions: list[ToolDefinition] | None = None,
    memory_entries: list[MemoryEntry] | None = None,
    message_history: list[dict] | None = None,
    user_task: str = "Write a test.",
) -> list[dict]:
    from harness.context.context_builder import build

    return build(
        system_prompt=system_prompt,
        tool_definitions=tool_definitions or [],
        memory_entries=memory_entries or [],
        message_history=message_history or [],
        user_task=user_task,
    )


def _make_tool(name: str) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Description of {name}",
        parameters={"type": "object", "properties": {}, "required": []},
    )


def _make_memory(content: str, id_str: str = "m1") -> MemoryEntry:
    return MemoryEntry(
        id=id_str,
        category="DECISION",
        content=content,
        created_at=1234567890.0,
        source_round=0,
    )


# ---------------------------------------------------------------------------
# First Round
# ---------------------------------------------------------------------------


class TestFirstRound:
    def test_first_round_includes_user_task(self) -> None:
        result = _build(message_history=[], user_task="Implement X")

        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == "Implement X"

    def test_first_round_has_system_message(self) -> None:
        result = _build(message_history=[], user_task="Task")

        assert result[0]["role"] == "system"

    def test_first_round_message_count(self) -> None:
        result = _build(
            message_history=[],
            user_task="Task",
            tool_definitions=[_make_tool("read_file")],
            memory_entries=[_make_memory("Use snake_case")],
        )

        # system + user_task = 2 messages
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Non-First Round
# ---------------------------------------------------------------------------


class TestNonFirstRound:
    def test_non_first_round_does_not_append_user_task(self) -> None:
        history = [
            {"role": "user", "content": "Implement X"},
            {"role": "assistant", "content": "I'll do that."},
        ]

        result = _build(message_history=history, user_task="Implement X")

        assert len(result) == 3  # system + 2 history messages
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    def test_non_first_round_preserves_history_order(self) -> None:
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
        ]

        result = _build(message_history=history, user_task="Irrelevant")

        # system + 3 history
        assert result[1:] == history


# ---------------------------------------------------------------------------
# Memory Entries
# ---------------------------------------------------------------------------


class TestMemoryEntries:
    def test_memory_appended_to_system_message(self) -> None:
        mem = _make_memory("Use 4-space indentation")

        result = _build(memory_entries=[mem])

        system_content = result[0]["content"]
        assert "Use 4-space indentation" in system_content

    def test_multiple_memory_entries(self) -> None:
        mem1 = _make_memory("Prefer pytest", id_str="m1")
        mem2 = _make_memory("Use type hints", id_str="m2")

        result = _build(memory_entries=[mem1, mem2])

        system_content = result[0]["content"]
        assert "Prefer pytest" in system_content
        assert "Use type hints" in system_content

    def test_empty_memory_entries(self) -> None:
        result = _build(memory_entries=[])

        system_content = result[0]["content"]
        assert "You are a coding agent." in system_content


# ---------------------------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    def test_tool_definitions_in_system_message(self) -> None:
        td = _make_tool("read_file")

        result = _build(tool_definitions=[td])

        system_content = result[0]["content"]
        assert "read_file" in system_content
        assert "Description of read_file" in system_content

    def test_multiple_tool_definitions(self) -> None:
        td1 = _make_tool("read_file")
        td2 = _make_tool("write_file")

        result = _build(tool_definitions=[td1, td2])

        system_content = result[0]["content"]
        assert "read_file" in system_content
        assert "write_file" in system_content

    def test_empty_tool_definitions(self) -> None:
        result = _build(tool_definitions=[])

        system_content = result[0]["content"]
        assert "You are a coding agent." in system_content


# ---------------------------------------------------------------------------
# Pure Function
# ---------------------------------------------------------------------------


class TestPureFunction:
    def test_does_not_modify_message_history(self) -> None:
        history = [{"role": "user", "content": "Original"}]
        original = list(history)

        _build(message_history=history)

        assert history == original

    def test_does_not_modify_tool_definitions(self) -> None:
        td = _make_tool("read_file")
        original_name = td.name

        _build(tool_definitions=[td])

        assert td.name == original_name

    def test_does_not_modify_memory_entries(self) -> None:
        mem = _make_memory("Original content")
        original_content = mem.content

        _build(memory_entries=[mem])

        assert mem.content == original_content

    def test_consecutive_calls_return_independent_lists(self) -> None:
        result1 = _build(user_task="Task 1")
        result2 = _build(user_task="Task 2")

        assert result1 is not result2
        assert result1[-1]["content"] == "Task 1"
        assert result2[-1]["content"] == "Task 2"
