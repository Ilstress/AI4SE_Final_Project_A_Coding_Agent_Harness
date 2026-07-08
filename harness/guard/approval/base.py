"""HumanApprovalProvider ABC — SPEC §3.6.4."""

from abc import ABC, abstractmethod

from harness.models.approval import ApprovalRequest, ApprovalResult


class HumanApprovalProvider(ABC):
    """Abstract interface for human-in-the-loop approval.

    Implementations handle the I/O of asking a human to approve or reject
    an action.  Timeout handling is the responsibility of Main Loop, not
    the provider.
    """

    @abstractmethod
    def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """Present *request* to the human and return their decision."""
        ...
