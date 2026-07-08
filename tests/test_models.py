"""Tests for all 16 data models defined in SPEC §6.

Each test verifies:
- Construction with valid data
- Frozen (immutable) behavior
- Enum values
- Default values where applicable
- Optional fields (None)
"""

import time
from dataclasses import FrozenInstanceError

import pytest

# ============================================================
# We import from harness.models after implementation.
# Tests are written first (TDD: red phase).
# ============================================================


# ---------------------------------------------------------------------------
# 6.1 Action
# ---------------------------------------------------------------------------
class TestAction:
    """SPEC §6.1: Action — parsed tool call the agent intends to execute."""

    def test_action_construction(self):
        from harness.models.action import Action

        action = Action(
            tool_name="read_file",
            parameters={"path": "src/main.py"},
            raw_response={"id": "call_1", "name": "read_file", "arguments": {}},
        )
        assert action.tool_name == "read_file"
        assert action.parameters == {"path": "src/main.py"}
        assert action.raw_response == {"id": "call_1", "name": "read_file", "arguments": {}}

    def test_action_is_frozen(self):
        from harness.models.action import Action

        action = Action(
            tool_name="read_file",
            parameters={"path": "src/main.py"},
            raw_response={},
        )
        with pytest.raises(FrozenInstanceError):
            action.tool_name = "write_file"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.2 ToolCall
# ---------------------------------------------------------------------------
class TestToolCall:
    """SPEC §6.2: ToolCall — raw tool call from LLM API response."""

    def test_toolcall_construction(self):
        from harness.models.tool_call import ToolCall

        tc = ToolCall(
            id="call_abc123",
            name="execute_shell",
            arguments={"command": "pytest"},
        )
        assert tc.id == "call_abc123"
        assert tc.name == "execute_shell"
        assert tc.arguments == {"command": "pytest"}

    def test_toolcall_is_frozen(self):
        from harness.models.tool_call import ToolCall

        tc = ToolCall(id="x", name="y", arguments={})
        with pytest.raises(FrozenInstanceError):
            tc.name = "z"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.3 ToolResult
# ---------------------------------------------------------------------------
class TestToolResult:
    """SPEC §6.3: ToolResult — result of executing a tool action."""

    def test_successful_shell_result(self):
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=True,
            exit_code=0,
            stdout="hello",
            stderr=None,
            error=None,
            duration_ms=150,
        )
        assert tr.success is True
        assert tr.exit_code == 0
        assert tr.stdout == "hello"
        assert tr.stderr is None
        assert tr.error is None
        assert tr.duration_ms == 150

    def test_failed_shell_result(self):
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=False,
            exit_code=1,
            stdout=None,
            stderr="command not found",
            error=None,
            duration_ms=50,
        )
        assert tr.success is False
        assert tr.exit_code == 1
        assert tr.stderr == "command not found"

    def test_file_not_found_result(self):
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=False,
            exit_code=None,
            stdout=None,
            stderr=None,
            error="FILE_NOT_FOUND",
            duration_ms=5,
        )
        assert tr.success is False
        assert tr.error == "FILE_NOT_FOUND"
        assert tr.exit_code is None  # only for shell

    def test_toolresult_is_frozen(self):
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=True, exit_code=None, stdout=None, stderr=None, error=None, duration_ms=0
        )
        with pytest.raises(FrozenInstanceError):
            tr.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.4 Feedback
