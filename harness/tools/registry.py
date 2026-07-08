"""SPEC §3.3.1: ToolRegistry — centralized registry of available tools.

Immutable after initialization. Used by ActionParser (tool name validation)
and ToolExecutor (dispatch) and ContextBuilder (tool definitions for LLM).
"""

from harness.models.tool_definition import ToolDefinition
from harness.tools.definitions import _BUILTIN_TOOLS


class ToolRegistry:
    """Immutable registry of available tools.

    Initialized at startup based on ``tools.enabled`` configuration.
    Once created, tools cannot be added or removed.
    """

    def __init__(self, enabled: list[str] | None = None) -> None:
        """Initialize the registry with the given enabled tools.

        Args:
            enabled: List of tool names to enable. If None or not provided,
                     all 4 built-in tools are registered.
        """
        if enabled is None:
            enabled = [
                "read_file",
                "write_file",
                "execute_shell",
                "task_complete",
            ]

        self._tools: dict[str, ToolDefinition] = {}
        for name in enabled:
            definition = _BUILTIN_TOOLS.get(name)
            if definition is not None:
                self._tools[name] = definition

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def is_registered(self, tool_name: str) -> bool:
        """Return True if the tool is registered in this registry."""
        return tool_name in self._tools

    def get_tool(self, tool_name: str) -> ToolDefinition:
        """Return the ToolDefinition for the given tool name.

        Raises:
            KeyError: If the tool is not registered.
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered")
        return self._tools[tool_name]

    def get_all_tools(self) -> list[ToolDefinition]:
        """Return a copy of all registered ToolDefinitions."""
        return list(self._tools.values())
