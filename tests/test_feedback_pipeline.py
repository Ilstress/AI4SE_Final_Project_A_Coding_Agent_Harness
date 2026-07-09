"""Tests for FeedbackPipeline — SPEC §3.6, PLAN T8.9."""

from harness.feedback.controllers.governance import (
    GovernanceController,
    GovernanceDecision,
    GovernanceState,
)
from harness.feedback.controllers.recovery import (
    RecoveryController,
    RecoveryDecision,
    RecoveryState,
)
from harness.feedback.coordination import (
    CoordinationLayer,
    EscalationEvent,
)
from harness.feedback.fingerprint import FingerprintStrategy
from harness.feedback.pipeline import FeedbackPipeline, PipelineResult
from harness.feedback.router import Track
from harness.models.feedback import FeedbackSource, Severity
from harness.models.tool_result import ToolResult


def _make_tool_result(
    success: bool = False,
    exit_code: int = 1,
    stdout: str = "",
    stderr: str = "error: file not found",
) -> ToolResult:
    return ToolResult(
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error="file not found" if not success else None,
        duration_ms=10,
    )


def _make_guard_result(verdict: str = "BLOCKED", rules: list[str] | None = None) -> dict:
    if rules is None:
        rules = ["RuleA"]
    return {
        "guard_result": _FakeGuardResult(verdict=verdict, rule_names=rules),
    }


class _FakeGuardResult:
    def __init__(self, verdict: str, rule_names: list[str]) -> None:
        self.verdict = _FakeVerdict(verdict)
        self.rule_results = [_FakeRuleResult(name) for name in rule_names]


class _FakeVerdict:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeRuleResult:
    def __init__(self, rule_name: str) -> None:
        self.rule_name = rule_name


# ---------------------------------------------------------------------------
# Shell failure → RECOVERY track
# ---------------------------------------------------------------------------


class TestShellFailurePipeline:
    def test_shell_failure_routes_to_recovery_continue(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = {
            "command": "rm -rf /",
            "tool_result": _make_tool_result(success=False, exit_code=1),
        }
        result = pipeline.process(FeedbackSource.SHELL, raw_data)

        assert result.track == Track.RECOVERY
        assert result.recovery_decision == RecoveryDecision.CONTINUE
        assert result.governance_decision is None
        assert result.feedback is not None
        assert result.feedback.source == FeedbackSource.SHELL
        assert result.feedback.severity == Severity.ERROR
        assert result.feedback.fingerprint != ""


# ---------------------------------------------------------------------------
# Guardrail BLOCKED → GOVERNANCE track
# ---------------------------------------------------------------------------


class TestGuardrailBlockedPipeline:
    def test_guardrail_blocked_routes_to_governance_block(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = _make_guard_result(verdict="BLOCKED")
        result = pipeline.process(FeedbackSource.GUARDRAIL, raw_data)

        assert result.track == Track.GOVERNANCE
        assert result.governance_decision == GovernanceDecision.BLOCK
        assert result.recovery_decision is None
        assert result.feedback.source == FeedbackSource.GUARDRAIL
        assert result.feedback.severity == Severity.CRITICAL


# ---------------------------------------------------------------------------
# Convergence detection
# ---------------------------------------------------------------------------


class TestConvergencePipeline:
    def test_three_same_errors_triggers_convergence(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = {
            "command": "bad_command",
            "tool_result": _make_tool_result(success=False, exit_code=1),
        }

        # First error
        result1 = pipeline.process(FeedbackSource.SHELL, raw_data)
        assert result1.escalation_event is None

        # Second error — same command
        result2 = pipeline.process(FeedbackSource.SHELL, raw_data)
        assert result2.escalation_event is None

        # Third error — convergence should trigger
        result3 = pipeline.process(FeedbackSource.SHELL, raw_data)
        assert result3.escalation_event == EscalationEvent.CONVERGENCE_FAILURE


# ---------------------------------------------------------------------------
# End-to-end: ToolResult → Feedback → Router → Controller → PipelineResult
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_pipeline_returns_pipeline_result(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = {
            "command": "ls",
            "tool_result": _make_tool_result(success=True, exit_code=0, stdout="file.txt"),
        }
        result = pipeline.process(FeedbackSource.SHELL, raw_data)

        assert isinstance(result, PipelineResult)
        assert result.feedback is not None
        assert result.track is not None
        assert result.feedback.fingerprint != ""

    def test_recovery_state_advances(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = {
            "command": "bad_cmd",
            "tool_result": _make_tool_result(success=False, exit_code=1),
        }

        assert recovery.state == RecoveryState.IDLE
        pipeline.process(FeedbackSource.SHELL, raw_data)
        assert recovery.state == RecoveryState.CONTINUE  # type: ignore[comparison-overlap]

    def test_governance_state_advances(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = _make_guard_result(verdict="BLOCKED")

        assert governance.state == GovernanceState.IDLE
        pipeline.process(FeedbackSource.GUARDRAIL, raw_data)
        assert governance.state == GovernanceState.BLOCK  # type: ignore[comparison-overlap]

    def test_pipeline_result_contains_fingerprint(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        raw_data = {
            "command": "test_cmd",
            "tool_result": _make_tool_result(success=False, exit_code=2),
        }
        result = pipeline.process(FeedbackSource.SHELL, raw_data)
        expected_fp = FingerprintStrategy.generate(result.feedback)

        assert result.feedback.fingerprint == expected_fp
        assert len(result.feedback.fingerprint) == 16


# ---------------------------------------------------------------------------
# Pipeline does not hold state
# ---------------------------------------------------------------------------


class TestPipelineStateless:
    def test_pipeline_has_no_mutable_state(self) -> None:
        recovery = RecoveryController()
        governance = GovernanceController()
        coordination = CoordinationLayer()
        pipeline = FeedbackPipeline(recovery, governance, coordination)

        # Pipeline is a pure orchestrator — state lives in controllers/coordination
        assert not hasattr(pipeline, "_state")
        assert not hasattr(pipeline, "_feedback_count")
