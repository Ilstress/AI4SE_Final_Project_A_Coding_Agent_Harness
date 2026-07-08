"""Tests for ToolRegistry — SPEC §3.3.1, PLAN T4.1."""

import pytest

from harness.models.tool_definition import ToolDefinition
from harness.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# ToolRegistry — Construction & Default Registration
# ---------------------------------------------------------------------------


class TestToolRegistryConstruction:
    """Verify ToolRegistry initializes with correct built-in tools."""

    def test_default_registers_all_four_tools(self) -> None:
        """All 4 built-in tools should be registered by default."""
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry()

        assert registry.is_registered("read_file")
        assert registry.is_registered("write_file")
        assert registry.is_registered("execute_shell")
        assert registry.is_registered("task_complete")
        assert len(registry.get_all_tools()) == 4

    def test_empty_enabled_list_registers_none(self) -> None:
        """Empty enabled list should register 0 tools."""
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry(enabled=[])

        assert len(registry.get_all_tools()) == 0

    def test_subset_enabled_registers_only_those(self) -> None:
        """Only tools in the enabled list should be registered."""
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry(enabled=["read_file", "execute_shell"])

        assert registry.is_registered("read_file")
        assert not registry.is_registered("write_file")
        assert registry.is_registered("execute_shell")
        assert not registry.is_registered("task_complete")
        assert len(registry.get_all_tools()) == 2

    def test_unknown_tool_in_enabled_is_ignored(self) -> None:
        """Tools not in built-in definitions are silently ignored."""
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry(enabled=["read_file", "nonexistent_tool"])

        assert registry.is_registered("read_file")
        assert not registry.is_registered("nonexistent_tool")
        assert len(registry.get_all_tools()) == 1


# ---------------------------------------------------------------------------
# ToolRegistry — Query Methods
# ---------------------------------------------------------------------------


class TestToolRegistryQueries:
    """Verify is_registered, get_tool, get_all_tools."""

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        return ToolRegistry()

    def test_is_registered_true(self, registry: ToolRegistry) -> None:
        assert registry.is_registered("read_file") is True

    def test_is_registered_false(self, registry: ToolRegistry) -> None:
        assert registry.is_registered("nonexistent") is False

    def test_get_tool_returns_tool_definition(self, registry: ToolRegistry) -> None:
        td = registry.get_tool("read_file")

        assert isinstance(td, ToolDefinition)
        assert td.name == "read_file"
        assert isinstance(td.description, str)
        assert len(td.description) > 0
        assert isinstance(td.parameters, dict)
        assert td.parameters["type"] == "object"

    def test_get_tool_unknown_raises_key_error(self, registry: ToolRegistry) -> None:
        with pytest.raises(KeyError):
            registry.get_tool("nonexistent")

    def test_get_all_tools_returns_list_of_tool_definitions(self, registry: ToolRegistry) -> None:
        tools = registry.get_all_tools()

        assert isinstance(tools, list)
        assert len(tools) == 4
        assert all(isinstance(td, ToolDefinition) for td in tools)

    def test_get_all_tools_returns_copy_not_internal(self, registry: ToolRegistry) -> None:
        tools1 = registry.get_all_tools()
        tools2 = registry.get_all_tools()

        assert tools1 == tools2
        assert tools1 is not tools2


# ---------------------------------------------------------------------------
# ToolRegistry — Immutability
# ---------------------------------------------------------------------------


class TestToolRegistryImmutability:
    """Registry must be immutable after initialization."""

    def test_no_add_method(self) -> None:
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert not hasattr(registry, "register")
        assert not hasattr(registry, "add_tool")

    def test_no_remove_method(self) -> None:
        from harness.tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert not hasattr(registry, "unregister")
        assert not hasattr(registry, "remove_tool")


# ---------------------------------------------------------------------------
# Built-in Tool Definitions
# ---------------------------------------------------------------------------


class TestBuiltinToolDefinitions:
    """Verify each built-in tool has correct JSON Schema definition."""

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        return ToolRegistry()

    def test_read_file_schema(self, registry: ToolRegistry) -> None:
        td = registry.get_tool("read_file")
        assert td.name == "read_file"
        assert "path" in td.parameters.get("properties", {})
        assert "path" in td.parameters.get("required", [])

    def test_write_file_schema(self, registry: ToolRegistry) -> None:
        td = registry.get_tool("write_file")
        assert td.name == "write_file"
        props = td.parameters.get("properties", {})
        assert "path" in props
        assert "content" in props
        required = td.parameters.get("required", [])
        assert "path" in required
        assert "content" in required

    def test_execute_shell_schema(self, registry: ToolRegistry) -> None:
        td = registry.get_tool("execute_shell")
        assert td.name == "execute_shell"
        props = td.parameters.get("properties", {})
        assert "command" in props
        assert "cwd" in props
        assert "command" in td.parameters.get("required", [])

    def test_task_complete_schema(self, registry: ToolRegistry) -> None:
        td = registry.get_tool("task_complete")
        assert td.name == "task_complete"
        props = td.parameters.get("properties", {})
        assert "summary" in props
        assert "summary" in td.parameters.get("required", [])
