"""Tests for MainLoop — SPEC §3.1, PLAN T10.1."""

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
from harness.llm.mock_adapter import MockAdapter
from harness.loop.main_loop import LoopState, MainLoop
from harness.models.approval import ApprovalOutcome, ApprovalResult
from harness.models.config import Config, LLMConfig, LoopConfig, WorkspaceConfig
from harness.models.llm_response import LLMResponse
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    workspace_root: str | None = None,
    max_iterations: int = 10,
    timeout_seconds: float = 300.0,
) -> Config:
    if workspace_root is None:
        workspace_root = tempfile.gettempdir()
    return Config(
        workspace=WorkspaceConfig(root=workspace_root),
        llm=LLMConfig(provider="mock", model="mock"),
        loop=LoopConfig(max_iterations=max_iterations, timeout_seconds=timeout_seconds),
    )


def _make_tool_call_response(
    tool_name: str,
    arguments: dict,
) -> LLMResponse:
    return LLMResponse(
        content=None,
        tool_calls=[
            {
                "id": "call_1",
                "name": tool_name,
                "arguments": arguments,
            }
        ],
        finish_reason="tool_calls",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


def _make_text_only_response(text: str = "Thinking...") -> LLMResponse:
    return LLMResponse(
        content=text,
        tool_calls=None,
        finish_reason="stop",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


def _make_loop(
    llm_responses: list[LLMResponse] | None = None,
    approval_responses: list[ApprovalResult] | None = None,
    rules: list | None = None,
    max_iterations: int = 10,
    timeout_seconds: float = 300.0,
    workspace_root: str | None = None,
) -> MainLoop:
    """Create a MainLoop with all dependencies for testing."""
    if workspace_root is None:
        workspace_root = tempfile.gettempdir()

    config = _make_config(
        workspace_root=workspace_root,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )

    llm = MockAdapter(llm_responses or [])

    registry = ToolRegistry()
    executor = ToolExecutor(workspace_root=workspace_root, registry=registry)

    rule_engine = RuleEngine(rules or [])
    approval = MockApprovalProvider(approval_responses or [])
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


# ---------------------------------------------------------------------------
# Normal flow
# ---------------------------------------------------------------------------


class TestNormalFlow:
    @pytest.mark.asyncio
    async def test_task_complete_returns_completed(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("task_complete", {"summary": "All done"}),
            ],
        )
        result = await loop.run("Complete the task")
        assert result == LoopState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_returns_loop_state(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("task_complete", {"summary": "Done"}),
            ],
        )
        result = await loop.run("Do something")
        assert isinstance(result, LoopState)

    @pytest.mark.asyncio
    async def test_initial_state_is_start(self) -> None:
        loop = _make_loop()
        assert loop.state == LoopState.START


# ---------------------------------------------------------------------------
# Iteration limit
# ---------------------------------------------------------------------------


class TestIterationLimit:
    @pytest.mark.asyncio
    async def test_max_iterations_exceeded_returns_failed(self) -> None:
        # Mock always returns TextOnly — never completes
        responses = [_make_text_only_response("Thinking...") for _ in range(15)]
        loop = _make_loop(
            llm_responses=responses,
            max_iterations=3,
        )
        result = await loop.run("Do something")
        assert result == LoopState.FAILED

    @pytest.mark.asyncio
    async def test_iteration_count_matches(self) -> None:
        responses = [_make_text_only_response("Thinking...") for _ in range(5)]
        loop = _make_loop(
            llm_responses=responses,
            max_iterations=3,
        )
        await loop.run("Do something")
        assert loop.iteration == 3  # stopped at max_iterations


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_returns_failed(self) -> None:
        # Use a very small timeout (1 microsecond) so the loop overhead
        # alone exceeds it, triggering a genuine timeout.
        responses = [_make_text_only_response("Thinking...") for _ in range(100)]
        loop = _make_loop(
            llm_responses=responses,
            max_iterations=100,
            timeout_seconds=0.000001,
        )
        result = await loop.run("Do something")
        assert result == LoopState.FAILED
        # Verify it was the timeout that stopped the loop, not mock exhaustion
        assert loop.iteration < 100


