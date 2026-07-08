"""TerminalApprovalProvider — interactive terminal-based HITL approval."""

from harness.guard.approval.base import HumanApprovalProvider
from harness.models.approval import ApprovalOutcome, ApprovalRequest, ApprovalResult


class TerminalApprovalProvider(HumanApprovalProvider):
    """Prompts the user via stdin/stdout for approval decisions."""

    def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        self._display(request)

        while True:
            try:
                response = input("Approve? [y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return ApprovalResult(ApprovalOutcome.REJECTED)

            if response in ("y", "yes"):
                return ApprovalResult(ApprovalOutcome.APPROVED)
            if response in ("n", "no"):
                return ApprovalResult(ApprovalOutcome.REJECTED)

            print("Please answer 'y' or 'n'.")

    @staticmethod
    def _display(request: ApprovalRequest) -> None:
        print("=" * 60)
        print("HUMAN APPROVAL REQUIRED")
        print("=" * 60)
        print(f"\n{request.description}\n")
        if request.evidence:
            print("Evidence:")
            for i, item in enumerate(request.evidence, 1):
                for key, value in item.items():
                    print(f"  [{i}] {key}: {value}")
        print()
