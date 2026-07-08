"""SPEC §6.6: GuardResult — result of guardrail evaluation on an action."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GuardVerdict(Enum):
    """Verdict of a guardrail evaluation."""

    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class GuardResult:
    """Result of guardrail evaluation on an action.

    Constraints:
        - GuardResult is immutable.
        - When verdict is ALLOWED, rule_results is empty.
        - approval_request is only non-None when verdict is APPROVAL_REQUIRED.
    """

    verdict: GuardVerdict
    rule_results: tuple[Any, ...]  # tuple[RuleResult, ...] (forward reference)
    approval_request: Any | None  # ApprovalRequest | None (forward reference)
