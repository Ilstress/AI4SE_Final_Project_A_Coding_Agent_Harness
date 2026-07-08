"""Tests for HumanApprovalProvider — SPEC §3.6.4, PLAN T7.3."""

from unittest.mock import patch

from harness.guard.approval.base import HumanApprovalProvider
from harness.guard.approval.mock import MockApprovalProvider
from harness.guard.approval.terminal import TerminalApprovalProvider
from harness.models.approval import ApprovalOutcome, ApprovalRequest, ApprovalResult


def _make_request() -> ApprovalRequest:
    return ApprovalRequest(
        description="Test action needs approval",
        evidence=[{"rule": "TestRule", "reason": "Test reason"}],
        timestamp=1234567890.0,
    )


# ---------------------------------------------------------------------------
# MockApprovalProvider
# ---------------------------------------------------------------------------


class TestMockApprovalProvider:
    def test_returns_approved(self) -> None:
        provider = MockApprovalProvider(
            [ApprovalResult(ApprovalOutcome.APPROVED)]
        )
        result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.APPROVED

    def test_returns_rejected(self) -> None:
        provider = MockApprovalProvider(
            [ApprovalResult(ApprovalOutcome.REJECTED)]
        )
        result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.REJECTED

    def test_returns_responses_in_sequence(self) -> None:
        provider = MockApprovalProvider(
            [
                ApprovalResult(ApprovalOutcome.APPROVED),
                ApprovalResult(ApprovalOutcome.REJECTED),
                ApprovalResult(ApprovalOutcome.APPROVED),
            ]
        )
        assert provider.request_approval(_make_request()).result == ApprovalOutcome.APPROVED
        assert provider.request_approval(_make_request()).result == ApprovalOutcome.REJECTED
        assert provider.request_approval(_make_request()).result == ApprovalOutcome.APPROVED

    def test_exhausted_returns_last(self) -> None:
        provider = MockApprovalProvider(
            [ApprovalResult(ApprovalOutcome.REJECTED)]
        )
        provider.request_approval(_make_request())
        # Exhausted — should return last response
        result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.REJECTED

    def test_call_count_tracks_invocations(self) -> None:
        provider = MockApprovalProvider(
            [
                ApprovalResult(ApprovalOutcome.APPROVED),
                ApprovalResult(ApprovalOutcome.APPROVED),
            ]
        )
        assert provider.call_count == 0
        provider.request_approval(_make_request())
        assert provider.call_count == 1
        provider.request_approval(_make_request())
        assert provider.call_count == 2

    def test_implements_abstract_interface(self) -> None:
        provider = MockApprovalProvider([])
        assert isinstance(provider, HumanApprovalProvider)


# ---------------------------------------------------------------------------
# TerminalApprovalProvider
# ---------------------------------------------------------------------------


class TestTerminalApprovalProvider:
    def test_approve_on_y_input(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", return_value="y"):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.APPROVED

    def test_approve_on_yes_input(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", return_value="yes"):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.APPROVED

    def test_reject_on_n_input(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", return_value="n"):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.REJECTED

    def test_reject_on_no_input(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", return_value="no"):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.REJECTED

    def test_retry_on_invalid_then_accept(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", side_effect=["maybe", "y"]):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.APPROVED

    def test_case_insensitive(self) -> None:
        provider = TerminalApprovalProvider()
        with patch("builtins.input", return_value="Y"):
            result = provider.request_approval(_make_request())
        assert result.result == ApprovalOutcome.APPROVED

    def test_implements_abstract_interface(self) -> None:
        provider = TerminalApprovalProvider()
        assert isinstance(provider, HumanApprovalProvider)
