"""Tests for MemoryRetriever — SPEC §3.7, PLAN T9.2."""

import os
import tempfile

from harness.memory.retriever import MemoryRetriever
from harness.memory.store import MemoryStore
from harness.models.memory_entry import MemoryEntry


def _temp_store() -> tuple[MemoryStore, str]:
    """Create a MemoryStore backed by a temporary file. Returns (store, path)."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    return MemoryStore(path), path


def _make_entry(
    entry_id: str,
    category: str = "CONVENTION",
    content: str = "Test content",
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        category=category,
        content=content,
        created_at=1234567890.0,
        source_round=1,
    )


# ---------------------------------------------------------------------------
# Full injection: retrieve returns all entries
# ---------------------------------------------------------------------------


class TestFullInjection:
    def test_three_entries_returns_all_three(self) -> None:
        store, path = _temp_store()
        try:
            entries = [
                _make_entry("mem-001", "CONVENTION", "Use snake_case"),
                _make_entry("mem-002", "DECISION", "Use pytest"),
                _make_entry("mem-003", "PREFERENCE", "Dark mode"),
            ]
            store.write(entries)

            retriever = MemoryRetriever(store)
            result = retriever.retrieve("Write a function")
            assert len(result) == 3
            assert result[0].id == "mem-001"
            assert result[1].id == "mem-002"
            assert result[2].id == "mem-003"
        finally:
            os.unlink(path)

    def test_empty_store_returns_empty_list(self) -> None:
        store, path = _temp_store()
        try:
            store.write([])

            retriever = MemoryRetriever(store)
            result = retriever.retrieve("Any task")
            assert result == []
        finally:
            os.unlink(path)

    def test_returns_list(self) -> None:
        store, path = _temp_store()
        try:
            store.write([_make_entry("mem-001")])

            retriever = MemoryRetriever(store)
            result = retriever.retrieve("Some task")
            assert isinstance(result, list)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Task string does not affect current implementation
# ---------------------------------------------------------------------------


class TestTaskAgnostic:
    def test_different_tasks_return_same_result(self) -> None:
        store, path = _temp_store()
        try:
            entries = [
                _make_entry("mem-001", "CONVENTION", "Use snake_case"),
                _make_entry("mem-002", "DECISION", "Use pytest"),
            ]
            store.write(entries)

            retriever = MemoryRetriever(store)
            result1 = retriever.retrieve("Write a function")
            result2 = retriever.retrieve("Fix a bug")
            result3 = retriever.retrieve("")
            assert result1 == result2 == result3
        finally:
            os.unlink(path)

    def test_task_string_not_used_for_filtering(self) -> None:
        store, path = _temp_store()
        try:
            entries = [
                _make_entry("mem-001", "CONVENTION", "Use snake_case"),
                _make_entry("mem-002", "DECISION", "Use pytest"),
                _make_entry("mem-003", "SUMMARY", "Completed login"),
            ]
            store.write(entries)

            retriever = MemoryRetriever(store)
            # Even with a very specific task, all entries are returned
            result = retriever.retrieve("Implement login page with React")
            assert len(result) == 3
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Accepts MemoryStore at construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_accepts_memory_store(self) -> None:
        store, path = _temp_store()
        try:
            retriever = MemoryRetriever(store)
            assert retriever._store is store
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Retrieval returns MemoryEntry instances
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_memory_entry_instances(self) -> None:
        store, path = _temp_store()
        try:
            store.write([_make_entry("mem-001", "CONVENTION", "Use snake_case")])

            retriever = MemoryRetriever(store)
            result = retriever.retrieve("task")
            assert len(result) == 1
            entry = result[0]
            assert isinstance(entry, MemoryEntry)
            assert entry.id == "mem-001"
            assert entry.category == "CONVENTION"
            assert entry.content == "Use snake_case"
            assert entry.created_at == 1234567890.0
            assert entry.source_round == 1
        finally:
            os.unlink(path)
