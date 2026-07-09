"""Tests for ShellGen — SPEC §3.6.1, PLAN T8.1."""

from harness.feedback.generators.base import FeedbackGenerator
from harness.feedback.generators.shell_gen import ShellGen
from harness.models.feedback import FeedbackSource, Severity
from harness.models.tool_result import ToolResult


def _make_result(
    success: bool,
    exit_code: int | None = 0,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None,
    duration_ms: int = 10,
) -> ToolResult:
    return ToolResult(
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error=error,
        duration_ms=duration_ms,
    )


def _raw_data(command: str, tool_result: ToolResult) -> dict:
    return {"command": command, "tool_result": tool_result}


# ---------------------------------------------------------------------------
# Successful shell
# ---------------------------------------------------------------------------


class TestSuccessfulShell:
    def test_returns_shell_source(self) -> None:
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.source == FeedbackSource.SHELL

    def test_success_returns_info_severity(self) -> None:
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.severity == Severity.INFO

    def test_payload_contains_command(self) -> None:
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.payload["command"] == "echo hello"

    def test_payload_contains_exit_code(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data("echo hello", _make_result(True, exit_code=0))
        )
        assert result.payload["exit_code"] == 0

    def test_payload_contains_stdout(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data("echo hello", _make_result(True, stdout="hello"))
        )
        assert result.payload["stdout"] == "hello"

    def test_payload_contains_stderr(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data("echo hello", _make_result(True, stderr="warning"))
        )
        assert result.payload["stderr"] == "warning"

    def test_metadata_latency_from_tool_result(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data("echo hello", _make_result(True, duration_ms=42))
        )
        assert result.metadata.latency_ms == 42


# ---------------------------------------------------------------------------
# Failed shell
# ---------------------------------------------------------------------------


class TestFailedShell:
    def test_failure_returns_error_severity(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data("bad_cmd", _make_result(False, exit_code=1))
        )
        assert result.severity == Severity.ERROR

    def test_payload_contains_stderr_on_failure(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data(
                "bad_cmd", _make_result(False, exit_code=1, stderr="not found")
            )
        )
        assert result.payload["stderr"] == "not found"


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_timeout_returns_error_severity(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data(
                "sleep 100",
                _make_result(
                    False, exit_code=None, error="TIMEOUT", duration_ms=60000
                ),
            )
        )
        assert result.severity == Severity.ERROR

    def test_payload_contains_error_on_timeout(self) -> None:
        gen = ShellGen()
        result = gen.generate(
            _raw_data(
                "sleep 100",
                _make_result(
                    False, exit_code=None, error="TIMEOUT", duration_ms=60000
                ),
            )
        )
        assert result.payload["error"] == "TIMEOUT"


# ---------------------------------------------------------------------------
# Interface contract
# ---------------------------------------------------------------------------


class TestInterfaceContract:
    def test_implements_abstract_interface(self) -> None:
        gen = ShellGen()
        assert isinstance(gen, FeedbackGenerator)

    def test_fingerprint_is_empty(self) -> None:
        """Fingerprint is filled later by FingerprintStrategy."""
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.fingerprint == ""

    def test_round_is_zero(self) -> None:
        """Round is filled later by the Pipeline."""
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.round == 0

    def test_tool_call_is_none(self) -> None:
        """ToolCall is filled later by the Pipeline."""
        gen = ShellGen()
        result = gen.generate(_raw_data("echo hello", _make_result(True)))
        assert result.tool_call is None
