"""Tests for Tool Handlers (T4.2) and Tool Executor (T4.3).

SPEC §3.5, PLAN T4.2 + T4.3.
"""

from pathlib import Path

import pytest

from harness.models.tool_result import ToolResult
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# read_file Handler
# ---------------------------------------------------------------------------


class TestReadFileHandler:
    async def _read_file(self, workspace: Path, path: str) -> ToolResult:
        from harness.tools.handlers.read_file import read_file

        return await read_file(str(workspace), path)

    @pytest.mark.asyncio
    async def test_reads_existing_file(self, tmp_path: Path) -> None:
        file = tmp_path / "data.txt"
        file.write_text("Hello, World!")

        result = await self._read_file(tmp_path, "data.txt")

        assert result.success is True
        assert result.stdout == "Hello, World!"
        assert result.error is None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path: Path) -> None:
        result = await self._read_file(tmp_path, "nonexistent.txt")

        assert result.success is False
        assert result.error == "FILE_NOT_FOUND"
        assert result.stdout is None

    @pytest.mark.asyncio
    async def test_reads_file_in_subdirectory(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        file = subdir / "nested.txt"
        file.write_text("nested content")

        result = await self._read_file(tmp_path, "sub/nested.txt")

        assert result.success is True
        assert result.stdout == "nested content"


# ---------------------------------------------------------------------------
# write_file Handler
# ---------------------------------------------------------------------------


class TestWriteFileHandler:
    async def _write_file(
        self, workspace: Path, path: str, content: str
    ) -> ToolResult:
        from harness.tools.handlers.write_file import write_file

        return await write_file(str(workspace), path, content)

    @pytest.mark.asyncio
    async def test_writes_new_file(self, tmp_path: Path) -> None:
        result = await self._write_file(tmp_path, "output.txt", "new content")

        assert result.success is True
        assert result.error is None
        assert result.duration_ms >= 0

        written = (tmp_path / "output.txt").read_text()
        assert written == "new content"

    @pytest.mark.asyncio
    async def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        file = tmp_path / "existing.txt"
        file.write_text("old content")

        result = await self._write_file(tmp_path, "existing.txt", "new content")

        assert result.success is True
        assert file.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        result = await self._write_file(
            tmp_path, "deep/nested/file.txt", "deep content"
        )

        assert result.success is True
        written = (tmp_path / "deep" / "nested" / "file.txt").read_text()
        assert written == "deep content"


# ---------------------------------------------------------------------------
# execute_shell Handler
# ---------------------------------------------------------------------------


class TestExecuteShellHandler:
    async def _execute(
        self, workspace: Path, command: str, cwd: str | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        from harness.tools.handlers.execute_shell import execute_shell

        if timeout is not None:
            return await execute_shell(str(workspace), command, cwd=cwd, timeout=timeout)
        return await execute_shell(str(workspace), command, cwd=cwd)

    @pytest.mark.asyncio
    async def test_echo_hello(self, tmp_path: Path) -> None:
        result = await self._execute(tmp_path, "echo hello")

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout is not None
        assert "hello" in result.stdout
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_failing_command(self, tmp_path: Path) -> None:
        # Use a command that exits non-zero
        result = await self._execute(tmp_path, 'python -c "exit(42)"')

        assert result.success is False
        assert result.exit_code == 42

    @pytest.mark.asyncio
    async def test_timeout(self, tmp_path: Path) -> None:
        # Sleep longer than the timeout
        result = await self._execute(
            tmp_path, 'python -c "import time; time.sleep(10)"', timeout=1.0
        )

        assert result.success is False
        assert result.error == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_respects_cwd_parameter(self, tmp_path: Path) -> None:
        subdir = tmp_path / "workdir"
        subdir.mkdir()

        result = await self._execute(
            tmp_path, 'python -c "import os; print(os.getcwd())"', cwd=str(subdir)
        )

        assert result.success is True
        assert result.stdout is not None
        assert str(subdir) in result.stdout

    @pytest.mark.asyncio
    async def test_captures_stderr(self, tmp_path: Path) -> None:
        result = await self._execute(
            tmp_path, "python -c \"import sys; sys.stderr.write('err msg\\n')\""
        )

        assert result.stderr is not None
        assert "err msg" in result.stderr


# ---------------------------------------------------------------------------
# task_complete Handler
# ---------------------------------------------------------------------------


class TestTaskCompleteHandler:
    @pytest.mark.asyncio
    async def test_returns_success(self) -> None:
        from harness.tools.handlers.task_complete import task_complete

        result = await task_complete("All tasks finished successfully.")

        assert result.success is True
        assert result.exit_code is None
        assert result.error is None
        assert result.stdout == "All tasks finished successfully."
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_empty_summary(self) -> None:
        from harness.tools.handlers.task_complete import task_complete

        result = await task_complete("")

        assert result.success is True
        assert result.stdout == ""


# ---------------------------------------------------------------------------
# Tool Executor — Dispatch
# ---------------------------------------------------------------------------


class TestToolExecutor:
    """Verify ToolExecutor dispatches Actions to the correct handlers."""

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        return ToolRegistry()

    @pytest.fixture
    def executor(self, tmp_path: Path, registry: ToolRegistry) -> ToolExecutor:
        return ToolExecutor(str(tmp_path), registry)

    @pytest.mark.asyncio
    async def test_execute_read_file_action(
        self, tmp_path: Path, executor: ToolExecutor
    ) -> None:
        from harness.models.action import Action

        file = tmp_path / "hello.txt"
        file.write_text("Hello from executor")

        action = Action(
            tool_name="read_file",
            parameters={"path": "hello.txt"},
            raw_response={},
        )
        result = await executor.execute(action)

        assert result.success is True
        assert result.stdout == "Hello from executor"

    @pytest.mark.asyncio
    async def test_execute_write_file_action(
        self, tmp_path: Path, executor: ToolExecutor
    ) -> None:
        from harness.models.action import Action

        action = Action(
            tool_name="write_file",
            parameters={"path": "out.txt", "content": "written by executor"},
            raw_response={},
        )
        result = await executor.execute(action)

        assert result.success is True
        written = (tmp_path / "out.txt").read_text()
        assert written == "written by executor"

    @pytest.mark.asyncio
    async def test_execute_shell_action(
        self, tmp_path: Path, executor: ToolExecutor
    ) -> None:
        from harness.models.action import Action

        action = Action(
            tool_name="execute_shell",
            parameters={"command": "echo dispatched"},
            raw_response={},
        )
        result = await executor.execute(action)

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout is not None
        assert "dispatched" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_task_complete_action(
        self, executor: ToolExecutor
    ) -> None:
        from harness.models.action import Action

        action = Action(
            tool_name="task_complete",
            parameters={"summary": "All done"},
            raw_response={},
        )
        result = await executor.execute(action)

        assert result.success is True
        assert result.stdout == "All done"

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_key_error(
        self, executor: ToolExecutor
    ) -> None:
        from harness.models.action import Action

        action = Action(
            tool_name="nonexistent_tool",
            parameters={},
            raw_response={},
        )
        with pytest.raises(KeyError):
            await executor.execute(action)
