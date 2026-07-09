"""MainLoop — event-driven state machine orchestrating the Agent runtime (SPEC §3.1, PLAN T10.1)."""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum

from harness.context.context_builder import build as build_context
from harness.feedback.pipeline import FeedbackPipeline
from harness.guard.guardrail import Guardrail
from harness.llm.abstract_llm import AbstractLLM
from harness.models.action import Action
from harness.models.approval import ApprovalOutcome
from harness.models.config import Config
from harness.models.feedback import FeedbackSource
from harness.models.guard_result import GuardResult, GuardVerdict
from harness.models.parse_error import ParseError
from harness.models.tool_result import ToolResult
from harness.parser.action_parser import parse as parse_action
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class LoopState(Enum):
    """States of the Main Loop state machine."""

    START = "START"
    RUNNING = "RUNNING"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LoopEvent(Enum):
    """Events that trigger state transitions."""

    INIT_COMPLETE = "init_complete"
    TASK_COMPLETE = "task_complete"
    HARD_LIMIT = "hard_limit"
    CONVERGENCE_FAILURE = "convergence_failure"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


# (current_state, event, next_state)
_Transition = tuple[LoopState, LoopEvent, LoopState]

_TRANSITIONS: list[_Transition] = [
    (LoopState.START, LoopEvent.INIT_COMPLETE, LoopState.RUNNING),
    (LoopState.RUNNING, LoopEvent.TASK_COMPLETE, LoopState.COMPLETED),
    (LoopState.RUNNING, LoopEvent.HARD_LIMIT, LoopState.FAILED),
    (LoopState.RUNNING, LoopEvent.CONVERGENCE_FAILURE, LoopState.FAILED),
    (LoopState.RUNNING, LoopEvent.APPROVAL_REQUIRED, LoopState.AWAITING_HUMAN),
    (LoopState.AWAITING_HUMAN, LoopEvent.APPROVED, LoopState.RUNNING),
    (LoopState.AWAITING_HUMAN, LoopEvent.REJECTED, LoopState.CANCELLED),
    (LoopState.AWAITING_HUMAN, LoopEvent.TIMEOUT, LoopState.FAILED),
]

# Map tool names to FeedbackSource for pipeline routing
_TOOL_FEEDBACK_SOURCE: dict[str, FeedbackSource] = {
    "execute_shell": FeedbackSource.SHELL,
    "write_file": FeedbackSource.DIFF,
    "read_file": FeedbackSource.TOOL_EXECUTOR,
    "task_complete": FeedbackSource.SYSTEM,
}

DEFAULT_SYSTEM_PROMPT = """You are a coding agent. You have access to tools for reading, writing,
and executing code. Complete the user's task step by step. When done,
call task_complete with a summary of what you accomplished."""


# ---------------------------------------------------------------------------
# MainLoop
# ---------------------------------------------------------------------------


