"""Rule abstract base class — SPEC §3.4."""

from abc import ABC, abstractmethod

from harness.models.action import Action
from harness.models.rule_result import RuleResult


class Rule(ABC):
    """Abstract rule evaluated by the RuleEngine before tool execution.

    Each rule inspects an Action and returns a RuleResult with one of:
        ALLOW  — the action is safe; proceed
        BLOCK  — the action is forbidden; stop immediately
        FLAG   — the action is suspicious; request human approval
    """

    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = workspace_root

    @property
    @abstractmethod
    def priority(self) -> int:
        """Lower values evaluate first.  100 = hard-boundary, 200 = heuristic."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique human-readable rule identifier."""

    @abstractmethod
    def evaluate(self, action: Action) -> RuleResult:
        """Evaluate *action* and return a RuleResult."""
