"""SPEC §6.8–6.9: ApprovalRequest and ApprovalResult."""

from dataclasses import dataclass
from enum import Enum


class ApprovalOutcome(Enum):
    """Outcome of a human approval interaction."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class ApprovalRequest:
    """Human approval request produced by GovernanceController.

    description: human-readable description of the action pending approval
    evidence: supporting evidence from the triggering rules
    timestamp: time the request was created
    """

    description: str
    evidence: list[dict]
    timestamp: float


@dataclass(frozen=True)
class ApprovalResult:
    """Result of a human approval interaction.

    result: APPROVED, REJECTED, or TIMEOUT
    """

    result: ApprovalOutcome
