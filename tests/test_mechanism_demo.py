"""Mechanism Demos — SPEC §9.10, §A.6, PLAN T12.1.

Three deterministic demonstrations of core Harness mechanisms.
All use MockAdapter — no real LLM, no network.
"""

import tempfile

import pytest

from harness.feedback.controllers.governance import GovernanceController
from harness.feedback.controllers.recovery import RecoveryController
from harness.feedback.coordination import CoordinationLayer
from harness.feedback.pipeline import FeedbackPipeline
from harness.guard.approval.mock import MockApprovalProvider
from harness.guard.guardrail import Guardrail
from harness.guard.rule_engine import RuleEngine
from harness.guard.rules.dangerous_shell import DangerousShellRule
from harness.guard.rules.path_boundary import PathBoundaryRule
from harness.llm.mock_adapter import MockAdapter
from harness.loop.main_loop import LoopState, MainLoop
from harness.models.action import Action
from harness.models.config import Config, LLMConfig, LoopConfig, WorkspaceConfig
from harness.models.guard_result import GuardVerdict
from harness.models.llm_response import LLMResponse
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(workspace_root: str) -> Config:
    return Config(
        workspace=WorkspaceConfig(root=workspace_root),
        llm=LLMConfig(provider="mock", model="mock"),
        loop=LoopConfig(max_iterations=10, timeout_seconds=300.0),
    )


