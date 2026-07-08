"""MockApprovalProvider — returns preset responses for testing."""

from harness.guard.approval.base import HumanApprovalProvider
from harness.models.approval import ApprovalRequest, ApprovalResult


class MockApprovalProvider(HumanApprovalProvider):
    """Returns a pre-programmed sequence of ApprovalResults.

    Responses are consumed in order.  Once exhausted, the last response
    is returned for every subsequent call.
    """

    def __init__(self, responses: list[ApprovalResult]) -> None:
        self._responses = responses
        self._index = 0
        self.call_count = 0

    def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        self.call_count += 1
        if self._index < len(self._responses):
            result = self._responses[self._index]
            self._index += 1
            return result
        return self._responses[-1]
