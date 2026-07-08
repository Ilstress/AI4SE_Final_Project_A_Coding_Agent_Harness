"""SPEC §6.16: PersistDecision — outcome of MemoryPolicy evaluation."""

from dataclasses import dataclass
from enum import Enum


class PersistOutcome(Enum):
    """Decision outcome for memory persistence."""

    PERSIST = "PERSIST"
    DISCARD = "DISCARD"


@dataclass(frozen=True)
class PersistDecision:
    """Outcome of MemoryPolicy evaluation.

    decision: PERSIST or DISCARD
    reason: rationale for the decision (for audit log)
    category: if PERSIST, the MemoryEntry category; None if DISCARD
    """

    decision: PersistOutcome
    reason: str
    category: str | None
