"""SPEC §6.7: RuleResult — result of a single rule evaluation."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuleVerdict(Enum):
    """Verdict of a single rule evaluation."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    FLAG = "FLAG"


@dataclass(frozen=True)
class RuleResult:
    """Result of a single rule evaluation.

    Contains the rule identifier, verdict, human-readable reason, and supporting evidence.
    """

    rule_name: str
    verdict: RuleVerdict
    reason: str
    evidence: dict[str, Any]
