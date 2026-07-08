"""Tests for RuleEngine — SPEC §3.4, PLAN T7.2."""

from harness.guard.rule_engine import RuleEngine
from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.approval import ApprovalRequest
from harness.models.guard_result import GuardVerdict
from harness.models.rule_result import RuleResult, RuleVerdict


class _SpyRule(Rule):
    """A rule that returns a preset verdict and records whether it was evaluated."""

    def __init__(
        self,
        verdict: RuleVerdict,
        priority: int = 100,
        name: str = "spy",
    ) -> None:
        super().__init__("/tmp/ws")
        self._verdict = verdict
        self._priority = priority
        self._name = name
        self.was_evaluated = False

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def rule_name(self) -> str:
        return self._name

    def evaluate(self, action: Action) -> RuleResult:
        self.was_evaluated = True
        return RuleResult(
            rule_name=self._name,
            verdict=self._verdict,
            reason=f"Spy rule {self._name}",
            evidence={"name": self._name},
        )


class _FailingRule(Rule):
    """A rule that raises an exception during evaluation."""

    def __init__(self, priority: int = 100) -> None:
        super().__init__("/tmp/ws")
        self._priority = priority

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def rule_name(self) -> str:
        return "FailingRule"

    def evaluate(self, action: Action) -> RuleResult:
        raise RuntimeError("Simulated failure")


def _make_action() -> Action:
    return Action(
        tool_name="read_file", parameters={"path": "test.py"}, raw_response={}
    )


def _make_engine(*rules: Rule) -> RuleEngine:
    return RuleEngine(list(rules))


# ---------------------------------------------------------------------------
# Allowed
# ---------------------------------------------------------------------------


class TestAllAllowed:
    def test_all_rules_allow_returns_allowed(self) -> None:
        engine = _make_engine(
            _SpyRule(RuleVerdict.ALLOW, priority=100, name="r1"),
            _SpyRule(RuleVerdict.ALLOW, priority=200, name="r2"),
        )
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.ALLOWED
        assert result.approval_request is None
        assert len(result.rule_results) == 2

    def test_empty_rules_returns_allowed(self) -> None:
        engine = _make_engine()
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.ALLOWED
        assert len(result.rule_results) == 0


# ---------------------------------------------------------------------------
# Blocked
# ---------------------------------------------------------------------------


class TestBlocked:
    def test_block_returns_blocked(self) -> None:
        engine = _make_engine(
            _SpyRule(RuleVerdict.ALLOW, priority=100, name="r1"),
            _SpyRule(RuleVerdict.BLOCK, priority=200, name="r2"),
        )
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.BLOCKED
        assert result.approval_request is None

    def test_block_short_circuits_remaining_rules(self) -> None:
        r1 = _SpyRule(RuleVerdict.BLOCK, priority=100, name="blocker")
        r2 = _SpyRule(RuleVerdict.ALLOW, priority=200, name="never_reached")

        engine = _make_engine(r1, r2)
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.BLOCKED
        assert r1.was_evaluated is True
        assert r2.was_evaluated is False
        assert len(result.rule_results) == 1

    def test_block_before_flag_short_circuits(self) -> None:
        r1 = _SpyRule(RuleVerdict.BLOCK, priority=100, name="blocker")
        r2 = _SpyRule(RuleVerdict.FLAG, priority=200, name="flagger")

        engine = _make_engine(r1, r2)
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.BLOCKED
        assert r2.was_evaluated is False


# ---------------------------------------------------------------------------
# Approval Required
# ---------------------------------------------------------------------------


class TestApprovalRequired:
    def test_flag_returns_approval_required(self) -> None:
        engine = _make_engine(
            _SpyRule(RuleVerdict.ALLOW, priority=100, name="r1"),
            _SpyRule(RuleVerdict.FLAG, priority=200, name="r2"),
        )
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.APPROVAL_REQUIRED
        assert result.approval_request is not None
        assert isinstance(result.approval_request, ApprovalRequest)

    def test_flag_produces_approval_request_with_evidence(self) -> None:
        rule = _SpyRule(RuleVerdict.FLAG, priority=200, name="flagger")
        engine = _make_engine(rule)
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.APPROVAL_REQUIRED
        req = result.approval_request
        assert req is not None
        assert "Spy rule flagger" in req.description
        assert len(req.evidence) == 1
        assert req.evidence[0]["name"] == "flagger"

    def test_multiple_flags_collected(self) -> None:
        r1 = _SpyRule(RuleVerdict.FLAG, priority=200, name="f1")
        r2 = _SpyRule(RuleVerdict.FLAG, priority=200, name="f2")
        engine = _make_engine(r1, r2)
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.APPROVAL_REQUIRED
        assert len(result.rule_results) == 2
        req = result.approval_request
        assert req is not None
        assert "f1" in req.description
        assert "f2" in req.description

    def test_approval_request_has_timestamp(self) -> None:
        engine = _make_engine(
            _SpyRule(RuleVerdict.FLAG, priority=200, name="f1"),
        )
        result = engine.evaluate(_make_action())

        assert result.approval_request is not None
        assert result.approval_request.timestamp > 0


# ---------------------------------------------------------------------------
# Exception → BLOCK (safety-first)
# ---------------------------------------------------------------------------


class TestExceptionBecomesBlock:
    def test_rule_exception_becomes_block(self) -> None:
        engine = _make_engine(
            _SpyRule(RuleVerdict.ALLOW, priority=100, name="r1"),
            _FailingRule(priority=200),
        )
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.BLOCKED
        assert len(result.rule_results) == 2
        assert result.rule_results[1].verdict == RuleVerdict.BLOCK
        assert "Simulated failure" in result.rule_results[1].reason

    def test_exception_in_first_rule_blocks_immediately(self) -> None:
        engine = _make_engine(
            _FailingRule(priority=100),
            _SpyRule(RuleVerdict.ALLOW, priority=200, name="never_reached"),
        )
        result = engine.evaluate(_make_action())

        assert result.verdict == GuardVerdict.BLOCKED
        assert len(result.rule_results) == 1


# ---------------------------------------------------------------------------
# Priority Ordering
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    def test_rules_evaluated_in_priority_order(self) -> None:
        r_high = _SpyRule(RuleVerdict.ALLOW, priority=100, name="high")
        r_low = _SpyRule(RuleVerdict.ALLOW, priority=200, name="low")

        # Pass in reverse order; engine must sort by priority
        engine = _make_engine(r_low, r_high)
        result = engine.evaluate(_make_action())

        names = [r.rule_name for r in result.rule_results]
        assert names == ["high", "low"]

    def test_priority_100_evaluated_before_200(self) -> None:
        eval_order: list[str] = []

        class _OrderedRule(Rule):
            def __init__(self, name: str, priority: int) -> None:
                super().__init__("/tmp/ws")
                self._name = name
                self._priority = priority

            @property
            def priority(self) -> int:
                return self._priority

            @property
            def rule_name(self) -> str:
                return self._name

            def evaluate(self, action: Action) -> RuleResult:
                eval_order.append(self._name)
                return RuleResult(self._name, RuleVerdict.ALLOW, "ok", {})

        engine = _make_engine(
            _OrderedRule("third", 300),
            _OrderedRule("first", 100),
            _OrderedRule("second", 200),
        )
        engine.evaluate(_make_action())

        assert eval_order == ["first", "second", "third"]
