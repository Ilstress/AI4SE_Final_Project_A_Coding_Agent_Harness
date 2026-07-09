"""MemoryRetriever — full-injection memory retrieval (SPEC §3.7, PLAN T9.2)."""

from harness.memory.store import MemoryStore
from harness.models.memory_entry import MemoryEntry


class MemoryRetriever:
    """Loads memory entries for a given task.

    MVP implementation: full injection — returns all stored entries.
    The task string is accepted but not used for filtering.
    The interface is designed to be replaceable (future: keyword/embedding-based retrieval).
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def retrieve(self, task: str) -> list[MemoryEntry]:
        """Return all memory entries for the given task.

        Current implementation: full injection (loads all entries).
        Future: may filter or rank by task relevance.
        """
        return self._store.read_all()
