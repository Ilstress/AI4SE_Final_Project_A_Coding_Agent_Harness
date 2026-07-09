"""Tests for MemoryStore — SPEC §3.7, PLAN T9.1."""

import json
import os
import tempfile
from pathlib import Path

from harness.memory.store import MemoryStore
from harness.models.memory_entry import MemoryEntry


def _make_entry(
    entry_id: str = "mem-001",
    category: str = "CONVENTION",
    content: str = "Use snake_case",
    created_at: float = 1234567890.0,
    source_round: int = 1,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        category=category,
        content=content,
        created_at=created_at,
        source_round=source_round,
    )


# ---------------------------------------------------------------------------
# Basic read/write
# ---------------------------------------------------------------------------


class TestBasicReadWrite:
    def test_write_then_read_returns_same_entries(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            entries = [
                _make_entry("mem-001", "CONVENTION", "Use snake_case"),
                _make_entry("mem-002", "DECISION", "Use pytest"),
            ]
            store.write(entries)
            result = store.read_all()
            assert len(result) == 2
            assert result[0].id == "mem-001"
            assert result[0].category == "CONVENTION"
            assert result[0].content == "Use snake_case"
            assert result[1].id == "mem-002"
            assert result[1].category == "DECISION"
            assert result[1].content == "Use pytest"
        finally:
            os.unlink(path)

    def test_read_all_returns_list(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            result = store.read_all()
            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Append
# ---------------------------------------------------------------------------


class TestAppend:
    def test_append_adds_to_existing_entries(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            store.write([_make_entry("mem-001", "CONVENTION", "First")])
            store.append(_make_entry("mem-002", "DECISION", "Second"))
            result = store.read_all()
            assert len(result) == 2
            assert result[0].id == "mem-001"
            assert result[1].id == "mem-002"
        finally:
            os.unlink(path)

    def test_append_to_empty_store(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            store.append(_make_entry("mem-001", "CONVENTION", "Only entry"))
            result = store.read_all()
            assert len(result) == 1
            assert result[0].id == "mem-001"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Empty / non-existent file
# ---------------------------------------------------------------------------


class TestEmptyFile:
    def test_empty_file_returns_empty_list(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            path = f.name

        try:
            store = MemoryStore(path)
            result = store.read_all()
            assert result == []
        finally:
            os.unlink(path)

    def test_non_existent_file_returns_empty_list(self) -> None:
        path = str(Path(tempfile.gettempdir()) / "nonexistent_memory.json")
        store = MemoryStore(path)
        result = store.read_all()
        assert result == []


# ---------------------------------------------------------------------------
# Corrupted JSON
# ---------------------------------------------------------------------------


class TestCorruptedFile:
    def test_corrupted_json_returns_empty_list(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("this is not valid json {{{")
            path = f.name

        try:
            store = MemoryStore(path)
            result = store.read_all()
            assert result == []
        finally:
            os.unlink(path)

    def test_valid_json_wrong_structure_returns_empty_list(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not": "a list"}, f)
            path = f.name

        try:
            store = MemoryStore(path)
            result = store.read_all()
            assert result == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Write failure (permission denied)
# ---------------------------------------------------------------------------


class TestWriteFailure:
    def test_write_to_readonly_directory_does_not_crash(self) -> None:
        # Use a path that is impossible to write to (root of a non-existent drive on Windows)
        path = "Z:/nonexistent_drive_xyz/memory.json"
        store = MemoryStore(path)
        # Should not raise
        store.write([_make_entry("mem-001", "CONVENTION", "Test")])
        # read_all should return empty list since file doesn't exist
        result = store.read_all()
        assert result == []


# ---------------------------------------------------------------------------
# Idempotent write
# ---------------------------------------------------------------------------


class TestIdempotentWrite:
    def test_write_overwrites_existing(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            store.write([_make_entry("mem-001", "CONVENTION", "First")])
            store.write([_make_entry("mem-002", "DECISION", "Second")])
            result = store.read_all()
            assert len(result) == 1
            assert result[0].id == "mem-002"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Timestamp and source_round preserved
# ---------------------------------------------------------------------------


class TestFieldPreservation:
    def test_timestamp_and_round_preserved(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            store = MemoryStore(path)
            entry = _make_entry(
                entry_id="mem-001",
                category="SUMMARY",
                content="Task completed",
                created_at=1699999999.0,
                source_round=42,
            )
            store.write([entry])
            result = store.read_all()
            assert len(result) == 1
            assert result[0].created_at == 1699999999.0
            assert result[0].source_round == 42
        finally:
            os.unlink(path)