# ---------------------------------------------------------------------------
# HITL flow
# ---------------------------------------------------------------------------


class TestHitlFlow:
    @pytest.mark.asyncio
    async def test_approval_required_then_approved_completes(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("execute_shell", {"command": "rm -rf /"}),
                _make_tool_call_response("task_complete", {"summary": "Done"}),
            ],
            approval_responses=[
                ApprovalResult(ApprovalOutcome.APPROVED),
            ],
            rules=[DangerousShellRule("/tmp")],
        )
        result = await loop.run("Do something dangerous")
        assert result == LoopState.COMPLETED

    @pytest.mark.asyncio
    async def test_approval_required_then_rejected_returns_cancelled(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("execute_shell", {"command": "rm -rf /"}),
            ],
            approval_responses=[
                ApprovalResult(ApprovalOutcome.REJECTED),
            ],
            rules=[DangerousShellRule("/tmp")],
        )
        result = await loop.run("Do something dangerous")
        assert result == LoopState.CANCELLED

    @pytest.mark.asyncio
    async def test_approval_required_then_timeout_returns_failed(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("execute_shell", {"command": "rm -rf /"}),
            ],
            approval_responses=[
                ApprovalResult(ApprovalOutcome.TIMEOUT),
            ],
            rules=[DangerousShellRule("/tmp")],
        )
        result = await loop.run("Do something dangerous")
        assert result == LoopState.FAILED


# ---------------------------------------------------------------------------
# Convergence failure
# ---------------------------------------------------------------------------


class TestConvergenceFailure:
    @pytest.mark.asyncio
    async def test_three_same_errors_triggers_convergence_failure(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("execute_shell", {"command": "bad_command"}),
                _make_tool_call_response("execute_shell", {"command": "bad_command"}),
                _make_tool_call_response("execute_shell", {"command": "bad_command"}),
                _make_tool_call_response("execute_shell", {"command": "bad_command"}),
            ],
            max_iterations=10,
        )
        result = await loop.run("Do something")
        # Convergence should be detected, resulting in FAILED
        assert result == LoopState.FAILED


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_mock_responses_returns_failed(self) -> None:
        loop = _make_loop(llm_responses=[])
        result = await loop.run("Do something")
        assert result == LoopState.FAILED


# ---------------------------------------------------------------------------
# Message history
# ---------------------------------------------------------------------------


class TestMessageHistory:
    @pytest.mark.asyncio
    async def test_message_history_starts_empty(self) -> None:
        loop = _make_loop()
        assert loop.message_history == []

    @pytest.mark.asyncio
    async def test_message_history_includes_user_task(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("task_complete", {"summary": "Done"}),
            ],
        )
        await loop.run("Write a function")
        # The first message should be the user task
        assert len(loop.message_history) > 0
        user_messages = [m for m in loop.message_history if m["role"] == "user"]
        assert len(user_messages) >= 1

    @pytest.mark.asyncio
    async def test_text_only_appended_to_history(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_text_only_response("I'll think about this..."),
                _make_tool_call_response("task_complete", {"summary": "Done"}),
            ],
        )
        await loop.run("Write a function")
        assistant_messages = [m for m in loop.message_history if m["role"] == "assistant"]
        assert len(assistant_messages) >= 1


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    @pytest.mark.asyncio
    async def test_transition_table_has_eight_entries(self) -> None:
        from harness.loop.main_loop import _TRANSITIONS

        assert len(_TRANSITIONS) == 8

    @pytest.mark.asyncio
    async def test_start_to_running(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("task_complete", {"summary": "Done"}),
            ],
        )
        assert loop.state == LoopState.START
        await loop.run("task")
        assert loop.state == LoopState.COMPLETED  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_run_resets_state_between_calls(self) -> None:
        loop = _make_loop(
            llm_responses=[
                _make_tool_call_response("task_complete", {"summary": "First"}),
            ],
        )
        await loop.run("First task")
        assert loop.state == LoopState.COMPLETED

        # Replace the mock's responses and run again
        loop._llm = MockAdapter([
            _make_tool_call_response("task_complete", {"summary": "Second"}),
        ])
        result = await loop.run("Second task")
        assert result == LoopState.COMPLETED