class MainLoop:
    """Event-driven state machine that orchestrates the Agent runtime.

    Coordinates: ContextBuilder → LLM → ActionParser → Guardrail →
    ToolExecutor → FeedbackPipeline → StopConditions.

    Holds message history and tracks iteration count / wall-clock time.
    """

    def __init__(
        self,
        config: Config,
        llm: AbstractLLM,
        guardrail: Guardrail,
        tool_executor: ToolExecutor,
        tool_registry: ToolRegistry,
        feedback_pipeline: FeedbackPipeline,
    ) -> None:
        self._config = config
        self._llm = llm
        self._guardrail = guardrail
        self._tool_executor = tool_executor
        self._tool_registry = tool_registry
        self._feedback_pipeline = feedback_pipeline

        self._state = LoopState.START
        self._message_history: list[dict] = []
        self._iteration: int = 0
        self._start_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def iteration(self) -> int:
        return self._iteration

    @property
    def message_history(self) -> list[dict]:
        return list(self._message_history)

    async def run(self, task: str) -> LoopState:
        """Execute the Main Loop for a given user task.

        Returns one of the terminal states: COMPLETED, FAILED, or CANCELLED.
        """
        self._reset(task)

        try:
            # Transition: START → RUNNING
            self._apply_transition(LoopEvent.INIT_COMPLETE)

            while self._state == LoopState.RUNNING:
                # Check hard limits
                if self._iteration >= self._config.loop.max_iterations:
                    logger.warning("Hard limit: max_iterations (%s) exceeded", self._config.loop.max_iterations)
                    self._apply_transition(LoopEvent.HARD_LIMIT)
                    break

                if self._check_timeout():
                    logger.warning("Hard limit: timeout (%ss) exceeded", self._config.loop.timeout_seconds)
                    self._apply_transition(LoopEvent.HARD_LIMIT)
                    break

                self._iteration += 1

                # Execute one iteration
                await self._iterate(task)

            return self._state

        except Exception:
            logger.exception("Unhandled exception in Main Loop — transitioning to FAILED")
            self._state = LoopState.FAILED
            return self._state

    # ------------------------------------------------------------------
    # Single iteration
    # ------------------------------------------------------------------

    async def _iterate(self, task: str) -> None:
        # 1. Build context
        tools = self._tool_registry.get_all_tools()
        messages = build_context(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tool_definitions=tools,
            memory_entries=[],
            message_history=self._message_history,
            user_task=task,
        )

        # 2. LLM call
        try:
            response = await self._llm.call(messages)
        except Exception:
            logger.exception("LLM call failed")
            self._state = LoopState.FAILED
            return

        # 3. Parse response
        parsed = parse_action(response, self._tool_registry)

        # 4. Dispatch
        if isinstance(parsed, str):
            # TextOnly: append to history, continue
            self._message_history.append({"role": "assistant", "content": parsed})
            return

        actions: list[Action | ParseError] = parsed if isinstance(parsed, list) else [parsed]

        for item in actions:
            if self._state != LoopState.RUNNING:
                break

            if isinstance(item, ParseError):
                self._handle_parse_error(item)
            else:
                await self._handle_action(item)

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------

    async def _handle_action(self, action: Action) -> None:
        guard_result = self._guardrail.evaluate(action)

        if guard_result.verdict == GuardVerdict.ALLOWED:
            await self._execute_and_feedback(action)
        elif guard_result.verdict == GuardVerdict.BLOCKED:
            self._handle_blocked(action, guard_result)
        elif guard_result.verdict == GuardVerdict.APPROVAL_REQUIRED:
            await self._handle_approval_required(action, guard_result)

    async def _execute_and_feedback(self, action: Action) -> None:
        result = await self._tool_executor.execute(action)

        # Record in message history
        self._message_history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [action.raw_response],
        })
        self._message_history.append({
            "role": "tool",
            "content": result.stdout or result.stderr or "",
            "tool_call_id": action.raw_response.get("id", ""),
        })

        # Check for task_complete
        if action.tool_name == "task_complete" and result.success:
            self._apply_transition(LoopEvent.TASK_COMPLETE)
            return

        # Feed to Feedback Pipeline
        source = _TOOL_FEEDBACK_SOURCE.get(action.tool_name, FeedbackSource.TOOL_EXECUTOR)
        raw_data = self._build_raw_data(action, result)
        pipeline_result = self._feedback_pipeline.process(source, raw_data)

        if pipeline_result.escalation_event is not None:
            logger.warning("Escalation: %s", pipeline_result.escalation_event.value)
            self._apply_transition(LoopEvent.CONVERGENCE_FAILURE)

    def _handle_blocked(self, action: Action, guard_result: GuardResult) -> None:
        raw_data = {"guard_result": guard_result}
        self._feedback_pipeline.process(FeedbackSource.GUARDRAIL, raw_data)

    async def _handle_approval_required(self, action: Action, guard_result: GuardResult) -> None:
        self._apply_transition(LoopEvent.APPROVAL_REQUIRED)

        approval_request = guard_result.approval_request
        if approval_request is None:
            logger.error("APPROVAL_REQUIRED but no ApprovalRequest produced")
            self._state = LoopState.FAILED
            return

        # Main Loop manages HITL timeout (SPEC §3.6.4)
        hitl_timeout = self._config.guard.hitl_timeout_seconds
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._guardrail.approval_provider.request_approval, approval_request),
                timeout=hitl_timeout,
            )
        except TimeoutError:
            logger.warning("HITL timeout (%ss) exceeded", hitl_timeout)
            self._apply_transition(LoopEvent.TIMEOUT)
            return

        if result.result == ApprovalOutcome.APPROVED:
            self._apply_transition(LoopEvent.APPROVED)
            await self._execute_and_feedback(action)
        elif result.result == ApprovalOutcome.REJECTED:
            self._apply_transition(LoopEvent.REJECTED)
        elif result.result == ApprovalOutcome.TIMEOUT:
            self._apply_transition(LoopEvent.TIMEOUT)

    def _handle_parse_error(self, error: ParseError) -> None:
        raw_data = {"parse_error": error}
        self._feedback_pipeline.process(FeedbackSource.PARSER, raw_data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset(self, task: str) -> None:
        self._state = LoopState.START
        self._message_history = [{"role": "user", "content": task}]
        self._iteration = 0
        self._start_time = time.time()

    def _check_timeout(self) -> bool:
        if self._config.loop.timeout_seconds <= 0:
            return False
        elapsed = time.time() - self._start_time
        return elapsed > self._config.loop.timeout_seconds

    def _apply_transition(self, event: LoopEvent) -> None:
        for current_state, evt, next_state in _TRANSITIONS:
            if current_state == self._state and evt == event:
                logger.info("State transition: %s --(%s)--> %s", self._state.value, event.value, next_state.value)
                self._state = next_state
                return
        logger.warning("No transition for (%s, %s)", self._state.value, event.value)

    @staticmethod
    def _build_raw_data(action: Action, result: ToolResult) -> dict:
        return {
            "command": action.parameters.get("command", ""),
            "tool_result": result,
        }
