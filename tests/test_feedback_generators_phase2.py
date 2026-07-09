"""Tests for TestGen, LintGen, DiffGen — SPEC §3.6.1, PLAN T8.2."""

from harness.feedback.generators.base import FeedbackGenerator
from harness.feedback.generators.diff_gen import DiffGen
from harness.feedback.generators.lint_gen import LintGen
from harness.feedback.generators.test_gen import TestGen
from harness.models.feedback import FeedbackSource, Severity
from harness.models.tool_result import ToolResult


def _make_result(
    success: bool = True,
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


def _raw(tool_result: ToolResult) -> dict:
    return {"tool_result": tool_result}


# ---------------------------------------------------------------------------
# TestGen
# ---------------------------------------------------------------------------


class TestTestGen:
    def test_source_is_test(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(stdout="10 passed"))
        )
        assert result.source == FeedbackSource.TEST

    def test_all_passed_returns_info(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(stdout="10 passed"))
        )
        assert result.severity == Severity.INFO

    def test_has_failures_returns_error(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(exit_code=1, stdout="8 passed, 2 failed"))
        )
        assert result.severity == Severity.ERROR

    def test_payload_contains_passed(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(stdout="10 passed"))
        )
        assert result.payload["passed"] == 10

    def test_payload_contains_failed(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(exit_code=1, stdout="8 passed, 2 failed"))
        )
        assert result.payload["failed"] == 2

    def test_payload_contains_total(self) -> None:
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(stdout="3 passed, 1 failed"))
        )
        assert result.payload["total"] == 4

    def test_empty_output_zero_tests(self) -> None:
        gen = TestGen()
        result = gen.generate(_raw(_make_result(stdout="")))
        assert result.payload["passed"] == 0
        assert result.payload["failed"] == 0
        assert result.payload["total"] == 0

    def test_failed_first_in_summary(self) -> None:
        """pytest sometimes prints '2 failed, 8 passed'."""
        gen = TestGen()
        result = gen.generate(
            _raw(_make_result(exit_code=1, stdout="2 failed, 8 passed"))
        )
        assert result.payload["passed"] == 8
        assert result.payload["failed"] == 2

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(TestGen(), FeedbackGenerator)


# ---------------------------------------------------------------------------
# LintGen
# ---------------------------------------------------------------------------


class TestLintGen:
    def test_source_is_lint(self) -> None:
        gen = LintGen()
        result = gen.generate(_raw(_make_result(stdout="")))
        assert result.source == FeedbackSource.LINT

    def test_no_issues_returns_info(self) -> None:
        gen = LintGen()
        result = gen.generate(_raw(_make_result(stdout="")))
        assert result.severity == Severity.INFO

    def test_has_issues_returns_warning(self) -> None:
        gen = LintGen()
        result = gen.generate(
            _raw(
                _make_result(
                    exit_code=1,
                    stdout="file.py:1:1: E501 line too long\n",
                )
            )
        )
        assert result.severity == Severity.WARNING

    def test_payload_contains_errors_list(self) -> None:
        gen = LintGen()
        stdout = "file.py:1:1: E501 line too long\nfile.py:2:1: F401 unused\n"
        result = gen.generate(
            _raw(_make_result(exit_code=1, stdout=stdout))
        )
        assert len(result.payload["errors"]) == 2

    def test_stderr_included_in_output(self) -> None:
        gen = LintGen()
        result = gen.generate(
            _raw(
                _make_result(
                    exit_code=1, stderr="mypy: error: ...\n"
                )
            )
        )
        assert len(result.payload["errors"]) == 1

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(LintGen(), FeedbackGenerator)


# ---------------------------------------------------------------------------
# DiffGen
# ---------------------------------------------------------------------------


class TestDiffGen:
    def test_source_is_diff(self) -> None:
        gen = DiffGen()
        result = gen.generate(
            _raw(_make_result(stdout="1 file changed, 3 insertions(+)"))
        )
        assert result.source == FeedbackSource.DIFF

    def test_returns_info_severity(self) -> None:
        gen = DiffGen()
        result = gen.generate(
            _raw(_make_result(stdout="1 file changed, 3 insertions(+)"))
        )
        assert result.severity == Severity.INFO

    def test_payload_contains_patch(self) -> None:
        gen = DiffGen()
        stdout = "diff --git a/file.py b/file.py\n+hello"
        result = gen.generate(_raw(_make_result(stdout=stdout)))
        assert result.payload["patch"] == stdout

    def test_payload_contains_files_changed(self) -> None:
        gen = DiffGen()
        result = gen.generate(
            _raw(_make_result(stdout="2 files changed, 10 insertions(+), 5 deletions(-)"))
        )
        assert result.payload["files_changed"] == 2

    def test_payload_contains_additions(self) -> None:
        gen = DiffGen()
        result = gen.generate(
            _raw(_make_result(stdout="2 files changed, 10 insertions(+), 5 deletions(-)"))
        )
        assert result.payload["additions"] == 10

    def test_payload_contains_deletions(self) -> None:
        gen = DiffGen()
        result = gen.generate(
            _raw(_make_result(stdout="2 files changed, 10 insertions(+), 5 deletions(-)"))
        )
        assert result.payload["deletions"] == 5

    def test_empty_diff_zero_stats(self) -> None:
        gen = DiffGen()
        result = gen.generate(_raw(_make_result(stdout="")))
        assert result.payload["files_changed"] == 0
        assert result.payload["additions"] == 0
        assert result.payload["deletions"] == 0

    def test_implements_abstract_interface(self) -> None:
        assert isinstance(DiffGen(), FeedbackGenerator)
