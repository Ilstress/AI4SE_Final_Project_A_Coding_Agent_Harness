"""MemoryPolicy — deterministic memory persistence policy (SPEC §3.7, PLAN T9.3)."""

from harness.models.feedback import Feedback, FeedbackSource
from harness.models.persist_decision import PersistDecision, PersistOutcome


class MemoryPolicy:
    """Deterministic policy for deciding whether a Feedback event should be persisted.

    Pure code mechanism — NOT LLM judgment.
    Rules are table-driven and deterministic: same input always produces same output.
    Policy decides "whether to persist"; Serializer decides "what to persist".
    """

    # (source, outcome, category)
    _RULES: list[tuple[FeedbackSource, PersistOutcome, str | None]] = [
        (FeedbackSource.MEMORY, PersistOutcome.PERSIST, "SUMMARY"),
    ]

    def evaluate(self, feedback: Feedback) -> PersistDecision:
        """Evaluate whether a Feedback event should be persisted to long-term memory.

        Returns:
            PersistDecision with PERSIST or DISCARD, a reason string, and a category
            (populated only for PERSIST decisions).
        """
        source = feedback.source
        for rule_source, outcome, category in self._RULES:
            if source == rule_source:
                return PersistDecision(
                    decision=outcome,
                    reason=f"Rule matched: source={source.value}",
                    category=category,
                )

        return PersistDecision(
            decision=PersistOutcome.DISCARD,
            reason=f"Default: source={source.value} is not persisted",
            category=None,
        )
