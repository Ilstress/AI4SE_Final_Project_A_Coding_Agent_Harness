"""SPEC §3.5: ToolExecutor — dispatches approved Actions to handlers.

The executor is a pure execution engine: it does not evaluate safety,
modify actions, or make decisions. It only executes pre-approved actions.
"""

from harness.models.action import Action
from harness.models.tool_result import ToolResult
from harness.tools.handlers.execute_shell import execute_shell
from harness.tools.handlers.read_file import read_file
from harness.tools.handlers.task_complete import task_complete
from harness.tools.handlers.write_file import write_file
from harness.tools.registry import ToolRegistry


class ToolExecutor:
    """Executes approved Actions by dispatching to the correct handler.

    Does not evaluate safety — all actions must be pre-approved by the
    Guardrail before reaching the executor.
    """

    def __init__(self, workspace_root: str, registry: ToolRegistry) -> None:
        self._workspace_root = workspace_root
        self._registry = registry

    async def execute(self, action: Action) -> ToolResult:
        """Dispatch the action to the appropriate handler.

        Args:
            action: The approved Action to execute.

        Returns:
            ToolResult from the handler.

        Raises:
            KeyError: If the tool name is not registered (should be caught
                by ActionParser before reaching the executor).
        """
        if not self._registry.is_registered(action.tool_name):
            raise KeyError(
                f"Tool '{action.tool_name}' is not registered"
            )

        return await self._dispatch(action)

    async def _dispatch(self, action: Action) -> ToolResult:
        """Route to the correct handler based on tool_name."""
        name = action.tool_name
        params = action.parameters
        ws = self._workspace_root

        if name == "read_file":
            return await read_file(ws, params["path"])
        if name == "write_file":
            return await write_file(ws, params["path"], params["content"])
        if name == "execute_shell":
            return await execute_shell(
                ws, params["command"], cwd=params.get("cwd")
            )
        if name == "task_complete":
            return await task_complete(params["summary"])

        raise KeyError(f"Tool '{name}' is not registered")
