"""RuleEngine — priority-sorted rule evaluation with short-circuit (SPEC §3.4)."""

import time
from collections.abc import Sequence

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.approval import ApprovalRequest
from harness.models.guard_result import GuardResult, GuardVerdict
from harness.models.rule_result import RuleResult, RuleVerdict


class RuleEngine:
    """Evaluates actions against a priority-sorted list of Rules.

    BLOCK  → immediate short-circuit; no further rules evaluated.
    FLAG   → collected; continue evaluating remaining rules.
    ALLOW  → continue.

    Stateless — holds no session state.  All state is owned by Main Loop.
    """

    def __init__(self, rules: Sequence[Rule]) -> None:
        self._rules: list[Rule] = sorted(rules, key=lambda r: r.priority)

    def evaluate(self, action: Action) -> GuardResult:
        """Evaluate *action* against all rules in priority order.

        Returns:
            GuardResult with verdict ALLOWED, BLOCKED, or APPROVAL_REQUIRED.
        """
        rule_results: list[RuleResult] = []
        flagged: list[RuleResult] = []

        for rule in self._rules:
            try:
                result = rule.evaluate(action)
            except Exception as exc:
                result = RuleResult(
                    rule_name=rule.rule_name,
                    verdict=RuleVerdict.BLOCK,
                    reason=f"Rule '{rule.rule_name}' raised an exception: {exc}",
                    evidence={"exception": str(exc)},
                )

            rule_results.append(result)

            if result.verdict == RuleVerdict.BLOCK:
                return GuardResult(
                    verdict=GuardVerdict.BLOCKED,
                    rule_results=tuple(rule_results),
                    approval_request=None,
                )

            if result.verdict == RuleVerdict.FLAG:
                flagged.append(result)

        if flagged:
            description = "; ".join(r.reason for r in flagged)
            evidence = [dict(r.evidence) for r in flagged]
            return GuardResult(
                verdict=GuardVerdict.APPROVAL_REQUIRED,
                rule_results=tuple(rule_results),
                approval_request=ApprovalRequest(
                    description=description,
                    evidence=evidence,
                    timestamp=time.time(),
                ),
            )

        return GuardResult(
            verdict=GuardVerdict.ALLOWED,
            rule_results=tuple(rule_results),
            approval_request=None,
        )
