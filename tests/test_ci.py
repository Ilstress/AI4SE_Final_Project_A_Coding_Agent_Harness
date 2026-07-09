"""Tests for CI/CD configuration — SPEC §9.11, PLAN T13.2.

Structural verification of GitHub Actions workflow and GitLab CI config.
These tests validate the files exist and contain required elements.
"""

from pathlib import Path


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# GitHub Actions workflow
# ---------------------------------------------------------------------------


class TestGitHubActionsWorkflowExists:
    """Verify .github/workflows/unit-test.yml exists."""

    def test_workflow_file_exists(self) -> None:
        path = _repo_root() / ".github" / "workflows" / "unit-test.yml"
        assert path.exists(), f"Workflow not found at {path}"
        assert path.is_file(), f"Workflow at {path} is not a file"


class TestGitHubActionsWorkflowContent:
    """Verify the GitHub Actions workflow has required structure."""

    @staticmethod
    def _read_workflow() -> str:
        path = _repo_root() / ".github" / "workflows" / "unit-test.yml"
        return path.read_text(encoding="utf-8")

    def test_has_name(self) -> None:
        content = self._read_workflow()
        assert "name:" in content, "Workflow must have a name"

    def test_triggers_on_push(self) -> None:
        content = self._read_workflow()
        assert "push:" in content, "Workflow must trigger on push"

    def test_has_unit_test_job(self) -> None:
        content = self._read_workflow()
        assert "unit-test" in content, "Workflow must contain a job named 'unit-test'"

    def test_uses_python_311(self) -> None:
        content = self._read_workflow()
        assert "3.11" in content, "Workflow must use Python 3.11"

    def test_runs_make_test(self) -> None:
        content = self._read_workflow()
        assert "make test" in content or "pytest" in content, (
            "Workflow must run 'make test' or 'pytest'"
        )

    def test_has_checkout_step(self) -> None:
        content = self._read_workflow()
        assert "checkout" in content.lower() or "actions/checkout" in content, (
            "Workflow must include a checkout step"
        )

    def test_valid_yaml_parsable(self) -> None:
        import yaml  # type: ignore[import-untyped]

        content = self._read_workflow()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise AssertionError(f"Workflow file is not valid YAML: {exc}") from exc


# ---------------------------------------------------------------------------
# GitLab CI configuration
# ---------------------------------------------------------------------------


class TestGitLabCIExists:
    """Verify .gitlab-ci.yml exists (通用要求 §五.6)."""

    def test_gitlab_ci_exists(self) -> None:
        path = _repo_root() / ".gitlab-ci.yml"
        assert path.exists(), f"GitLab CI config not found at {path}"
        assert path.is_file(), f"GitLab CI config at {path} is not a file"


class TestGitLabCIContent:
    """Verify .gitlab-ci.yml has the required unit-test job."""

    @staticmethod
    def _read_ci() -> str:
        path = _repo_root() / ".gitlab-ci.yml"
        return path.read_text(encoding="utf-8")

    def test_has_unit_test_job(self) -> None:
        content = self._read_ci()
        assert "unit-test" in content, (
            "GitLab CI must contain a job named 'unit-test'"
        )

    def test_uses_python_311_image(self) -> None:
        content = self._read_ci()
        assert "python" in content.lower(), "GitLab CI must use a Python image"
        assert "3.11" in content, "GitLab CI must use Python 3.11"

    def test_runs_pytest(self) -> None:
        content = self._read_ci()
        assert "pytest" in content or "make test" in content, (
            "GitLab CI must run tests"
        )

    def test_valid_yaml_parsable(self) -> None:
        import yaml

        content = self._read_ci()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise AssertionError(f"GitLab CI file is not valid YAML: {exc}") from exc