# ---------------------------------------------------------------------------
class TestFeedback:
    """SPEC §6.4: Feedback — immutable event consumed by Feedback Pipeline."""

    def test_feedback_construction(self):
        from harness.models.feedback import Feedback, FeedbackMetadata, FeedbackSource, Severity

        metadata = FeedbackMetadata(
            provider="deepseek",
            latency_ms=200,
            retry_count=0,
            trace_id=None,
        )
        fb = Feedback(
            fingerprint="abc123def456",
            source=FeedbackSource.SHELL,
            severity=Severity.ERROR,
            payload={"exit_code": 1, "command": "pytest"},
            metadata=metadata,
            round=3,
            timestamp=time.time(),
            tool_call=None,
            correlation_id=None,
        )
        assert fb.fingerprint == "abc123def456"
        assert fb.source == FeedbackSource.SHELL
        assert fb.severity == Severity.ERROR
        assert fb.payload == {"exit_code": 1, "command": "pytest"}
        assert fb.metadata.provider == "deepseek"
        assert fb.round == 3
        assert fb.tool_call is None
        assert fb.correlation_id is None

    def test_feedback_is_frozen(self):
        from harness.models.feedback import Feedback, FeedbackMetadata, FeedbackSource, Severity

        metadata = FeedbackMetadata(provider="x", latency_ms=0, retry_count=0, trace_id=None)
        fb = Feedback(
            fingerprint="fp",
            source=FeedbackSource.SHELL,
            severity=Severity.INFO,
            payload={},
            metadata=metadata,
            round=1,
            timestamp=0.0,
            tool_call=None,
            correlation_id=None,
        )
        with pytest.raises(FrozenInstanceError):
            fb.fingerprint = "new"  # type: ignore[misc]

    def test_feedback_with_tool_call(self):
        from harness.models.feedback import Feedback, FeedbackMetadata, FeedbackSource, Severity
        from harness.models.tool_call import ToolCall

        tc = ToolCall(id="call_1", name="execute_shell", arguments={"command": "pytest"})
        metadata = FeedbackMetadata(provider="x", latency_ms=0, retry_count=0, trace_id=None)
        fb = Feedback(
            fingerprint="fp",
            source=FeedbackSource.TEST,
            severity=Severity.ERROR,
            payload={"passed": 0, "failed": 1},
            metadata=metadata,
            round=2,
            timestamp=0.0,
            tool_call=tc,
            correlation_id="corr_001",
        )
        assert fb.tool_call is not None
        assert fb.tool_call.name == "execute_shell"
        assert fb.correlation_id == "corr_001"


# ---------------------------------------------------------------------------
# 6.5 FeedbackMetadata
# ---------------------------------------------------------------------------
class TestFeedbackMetadata:
    """SPEC §6.5: FeedbackMetadata — system-level metadata for Feedback."""

    def test_metadata_construction(self):
        from harness.models.feedback import FeedbackMetadata

        m = FeedbackMetadata(
            provider="deepseek",
            latency_ms=350,
            retry_count=2,
            trace_id="trace_xyz",
        )
        assert m.provider == "deepseek"
        assert m.latency_ms == 350
        assert m.retry_count == 2
        assert m.trace_id == "trace_xyz"

    def test_metadata_trace_id_optional(self):
        from harness.models.feedback import FeedbackMetadata

        m = FeedbackMetadata(provider="openai", latency_ms=100, retry_count=0, trace_id=None)
        assert m.trace_id is None

    def test_metadata_is_frozen(self):
        from harness.models.feedback import FeedbackMetadata

        m = FeedbackMetadata(provider="x", latency_ms=0, retry_count=0, trace_id=None)
        with pytest.raises(FrozenInstanceError):
            m.provider = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.6 GuardResult
# ---------------------------------------------------------------------------
class TestGuardResult:
    """SPEC §6.6: GuardResult — result of guardrail evaluation on an action."""

    def test_allowed_guard_result(self):
        from harness.models.guard_result import GuardResult, GuardVerdict

        gr = GuardResult(verdict=GuardVerdict.ALLOWED, rule_results=(), approval_request=None)
        assert gr.verdict == GuardVerdict.ALLOWED
        assert gr.rule_results == ()
        assert gr.approval_request is None

    def test_blocked_guard_result(self):
        from harness.models.guard_result import GuardResult, GuardVerdict
        from harness.models.rule_result import RuleResult, RuleVerdict

        rr = RuleResult(
            rule_name="PathBoundaryRule",
            verdict=RuleVerdict.BLOCK,
            reason="Write path /etc/passwd is outside workspace",
            evidence={"path": "/etc/passwd"},
        )
        gr = GuardResult(verdict=GuardVerdict.BLOCKED, rule_results=(rr,), approval_request=None)
        assert gr.verdict == GuardVerdict.BLOCKED
        assert len(gr.rule_results) == 1
        assert gr.rule_results[0].rule_name == "PathBoundaryRule"

    def test_approval_required_guard_result(self):
        from harness.models.approval import ApprovalRequest
        from harness.models.guard_result import GuardResult, GuardVerdict
        from harness.models.rule_result import RuleResult, RuleVerdict

        rr = RuleResult(
            rule_name="DangerousShellRule",
            verdict=RuleVerdict.FLAG,
            reason="Detected rm -rf",
            evidence={"command": "rm -rf /"},
        )
        ar = ApprovalRequest(
            description="About to execute: rm -rf /",
            evidence=[{"rule": "DangerousShellRule", "command": "rm -rf /"}],
            timestamp=time.time(),
        )
        gr = GuardResult(
            verdict=GuardVerdict.APPROVAL_REQUIRED, rule_results=(rr,), approval_request=ar
        )
        assert gr.verdict == GuardVerdict.APPROVAL_REQUIRED
        assert gr.approval_request is not None
        assert gr.approval_request.description == "About to execute: rm -rf /"

    def test_guard_result_is_frozen(self):
        from harness.models.guard_result import GuardResult, GuardVerdict

        gr = GuardResult(verdict=GuardVerdict.ALLOWED, rule_results=(), approval_request=None)
        with pytest.raises(FrozenInstanceError):
            gr.verdict = GuardVerdict.BLOCKED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.7 RuleResult
