"""Tests for Serializer — SPEC §3.7, PLAN T9.4."""

import time

from harness.memory.serializer import Serializer
from harness.models.feedback import (
    Feedback,
    FeedbackMetadata,
    FeedbackSource,
    Severity,
)
from harness.models.memory_entry import MemoryEntry
from harness.models.persist_decision import PersistDecision, PersistOutcome


def _make_feedback(
    source: FeedbackSource = FeedbackSource.MEMORY,
    severity: Severity = Severity.INFO,
    payload: dict | None = None,
    source_round: int = 3,
) -> Feedback:
    if payload is None:
        payload = {"key": "value"}
    return Feedback(
        fingerprint="abc123",
        source=source,
        severity=severity,
        payload=payload,
        metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
        round=source_round,
        timestamp=time.time(),
        tool_call=None,
        correlation_id=None,
    )


def _make_persist_decision(
    outcome: PersistOutcome = PersistOutcome.PERSIST,
    category: str | None = "SUMMARY",
) -> PersistDecision:
    return PersistDecision(
        decision=outcome,
        reason="Test reason",
        category=category,
    )


# ---------------------------------------------------------------------------
# PERSIST → MemoryEntry
# ---------------------------------------------------------------------------


class TestPersistSerialization:
    def test_persist_produces_memory_entry(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision(PersistOutcome.PERSIST, "SUMMARY")
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert isinstance(result, MemoryEntry)

    def test_memory_entry_has_correct_category(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision(PersistOutcome.PERSIST, "DECISION")
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert result.category == "DECISION"

    def test_memory_entry_has_unique_id(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision()
        result1 = serializer.serialize(fb, decision)
        result2 = serializer.serialize(fb, decision)
        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id

    def test_memory_entry_contains_timestamp(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision()
        before = time.time()
        result = serializer.serialize(fb, decision)
        after = time.time()
        assert result is not None
        assert before <= result.created_at <= after

    def test_memory_entry_contains_source_round(self) -> None:
        serializer = Serializer()
        fb = _make_feedback(source_round=42)
        decision = _make_persist_decision()
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert result.source_round == 42

    def test_memory_entry_content_is_non_empty_string(self) -> None:
        serializer = Serializer()
        fb = _make_feedback(payload={"command": "ls", "exit_code": 0})
        decision = _make_persist_decision()
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert isinstance(result.content, str)
        assert len(result.content) > 0


# ---------------------------------------------------------------------------
# DISCARD → None
# ---------------------------------------------------------------------------


class TestDiscardSerialization:
    def test_discard_produces_none(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision(PersistOutcome.DISCARD)
        result = serializer.serialize(fb, decision)
        assert result is None


# ---------------------------------------------------------------------------
# Content includes feedback data
# ---------------------------------------------------------------------------


class TestContentFormat:
    def test_content_includes_source(self) -> None:
        serializer = Serializer()
        fb = _make_feedback(source=FeedbackSource.MEMORY)
        decision = _make_persist_decision()
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert "MEMORY" in result.content

    def test_content_includes_payload(self) -> None:
        serializer = Serializer()
        fb = _make_feedback(payload={"task": "Implement login"})
        decision = _make_persist_decision()
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert "Implement login" in result.content


# ---------------------------------------------------------------------------
# Different categories preserved
# ---------------------------------------------------------------------------


class TestCategoryPreservation:
    def test_convention_category(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision(PersistOutcome.PERSIST, "CONVENTION")
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert result.category == "CONVENTION"

    def test_preference_category(self) -> None:
        serializer = Serializer()
        fb = _make_feedback()
        decision = _make_persist_decision(PersistOutcome.PERSIST, "PREFERENCE")
        result = serializer.serialize(fb, decision)
        assert result is not None
        assert result.category == "PREFERENCE"