def _make_tool_call_response(tool_name: str, arguments: dict) -> LLMResponse:
    return LLMResponse(
        content=None,
        tool_calls=[{"id": "call_1", "name": tool_name, "arguments": arguments}],
        finish_reason="tool_calls",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


def _make_loop(
    llm_responses: list[LLMResponse],
    workspace_root: str,
    rules: list | None = None,
    max_iterations: int = 10,
) -> MainLoop:
    config = _make_config(workspace_root)
    llm = MockAdapter(llm_responses)
    registry = ToolRegistry()
    executor = ToolExecutor(workspace_root=workspace_root, registry=registry)
    rule_engine = RuleEngine(rules or [])
    approval = MockApprovalProvider([])
    guardrail = Guardrail(rule_engine, approval)
    recovery = RecoveryController()
    governance = GovernanceController()
    coordination = CoordinationLayer()
    pipeline = FeedbackPipeline(recovery, governance, coordination)

    return MainLoop(
        config=config,
        llm=llm,
        guardrail=guardrail,
        tool_executor=executor,
        tool_registry=registry,
        feedback_pipeline=pipeline,
    )


# ===================================================================
# Demo 1 — Guardrail deterministically blocks a dangerous action
# ===================================================================


class TestDemo1GuardrailBlock:
    """SPEC §9.10 item 1: Guardrail blocks writing outside the workspace."""

    def test_blocks_write_outside_workspace(self) -> None:
        """Construct Action(write_file, /etc/passwd) → Guardrail → BLOCKED."""
        workspace = tempfile.gettempdir()
        rule_engine = RuleEngine([PathBoundaryRule(workspace)])
        guardrail = Guardrail(rule_engine, MockApprovalProvider([]))

        action = Action(
            tool_name="write_file",
            parameters={"path": "/etc/passwd", "content": "malicious"},
            raw_response={
                "id": "call_1",
                "name": "write_file",
                "arguments": {"path": "/etc/passwd", "content": "malicious"},
            },
        )

        result = guardrail.evaluate(action)
        assert result.verdict == GuardVerdict.BLOCKED

    def test_allows_write_inside_workspace(self) -> None:
        """Sanity check: writing inside workspace is allowed."""
        workspace = tempfile.gettempdir()
        rule_engine = RuleEngine([PathBoundaryRule(workspace)])
        guardrail = Guardrail(rule_engine, MockApprovalProvider([]))

        action = Action(
            tool_name="write_file",
            parameters={"path": f"{workspace}/safe.txt", "content": "ok"},
            raw_response={
                "id": "call_1",
                "name": "write_file",
                "arguments": {"path": f"{workspace}/safe.txt", "content": "ok"},
            },
        )

        result = guardrail.evaluate(action)
        assert result.verdict == GuardVerdict.ALLOWED


# ===================================================================
# Demo 2 — Feedback Loop: test failure → feedback → agent adapts
# ===================================================================


class TestDemo2FeedbackLoop:
    """SPEC §9.10 item 2: Feedback loop detects failure and agent adapts.

    Sequence:
      1. LLM → write_file (make a change)
      2. LLM → execute_shell (run tests → fails with exit_code=1)
      3. LLM → write_file (fix the issue based on feedback)
      4. LLM → task_complete
    """

    @pytest.mark.asyncio
    async def test_agent_recovers_from_shell_failure(self) -> None:
        """Agent writes code, hits a shell failure, then fixes it."""
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("write_file", {"path": f"{workspace}/x.py", "content": "x = 1"}),
            _make_tool_call_response("execute_shell", {"command": "python -c \"exit(1)\""}),
            _make_tool_call_response("write_file", {"path": f"{workspace}/x.py", "content": "x = 2"}),
            _make_tool_call_response("task_complete", {"summary": "Fixed the test failure"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace)
        result = await loop.run("Fix the failing test in x.py")

        # The agent should complete after recovering from the failure
        assert result == LoopState.COMPLETED

    @pytest.mark.asyncio
    async def test_feedback_injected_into_history(self) -> None:
        """Verify the failed shell result is recorded in message history."""
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("execute_shell", {"command": "python -c \"import sys; print('FAILED'); sys.exit(1)\""}),
            _make_tool_call_response("task_complete", {"summary": "Done"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace)
        await loop.run("Run the tests")

        # The tool result message should contain the failure output
        tool_messages = [m for m in loop.message_history if m["role"] == "tool"]
        assert len(tool_messages) >= 1
        # The shell failure should produce stderr or stdout content
        tool_content = tool_messages[0]["content"]
        assert len(tool_content) > 0


# ===================================================================
# Demo 3 — Convergence detection: 3 same errors → FORCE_STOP
# ===================================================================


class TestDemo3ConvergenceDetection:
    """SPEC §9.10 item 3: Repeated errors trigger convergence failure.

    Sequence:
      1. LLM → execute_shell(bad_command) → fails
      2. LLM → execute_shell(bad_command) → fails (same fingerprint)
      3. LLM → execute_shell(bad_command) → fails (same fingerprint)
      4. CoordinationLayer detects convergence → escalation → FAILED
    """

    @pytest.mark.asyncio
    async def test_three_same_errors_triggers_failed(self) -> None:
        """Three identical failing commands → convergence failure → FAILED."""
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("execute_shell", {"command": "bad_command"}),
            _make_tool_call_response("execute_shell", {"command": "bad_command"}),
            _make_tool_call_response("execute_shell", {"command": "bad_command"}),
            _make_tool_call_response("execute_shell", {"command": "bad_command"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace, max_iterations=10)
        result = await loop.run("Run bad_command repeatedly")

        # Convergence should be detected, resulting in FAILED
        assert result == LoopState.FAILED

    @pytest.mark.asyncio
    async def test_different_errors_dont_trigger_convergence(self) -> None:
        """Different commands don't share the same fingerprint → no convergence failure."""
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("execute_shell", {"command": "error_a"}),
            _make_tool_call_response("execute_shell", {"command": "error_b"}),
            _make_tool_call_response("execute_shell", {"command": "error_c"}),
            _make_tool_call_response("task_complete", {"summary": "Done"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace, max_iterations=10)
        result = await loop.run("Run different commands")

        # Different errors → no convergence → completes normally
        assert result == LoopState.COMPLETED


# ===================================================================
# Cross-demo: DangerousShellRule triggers HITL
# ===================================================================


class TestDemoBonusDangerousShell:
    """Bonus: DangerousShellRule flags rm -rf and triggers APPROVAL_REQUIRED."""

    def test_dangerous_shell_flags_approval(self) -> None:
        """rm -rf inside workspace → FLAG → APPROVAL_REQUIRED."""
        workspace = tempfile.gettempdir()
        rule_engine = RuleEngine([DangerousShellRule(workspace)])
        approval = MockApprovalProvider([])
        guardrail = Guardrail(rule_engine, approval)

        action = Action(
            tool_name="execute_shell",
            parameters={"command": "rm -rf ./build/"},
            raw_response={
                "id": "call_1",
                "name": "execute_shell",
                "arguments": {"command": "rm -rf ./build/"},
            },
        )

        result = guardrail.evaluate(action)
        assert result.verdict == GuardVerdict.APPROVAL_REQUIRED
        assert result.approval_request is not None


# ===================================================================
# Demo 4 — End-to-End: full chain with all four tools
# ===================================================================


class TestDemo4EndToEnd:
    """Full Harness chain: ContextBuilder → LLM → Parser → Guardrail →
    ToolExecutor → Feedback → COMPLETED.

    Uses all four built-in tools in a realistic multi-step workflow.
    """

    @pytest.mark.asyncio
    async def test_full_happy_path_all_four_tools(self) -> None:
        """Complete multi-step workflow: read → write → shell → task_complete.

        Each step exercises the full chain:
          ContextBuilder → MockAdapter → ActionParser → Guardrail →
          ToolExecutor → FeedbackPipeline → StopConditions.
        """
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("read_file", {"path": f"{workspace}/app.py"}),
            _make_tool_call_response("write_file", {"path": f"{workspace}/app.py", "content": "print('hello')"}),
            _make_tool_call_response("execute_shell", {"command": "echo 'build ok'"}),
            _make_tool_call_response("task_complete", {"summary": "App created and verified"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace)
        result = await loop.run("Create a simple Python app and verify it builds")

        assert result == LoopState.COMPLETED
        # Four tool calls → four iterations
        assert loop.iteration == 4

    @pytest.mark.asyncio
    async def test_e2e_message_history_contains_all_roles(self) -> None:
        """Verify the message history captures the full conversation."""
        workspace = tempfile.gettempdir()

        responses = [
            _make_tool_call_response("read_file", {"path": f"{workspace}/app.py"}),
            _make_tool_call_response("write_file", {"path": f"{workspace}/app.py", "content": "x = 1"}),
            _make_tool_call_response("task_complete", {"summary": "Done"}),
        ]

        loop = _make_loop(llm_responses=responses, workspace_root=workspace)
        await loop.run("Update app.py")

        roles = {m["role"] for m in loop.message_history}
        assert "user" in roles
        assert "assistant" in roles
        assert "tool" in roles