# ---------------------------------------------------------------------------
class TestRuleResult:
    """SPEC §6.7: RuleResult — result of a single rule evaluation."""

    def test_rule_result_construction(self):
        from harness.models.rule_result import RuleResult, RuleVerdict

        rr = RuleResult(
            rule_name="PathBoundaryRule",
            verdict=RuleVerdict.BLOCK,
            reason="Path outside workspace",
            evidence={"path": "/etc/passwd", "workspace_root": "/home/project"},
        )
        assert rr.rule_name == "PathBoundaryRule"
        assert rr.verdict == RuleVerdict.BLOCK
        assert rr.reason == "Path outside workspace"
        assert rr.evidence == {"path": "/etc/passwd", "workspace_root": "/home/project"}

    def test_rule_result_is_frozen(self):
        from harness.models.rule_result import RuleResult, RuleVerdict

        rr = RuleResult(rule_name="R", verdict=RuleVerdict.ALLOW, reason="ok", evidence={})
        with pytest.raises(FrozenInstanceError):
            rr.verdict = RuleVerdict.BLOCK  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.8 ApprovalRequest
# ---------------------------------------------------------------------------
class TestApprovalRequest:
    """SPEC §6.8: ApprovalRequest — human approval request from GovernanceController."""

    def test_approval_request_construction(self):
        from harness.models.approval import ApprovalRequest

        ar = ApprovalRequest(
            description="Execute: rm -rf ./build/",
            evidence=[{"rule": "DangerousShellRule", "command": "rm -rf ./build/"}],
            timestamp=1730000000.0,
        )
        assert ar.description == "Execute: rm -rf ./build/"
        assert len(ar.evidence) == 1
        assert ar.timestamp == 1730000000.0

    def test_approval_request_is_frozen(self):
        from harness.models.approval import ApprovalRequest

        ar = ApprovalRequest(description="d", evidence=[], timestamp=0.0)
        with pytest.raises(FrozenInstanceError):
            ar.description = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.9 ApprovalResult
# ---------------------------------------------------------------------------
class TestApprovalResult:
    """SPEC §6.9: ApprovalResult — result of human approval interaction."""

    def test_approved_result(self):
        from harness.models.approval import ApprovalOutcome, ApprovalResult

        ar = ApprovalResult(result=ApprovalOutcome.APPROVED)
        assert ar.result == ApprovalOutcome.APPROVED

    def test_rejected_result(self):
        from harness.models.approval import ApprovalOutcome, ApprovalResult

        ar = ApprovalResult(result=ApprovalOutcome.REJECTED)
        assert ar.result == ApprovalOutcome.REJECTED

    def test_timeout_result(self):
        from harness.models.approval import ApprovalOutcome, ApprovalResult

        ar = ApprovalResult(result=ApprovalOutcome.TIMEOUT)
        assert ar.result == ApprovalOutcome.TIMEOUT

    def test_approval_result_is_frozen(self):
        from harness.models.approval import ApprovalOutcome, ApprovalResult

        ar = ApprovalResult(result=ApprovalOutcome.APPROVED)
        with pytest.raises(FrozenInstanceError):
            ar.result = ApprovalOutcome.REJECTED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.10 ExecutionOutcome
