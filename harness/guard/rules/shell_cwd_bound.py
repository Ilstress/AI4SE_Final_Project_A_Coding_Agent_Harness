"""ShellCWDBoundRule — blocks shell commands whose cwd is outside the workspace (SPEC §3.4)."""

from pathlib import Path

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.rule_result import RuleResult, RuleVerdict


class ShellCWDBoundRule(Rule):
    """Block execute_shell actions whose cwd falls outside the workspace."""

    @property
    def priority(self) -> int:
        return 100

    @property
    def rule_name(self) -> str:
        return "ShellCWDBoundRule"

    def evaluate(self, action: Action) -> RuleResult:
        if action.tool_name != "execute_shell":
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="Not an execute_shell action.",
                evidence={},
            )

        cwd = action.parameters.get("cwd")
        if cwd is None:
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="No cwd specified; defaults to workspace root.",
                evidence={},
            )

        workspace = Path(self._workspace_root).resolve()
        target = (workspace / cwd).resolve()

        try:
            target.relative_to(workspace)
        except ValueError:
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.BLOCK,
                reason=f"Shell cwd '{cwd}' resolves outside the workspace.",
                evidence={
                    "cwd": cwd,
                    "workspace_root": str(workspace),
                    "resolved": str(target),
                },
            )

        return RuleResult(
            rule_name=self.rule_name,
            verdict=RuleVerdict.ALLOW,
            reason="Shell cwd is within the workspace.",
            evidence={"cwd": cwd, "resolved": str(target)},
        )
