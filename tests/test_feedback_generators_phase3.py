"""Tests for GuardGen, ParserGen, ToolExecGen — SPEC §3.6.1, PLAN T8.3."""

from harness.feedback.generators.base import FeedbackGenerator
from harness.feedback.generators.guard_gen import GuardGen
from harness.feedback.generators.parser_gen import ParserGen
from harness.feedback.generators.tool_exec_gen import ToolExecGen
from harness.models.feedback import FeedbackSource, Severity
from harness.models.guard_result import GuardResult, GuardVerdict
from harness.models.parse_error import ParseError
from harness.models.tool_result import ToolResult

# ---------------------------------------------------------------------------
# GuardGen
# ---------------------------------------------------------------------------


class TestGuardGen:
    def test_source_is_guardrail(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {"guard_result": GuardResult(GuardVerdict.BLOCKED, (), None)}
        )
        assert result.source == FeedbackSource.GUARDRAIL

    def test_blocked_returns_critical(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {"guard_result": GuardResult(GuardVerdict.BLOCKED, (), None)}
        )
        assert result.severity == Severity.CRITICAL

    def test_approval_required_returns_warning(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {
                "guard_result": GuardResult(
                    GuardVerdict.APPROVAL_REQUIRED, (), None
                )
            }
        )
        assert result.severity == Severity.WARNING

    def test_allowed_returns_info(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {"guard_result": GuardResult(GuardVerdict.ALLOWED, (), None)}
        )
        assert result.severity == Severity.INFO

    def test_payload_contains_verdict(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {"guard_result": GuardResult(GuardVerdict.BLOCKED, (), None)}
        )
        assert result.payload["verdict"] == "BLOCKED"

    def test_payload_contains_triggered_rules(self) -> None:
        gen = GuardGen()
        result = gen.generate(
            {"guard_result": GuardResult(GuardVerdict.BLOCKED, (), None)}
        )
        assert isinstance(result.payload["triggered_rules"], list)

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(GuardGen(), FeedbackGenerator)


# ---------------------------------------------------------------------------
# ParserGen
# ---------------------------------------------------------------------------


class TestParserGen:
    def test_source_is_parser(self) -> None:
        gen = ParserGen()
        result = gen.generate(
            {
                "parse_error": ParseError(
                    "UNKNOWN_TOOL", {}, "Unknown tool 'foo'"
                )
            }
        )
        assert result.source == FeedbackSource.PARSER

    def test_unknown_tool_returns_warning(self) -> None:
        gen = ParserGen()
        result = gen.generate(
            {
                "parse_error": ParseError(
                    "UNKNOWN_TOOL", {}, "Unknown tool 'foo'"
                )
            }
        )
        assert result.severity == Severity.WARNING

    def test_malformed_call_returns_error(self) -> None:
        gen = ParserGen()
        result = gen.generate(
            {
                "parse_error": ParseError(
                    "MALFORMED_CALL", {}, "Invalid JSON"
                )
            }
        )
        assert result.severity == Severity.ERROR

    def test_payload_contains_error_type(self) -> None:
        gen = ParserGen()
        result = gen.generate(
            {
                "parse_error": ParseError(
                    "UNKNOWN_TOOL", {}, "Unknown tool 'foo'"
                )
            }
        )
        assert result.payload["error_type"] == "UNKNOWN_TOOL"

    def test_payload_contains_detail(self) -> None:
        gen = ParserGen()
        result = gen.generate(
            {
                "parse_error": ParseError(
                    "MALFORMED_CALL", {}, "Invalid JSON"
                )
            }
        )
        assert result.payload["detail"] == "Invalid JSON"

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(ParserGen(), FeedbackGenerator)


# ---------------------------------------------------------------------------
# ToolExecGen
# ---------------------------------------------------------------------------


class TestToolExecGen:
    def test_source_is_tool_executor(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {"tool_result": ToolResult(False, None, None, None, "FILE_NOT_FOUND", 10)}
        )
        assert result.source == FeedbackSource.TOOL_EXECUTOR

    def test_file_not_found_returns_error(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {"tool_result": ToolResult(False, None, None, None, "FILE_NOT_FOUND", 10)}
        )
        assert result.severity == Severity.ERROR

    def test_permission_denied_returns_error(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {
                "tool_result": ToolResult(
                    False, None, None, None, "PERMISSION_DENIED", 10
                )
            }
        )
        assert result.severity == Severity.ERROR

    def test_success_returns_info(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {"tool_result": ToolResult(True, 0, "ok", None, None, 10)}
        )
        assert result.severity == Severity.INFO

    def test_payload_contains_error(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {"tool_result": ToolResult(False, None, None, None, "FILE_NOT_FOUND", 10)}
        )
        assert result.payload["error"] == "FILE_NOT_FOUND"

    def test_payload_contains_success(self) -> None:
        gen = ToolExecGen()
        result = gen.generate(
            {"tool_result": ToolResult(False, None, None, None, "FILE_NOT_FOUND", 10)}
        )
        assert result.payload["success"] is False

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(ToolExecGen(), FeedbackGenerator)