# ---------------------------------------------------------------------------
class TestExecutionOutcome:
    """SPEC §6.10: ExecutionOutcome — union type for Feedback Pipeline input."""

    def test_tool_result_variant(self):
        from harness.models.execution_outcome import ExecutionOutcome
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=True, exit_code=0, stdout="ok", stderr=None, error=None, duration_ms=10
        )
        eo = ExecutionOutcome(tool_result=tr)
        assert eo.tool_result is not None
        assert eo.guard_result is None
        assert eo.parse_error is None
        assert eo.tool_result.exit_code == 0

    def test_guard_result_variant(self):
        from harness.models.execution_outcome import ExecutionOutcome
        from harness.models.guard_result import GuardResult, GuardVerdict

        gr = GuardResult(verdict=GuardVerdict.BLOCKED, rule_results=(), approval_request=None)
        eo = ExecutionOutcome(guard_result=gr)
        assert eo.guard_result is not None
        assert eo.tool_result is None
        assert eo.parse_error is None
        assert eo.guard_result.verdict == GuardVerdict.BLOCKED

    def test_parse_error_variant(self):
        from harness.models.execution_outcome import ExecutionOutcome
        from harness.models.parse_error import ParseError

        pe = ParseError(
            error_type="MALFORMED_CALL",
            raw_response={"invalid": True},
            detail="JSON parse failed",
        )
        eo = ExecutionOutcome(parse_error=pe)
        assert eo.parse_error is not None
        assert eo.tool_result is None
        assert eo.guard_result is None
        assert eo.parse_error.error_type == "MALFORMED_CALL"

    def test_execution_outcome_is_frozen(self):
        from harness.models.execution_outcome import ExecutionOutcome
        from harness.models.tool_result import ToolResult

        tr = ToolResult(
            success=True, exit_code=None, stdout=None, stderr=None, error=None, duration_ms=0
        )
        eo = ExecutionOutcome(tool_result=tr)
        with pytest.raises(FrozenInstanceError):
            eo.tool_result = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.11 ParseError
# ---------------------------------------------------------------------------
class TestParseError:
    """SPEC §6.11: ParseError — failure to parse LLM response into valid action."""

    def test_unknown_tool_parse_error(self):
        from harness.models.parse_error import ParseError

        pe = ParseError(
            error_type="UNKNOWN_TOOL",
            raw_response={"id": "c1", "name": "delete_database", "arguments": {}},
            detail="Tool 'delete_database' is not registered",
        )
        assert pe.error_type == "UNKNOWN_TOOL"
        assert pe.raw_response == {"id": "c1", "name": "delete_database", "arguments": {}}
        assert pe.detail == "Tool 'delete_database' is not registered"

    def test_malformed_call_parse_error(self):
        from harness.models.parse_error import ParseError

        pe = ParseError(
            error_type="MALFORMED_CALL",
            raw_response={"invalid_json": True},
            detail="Missing required parameter 'path'",
        )
        assert pe.error_type == "MALFORMED_CALL"

    def test_parse_error_is_frozen(self):
        from harness.models.parse_error import ParseError

        pe = ParseError(error_type="UNKNOWN_TOOL", raw_response={}, detail="err")
        with pytest.raises(FrozenInstanceError):
            pe.error_type = "MALFORMED_CALL"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.12 MemoryEntry
