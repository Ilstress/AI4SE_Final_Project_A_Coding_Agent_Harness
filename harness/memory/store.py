"""MemoryStore — file-based memory persistence (SPEC §3.7, PLAN T9.1)."""

import json
import logging
import os
from dataclasses import asdict

from harness.models.memory_entry import MemoryEntry

logger = logging.getLogger(__name__)


class MemoryStore:
    """Pure file I/O for reading and writing memory entries to a JSON file.

    Does NOT interpret content — only reads and writes.
    All errors are non-fatal: corrupted files return empty, write failures log and continue.
    """

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_all(self) -> list[MemoryEntry]:
        """Read all memory entries from the JSON file.

        Returns:
            List of MemoryEntry objects. Empty list if file doesn't exist,
            is empty, or contains corrupted JSON.
        """
        if not os.path.exists(self._file_path):
            return []

        try:
            with open(self._file_path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            logger.warning("MemoryStore: cannot read file %s", self._file_path)
            return []

        if not content.strip():
            return []

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("MemoryStore: corrupted JSON in %s, starting with empty memory", self._file_path)
            return []

        if not isinstance(data, list):
            logger.warning("MemoryStore: expected JSON array in %s, got %s", self._file_path, type(data).__name__)
            return []

        entries: list[MemoryEntry] = []
        for item in data:
            try:
                entry = MemoryEntry(
                    id=item["id"],
                    category=item["category"],
                    content=item["content"],
                    created_at=item["created_at"],
                    source_round=item["source_round"],
                )
                entries.append(entry)
            except (KeyError, TypeError) as exc:
                logger.warning("MemoryStore: skipping malformed entry in %s: %s", self._file_path, exc)
        return entries

    def write(self, entries: list[MemoryEntry]) -> None:
        """Write entries to the JSON file, overwriting existing content.

        Write failures are logged but do not raise.
        """
        data = [asdict(entry) for entry in entries]
        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("MemoryStore: failed to write to %s: %s", self._file_path, exc)

    def append(self, entry: MemoryEntry) -> None:
        """Append a single entry to the memory file.

        Reads existing entries, appends the new one, and writes back.
        """
        existing = self.read_all()
        existing.append(entry)
        self.write(existing)
