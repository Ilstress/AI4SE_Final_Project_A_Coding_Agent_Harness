"""NetworkExfilRule — flags potential data exfiltration (SPEC §3.4)."""

import re

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.rule_result import RuleResult, RuleVerdict

_EXFIL_PATTERNS: list[tuple[str, str]] = [
    (r"curl\s+.*\|.*\b(bash|sh|zsh|python|perl)\b", "curl piped to interpreter"),
    (r"wget\s+.*\|.*\b(bash|sh|zsh|python|perl)\b", "wget piped to interpreter"),
    (r"curl\s+.*-F\s+\S+=", "curl multipart file upload"),
    (r"\bnc\s+.*\b\d{1,5}\b", "netcat connection to port"),
    (r"\bncat\s+.*\b\d{1,5}\b", "ncat connection to port"),
    (r"\bscp\s+", "secure copy to remote host"),
    (r"\brsync\s+.*\b\d{1,5}\b", "rsync to remote host"),
]


class NetworkExfilRule(Rule):
    """Flag execute_shell commands that may exfiltrate data."""

    @property
    def priority(self) -> int:
        return 200

    @property
    def rule_name(self) -> str:
        return "NetworkExfilRule"

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

        for pattern, description in _EXFIL_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RuleResult(
                    rule_name=self.rule_name,
                    verdict=RuleVerdict.FLAG,
                    reason=f"Potential data exfiltration detected: {description}",
                    evidence={"command": command, "pattern": pattern},
                )

        return RuleResult(
            rule_name=self.rule_name,
            verdict=RuleVerdict.ALLOW,
            reason="No data exfiltration patterns detected.",
            evidence={"command": command},
        )