# ---------------------------------------------------------------------------
class TestMemoryEntry:
    """SPEC §6.12: MemoryEntry — single record in long-term memory store."""

    def test_memory_entry_construction(self):
        from harness.models.memory_entry import MemoryEntry

        me = MemoryEntry(
            id="mem_001",
            category="CONVENTION",
            content="Use snake_case for all Python files",
            created_at=1730000000.0,
            source_round=2,
        )
        assert me.id == "mem_001"
        assert me.category == "CONVENTION"
        assert me.content == "Use snake_case for all Python files"
        assert me.created_at == 1730000000.0
        assert me.source_round == 2

    def test_memory_entry_categories(self):
        from harness.models.memory_entry import MemoryEntry

        for cat in ("CONVENTION", "DECISION", "PREFERENCE", "SUMMARY"):
            me = MemoryEntry(
                id="x", category=cat, content="c", created_at=0.0, source_round=0
            )
            assert me.category == cat

    def test_memory_entry_is_frozen(self):
        from harness.models.memory_entry import MemoryEntry

        me = MemoryEntry(id="x", category="SUMMARY", content="c", created_at=0.0, source_round=0)
        with pytest.raises(FrozenInstanceError):
            me.content = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.13 Configuration
# ---------------------------------------------------------------------------
class TestConfiguration:
    """SPEC §6.13: Configuration — immutable session configuration loaded at startup."""

    def test_config_construction(self):
        from harness.models.config import Config, LLMConfig, WorkspaceConfig

        cfg = Config(
            workspace=WorkspaceConfig(root="/home/user/project"),
            llm=LLMConfig(
                provider="deepseek",
                model="deepseek-chat",
                api_base=None,
            ),
        )
        assert cfg.workspace.root == "/home/user/project"
        assert cfg.llm.provider == "deepseek"
        assert cfg.llm.model == "deepseek-chat"
        assert cfg.llm.api_base is None

    def test_config_defaults(self):
        from harness.models.config import Config, LLMConfig, WorkspaceConfig

        cfg = Config(
            workspace=WorkspaceConfig(root="/tmp"),
            llm=LLMConfig(provider="openai", model="gpt-4o"),
        )
        # Default values from SPEC §3.8
        assert cfg.loop.max_iterations == 10
        assert cfg.loop.timeout_seconds == 300
        assert cfg.loop.convergence_threshold == 3
        assert cfg.guard.hitl_timeout_seconds == 120
        assert cfg.memory.file_path == "./memory.json"

    def test_config_is_frozen(self):
        from harness.models.config import Config, LLMConfig, WorkspaceConfig

        cfg = Config(
            workspace=WorkspaceConfig(root="/tmp"),
            llm=LLMConfig(provider="x", model="y"),
        )
        with pytest.raises(FrozenInstanceError):
            cfg.workspace.root = "/new"  # type: ignore[misc]

    def test_config_no_api_key_field(self):
        """API Key must NOT be in Config (SPEC constraint)."""
        from harness.models.config import Config, LLMConfig, WorkspaceConfig

        cfg = Config(
            workspace=WorkspaceConfig(root="/tmp"),
            llm=LLMConfig(provider="x", model="y"),
        )
        assert not hasattr(cfg, "api_key")
        assert not hasattr(cfg.llm, "api_key")

    def test_loop_config_defaults(self):
        from harness.models.config import LoopConfig

        lc = LoopConfig()
        assert lc.max_iterations == 10
        assert lc.timeout_seconds == 300
        assert lc.convergence_threshold == 3

    def test_guard_config_defaults(self):
        from harness.models.config import GuardConfig

        gc = GuardConfig()
        assert gc.hitl_timeout_seconds == 120
        assert gc.rules == []

    def test_tools_config_defaults(self):
        from harness.models.config import ToolsConfig

        tc = ToolsConfig()
        assert "read_file" in tc.enabled
        assert "write_file" in tc.enabled
        assert "execute_shell" in tc.enabled
        assert "task_complete" in tc.enabled

    def test_memory_config_defaults(self):
        from harness.models.config import MemoryConfig

        mc = MemoryConfig()
        assert mc.file_path == "./memory.json"


