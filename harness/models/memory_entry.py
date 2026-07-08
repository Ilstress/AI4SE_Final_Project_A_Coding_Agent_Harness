"""SPEC §6.12: MemoryEntry — single record in long-term memory store."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryEntry:
    """A single entry in the long-term memory store.

    category: 'CONVENTION', 'DECISION', 'PREFERENCE', or 'SUMMARY'
    """

    id: str
    category: str
    content: str
    created_at: float
    source_round: int
