"""DBDestructiveRule — flags destructive database commands (SPEC §3.4)."""

import re

from harness.guard.rules.base import Rule
from harness.models.action import Action
from harness.models.rule_result import RuleResult, RuleVerdict

_DB_DESTRUCTIVE_PATTERNS: list[tuple[str, str]] = [
    (r"\bDROP\s+TABLE\b", "DROP TABLE statement"),
    (r"\bDROP\s+DATABASE\b", "DROP DATABASE statement"),
    (r"\bDROP\s+INDEX\b", "DROP INDEX statement"),
    (r"\bDROP\s+SCHEMA\b", "DROP SCHEMA statement"),
    (r"\bDELETE\s+FROM\b", "DELETE FROM statement"),
    (r"\bTRUNCATE\b", "TRUNCATE statement"),
    (r"\bALTER\s+TABLE\s+\w+\s+DROP\b", "ALTER TABLE ... DROP"),
]


class DBDestructiveRule(Rule):
    """Flag execute_shell commands containing destructive SQL statements."""

    @property
    def priority(self) -> int:
        return 200

    @property
    def rule_name(self) -> str:
        return "DBDestructiveRule"

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

        for pattern, description in _DB_DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RuleResult(
                    rule_name=self.rule_name,
                    verdict=RuleVerdict.FLAG,
                    reason=f"Destructive database operation detected: {description}",
                    evidence={"command": command, "pattern": pattern},
                )

        return RuleResult(
            rule_name=self.rule_name,
            verdict=RuleVerdict.ALLOW,
            reason="No destructive database patterns detected.",
            evidence={"command": command},
        )