# ---------------------------------------------------------------------------
# 6.14 LLMResponse
# ---------------------------------------------------------------------------
class TestLLMResponse:
    """SPEC §6.14: LLMResponse — standardized response from LLM adapter."""

    def test_text_response(self):
        from harness.models.llm_response import LLMResponse

        resp = LLMResponse(
            content="Here is the code you requested.",
            tool_calls=None,
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        assert resp.content == "Here is the code you requested."
        assert resp.tool_calls is None
        assert resp.finish_reason == "stop"
        assert resp.usage["total_tokens"] == 150

    def test_tool_call_response(self):
        from harness.models.llm_response import LLMResponse

        resp = LLMResponse(
            content=None,
            tool_calls=[
                {"id": "call_1", "name": "read_file", "arguments": {"path": "src/main.py"}}
            ],
            finish_reason="tool_calls",
            usage={"prompt_tokens": 200, "completion_tokens": 30, "total_tokens": 230},
        )
        assert resp.content is None
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["name"] == "read_file"
        assert resp.finish_reason == "tool_calls"

    def test_llm_response_is_frozen(self):
        from harness.models.llm_response import LLMResponse

        resp = LLMResponse(
            content="hello", tool_calls=None, finish_reason="stop", usage={}
        )
        with pytest.raises(FrozenInstanceError):
            resp.content = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.15 ToolDefinition
# ---------------------------------------------------------------------------
class TestToolDefinition:
    """SPEC §6.15: ToolDefinition — JSON Schema definition of a tool."""

    def test_tool_definition_construction(self):
        from harness.models.tool_definition import ToolDefinition

        td = ToolDefinition(
            name="read_file",
            description="Read the contents of a file at the given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
                },
                "required": ["path"],
            },
        )
        assert td.name == "read_file"
        assert "Read the contents" in td.description
        assert td.parameters["type"] == "object"
        assert "path" in td.parameters["required"]

    def test_tool_definition_is_frozen(self):
        from harness.models.tool_definition import ToolDefinition

        td = ToolDefinition(name="t", description="d", parameters={})
        with pytest.raises(FrozenInstanceError):
            td.name = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6.16 PersistDecision
# ---------------------------------------------------------------------------
class TestPersistDecision:
    """SPEC §6.16: PersistDecision — outcome of MemoryPolicy evaluation."""

    def test_persist_decision(self):
        from harness.models.persist_decision import PersistDecision, PersistOutcome

        pd = PersistDecision(
            decision=PersistOutcome.PERSIST,
            reason="User input should be persisted",
            category="CONVENTION",
        )
        assert pd.decision == PersistOutcome.PERSIST
        assert pd.reason == "User input should be persisted"
        assert pd.category == "CONVENTION"

    def test_discard_decision(self):
        from harness.models.persist_decision import PersistDecision, PersistOutcome

        pd = PersistDecision(
            decision=PersistOutcome.DISCARD,
            reason="Shell output is transient",
            category=None,
        )
        assert pd.decision == PersistOutcome.DISCARD
        assert pd.category is None

    def test_persist_decision_is_frozen(self):
        from harness.models.persist_decision import PersistDecision, PersistOutcome

        pd = PersistDecision(decision=PersistOutcome.DISCARD, reason="r", category=None)
        with pytest.raises(FrozenInstanceError):
            pd.decision = PersistOutcome.PERSIST  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Enum value verification
# ---------------------------------------------------------------------------
class TestEnums:
    """Verify all enum values match SPEC §6 definitions."""

    def test_feedback_source_values(self):
        from harness.models.feedback import FeedbackSource

        values = {e.value for e in FeedbackSource}
        expected = {
            "SHELL", "TEST", "LINT", "DIFF", "GUARDRAIL",
            "PARSER", "TOOL_EXECUTOR", "MEMORY", "SYSTEM",
        }
        assert values == expected

    def test_severity_values(self):
        from harness.models.feedback import Severity

        values = {e.value for e in Severity}
        assert values == {"INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_guard_verdict_values(self):
        from harness.models.guard_result import GuardVerdict

        values = {e.value for e in GuardVerdict}
        assert values == {"ALLOWED", "BLOCKED", "APPROVAL_REQUIRED"}

    def test_rule_verdict_values(self):
        from harness.models.rule_result import RuleVerdict

        values = {e.value for e in RuleVerdict}
        assert values == {"ALLOW", "BLOCK", "FLAG"}

    def test_approval_outcome_values(self):
        from harness.models.approval import ApprovalOutcome

        values = {e.value for e in ApprovalOutcome}
        assert values == {"APPROVED", "REJECTED", "TIMEOUT"}

    def test_persist_outcome_values(self):
        from harness.models.persist_decision import PersistOutcome

        values = {e.value for e in PersistOutcome}
        assert values == {"PERSIST", "DISCARD"}
