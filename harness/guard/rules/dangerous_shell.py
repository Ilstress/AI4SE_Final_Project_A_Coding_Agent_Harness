"""DangerousShellRule — flags dangerous shell commands (SPEC §3.4)."""

import re

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.rule_result import RuleResult, RuleVerdict

_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\b", "Recursive force-delete"),
    (r":\(\)\s*\{.*:\|:&\s*\};:", "Fork bomb"),
    (r"chmod\s+777\s+/", "World-writable root permissions"),
    (r"\bmkfs\b", "Filesystem format"),
    (r"\bdd\s+if=", "Raw disk write"),
    (r">\s*/dev/sd[a-z]", "Overwrite disk device"),
    (r"\bshutdown\b", "System shutdown"),
    (r"\breboot\b", "System reboot"),
    (r"chown\s+-R\s+", "Recursive ownership change"),
]


class DangerousShellRule(Rule):
    """Flag execute_shell commands matching known dangerous patterns."""

    @property
    def priority(self) -> int:
        return 200

    @property
    def rule_name(self) -> str:
        return "DangerousShellRule"

    def evaluate(self, action: Action) -> RuleResult:
        if action.tool_name != "execute_shell":
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="Not an execute_shell action.",
                evidence={},
            )

        command = action.parameters.get("command")
        if command is None:
            return RuleResult(
                rule_name=self.rule_name,
                verdict=RuleVerdict.ALLOW,
                reason="No command parameter.",
                evidence={},
            )

        for pattern, description in _DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RuleResult(
                    rule_name=self.rule_name,
                    verdict=RuleVerdict.FLAG,
                    reason=f"Dangerous shell pattern detected: {description}",
                    evidence={"command": command, "pattern": pattern},
                )

        return RuleResult(
            rule_name=self.rule_name,
            verdict=RuleVerdict.ALLOW,
            reason="No dangerous shell patterns detected.",
            evidence={"command": command},
        )
