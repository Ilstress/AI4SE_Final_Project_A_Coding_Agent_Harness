"""FileReadBoundRule — blocks reads outside the workspace (SPEC §3.4)."""

from pathlib import Path

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.rule_result import RuleResult, RuleVerdict


class FileReadBoundRule(Rule):
    """Block read_file actions whose target path falls outside the workspace."""

    @property
    def priority(self) -> int:
        return 100

    @property
    def rule_name(self) -> str:
        return "FileReadBoundRule"

    def evaluate(self, action: Action) -> RuleResult:
        if action.tool_name != "read_file":
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="Not a read_file action.",
                evidence={},
            )

        path = action.parameters.get("path")
        if path is None:
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="No path parameter.",
                evidence={},
            )

        workspace = Path(self._workspace_root).resolve()
        target = (workspace / path).resolve()

        try:
            target.relative_to(workspace)
        except ValueError:
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.BLOCK,
                reason=f"Read path '{path}' resolves outside the workspace.",
                evidence={
                    "path": path,
                    "workspace_root": str(workspace),
                    "resolved": str(target),
                },
            )

        return RuleResult(
            rule_name=self.rule_name,
            verdict=RuleVerdict.ALLOW,
            reason="Read path is within the workspace.",
            evidence={"path": path, "resolved": str(target)},
        )
