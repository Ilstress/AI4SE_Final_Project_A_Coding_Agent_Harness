"""Guardrail — security boundary facade (SPEC §3.4)."""

import logging

from harness.guard.approval.base import HumanApprovalProvider
from harness.guard.rule_engine import RuleEngine
from harness.models.action import Action
from harness.models.guard_result import GuardResult, GuardVerdict

logger = logging.getLogger(__name__)


class Guardrail:
    """Security boundary that composes RuleEngine + HumanApprovalProvider.

    Every action passes through Guardrail.evaluate() before execution.
    Guardrail delegates to RuleEngine for rule evaluation and exposes
    the HumanApprovalProvider via ``approval_provider`` for use by Main
    Loop when approval is needed.

    Guardrail does not execute approval interactions — it only produces
    GuardResult.  The Main Loop reads the verdict and decides whether to
    call the approval provider.
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        approval_provider: HumanApprovalProvider,
    ) -> None:
        self._rule_engine = rule_engine
        self.approval_provider = approval_provider

    def evaluate(self, action: Action) -> GuardResult:
        """Evaluate *action* through the security boundary.

        All actions — including read_file and task_complete — must pass
        through this method.
        """
        result = self._rule_engine.evaluate(action)

        if result.verdict == GuardVerdict.BLOCKED:
            logger.warning(
                "Action BLOCKED: tool=%s, rules=%s",
                action.tool_name,
                [r.rule_name for r in result.rule_results],
            )
        elif result.verdict == GuardVerdict.APPROVAL_REQUIRED:
            logger.warning(
                "Action REQUIRES APPROVAL: tool=%s, rules=%s",
                action.tool_name,
                [r.rule_name for r in result.rule_results],
            )
        else:
            logger.debug(
                "Action ALLOWED: tool=%s", action.tool_name,
            )

        return result
