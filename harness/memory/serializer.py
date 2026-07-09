"""Serializer — structured JSON serialization for memory entries (SPEC §3.7, PLAN T9.4)."""

import json
import time
import uuid

from harness.models.feedback import Feedback
from harness.models.memory_entry import MemoryEntry
from harness.models.persist_decision import PersistDecision, PersistOutcome


class Serializer:
    """Converts Feedback + PersistDecision into a MemoryEntry.

    MVP: structured JSON serializer.
    LLM-based summarization is a reserved extension point.
    """

    def serialize(
        self, feedback: Feedback, persist_decision: PersistDecision
    ) -> MemoryEntry | None:
        """Serialize a Feedback event into a MemoryEntry.

        Returns:
            MemoryEntry if decision is PERSIST, None if DISCARD.
        """
        if persist_decision.decision == PersistOutcome.DISCARD:
            return None

        content = self._build_content(feedback)
        entry_id = self._generate_id()

        return MemoryEntry(
            id=entry_id,
            category=persist_decision.category or "SUMMARY",
            content=content,
            created_at=time.time(),
            source_round=feedback.round,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_content(feedback: Feedback) -> str:
        """Build a structured JSON content string from the Feedback."""
        data = {
            "source": feedback.source.value,
            "severity": feedback.severity.value,
            "payload": feedback.payload,
        }
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID for a memory entry."""
        return uuid.uuid4().hex[:16]
