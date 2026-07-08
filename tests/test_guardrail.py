"""Tests for Guardrail — SPEC §3.4, PLAN T7.4."""

from harness.guard.approval.mock import MockApprovalProvider
from harness.guard.guardrail import Guardrail
from harness.guard.rule_engine import RuleEngine
from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.guard_result import GuardVerdict
from harness.models.rule_result import RuleResult, RuleVerdict


class _FakeRule(Rule):
    """A rule that returns a preset verdict."""

    def __init__(
        self,
        verdict: RuleVerdict,
        priority: int = 100,
        name: str = "fake",
    ) -> None:
        super().__init__("/tmp/ws")
        self._verdict = verdict
        self._priority = priority
        self._name = name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def rule_name(self) -> str:
        return self._name

    def evaluate(self, action: Action) -> RuleResult:
        return RuleResult(
            rule_name=self._name,
            verdict=self._verdict,
            reason=f"Fake {self._name}",
            evidence={},
        )


def _make_action(tool_name: str = "read_file") -> Action:
    return Action(
        tool_name=tool_name, parameters={"path": "test.py"}, raw_response={}
    )


def _make_guardrail(*verdicts: RuleVerdict) -> Guardrail:
    rules = [
        _FakeRule(v, priority=100 + i * 100, name=f"r{i}")
        for i, v in enumerate(verdicts)
    ]
    return Guardrail(RuleEngine(rules), MockApprovalProvider([]))


# ---------------------------------------------------------------------------
# ALLOWED
# ---------------------------------------------------------------------------


class TestAllowed:
    def test_safe_action_returns_allowed(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.ALLOW)
        result = guardrail.evaluate(_make_action("read_file"))
        assert result.verdict == GuardVerdict.ALLOWED

    def test_task_complete_passes_through_guardrail(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.ALLOW)
        result = guardrail.evaluate(_make_action("task_complete"))
        assert result.verdict == GuardVerdict.ALLOWED


# ---------------------------------------------------------------------------
# BLOCKED
# ---------------------------------------------------------------------------


class TestBlocked:
    def test_boundary_violation_returns_blocked(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.BLOCK)
        result = guardrail.evaluate(_make_action("write_file"))
        assert result.verdict == GuardVerdict.BLOCKED

    def test_blocked_has_rule_results(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.ALLOW, RuleVerdict.BLOCK)
        result = guardrail.evaluate(_make_action("write_file"))
        assert result.verdict == GuardVerdict.BLOCKED
        assert len(result.rule_results) == 2


# ---------------------------------------------------------------------------
# APPROVAL_REQUIRED
# ---------------------------------------------------------------------------


class TestApprovalRequired:
    def test_dangerous_action_returns_approval_required(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.FLAG)
        result = guardrail.evaluate(_make_action("execute_shell"))
        assert result.verdict == GuardVerdict.APPROVAL_REQUIRED
        assert result.approval_request is not None

    def test_approval_required_includes_request(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.FLAG)
        result = guardrail.evaluate(_make_action("execute_shell"))
        req = result.approval_request
        assert req is not None
        assert len(req.description) > 0


# ---------------------------------------------------------------------------
# All actions go through Guardrail
# ---------------------------------------------------------------------------


class TestAllActionsGoThroughGuardrail:
    def test_all_tool_types_evaluated(self) -> None:
        guardrail = _make_guardrail(RuleVerdict.ALLOW)
        for tool in ["read_file", "write_file", "execute_shell", "task_complete"]:
            result = guardrail.evaluate(_make_action(tool))
            assert result.verdict == GuardVerdict.ALLOWED
