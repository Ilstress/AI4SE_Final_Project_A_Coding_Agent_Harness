"""Tests for Dockerfile — SPEC §7.2.2, PLAN T13.1.

Structural verification of Dockerfile and .dockerignore content.
Docker is not available in the test environment, so these tests verify
the files exist and contain required elements.
"""

import re
from pathlib import Path


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Dockerfile existence and structure
# ---------------------------------------------------------------------------


class TestDockerfileExists:
    """Verify Dockerfile exists at the repository root."""

    def test_dockerfile_exists(self) -> None:
        path = _repo_root() / "Dockerfile"
        assert path.exists(), f"Dockerfile not found at {path}"
        assert path.is_file(), f"Dockerfile at {path} is not a file"


class TestDockerfileContent:
    """Verify Dockerfile contains required elements per SPEC §7.2.2."""

    @staticmethod
    def _read_dockerfile() -> str:
        path = _repo_root() / "Dockerfile"
        return path.read_text(encoding="utf-8")

    def test_from_python_311_slim(self) -> None:
        content = self._read_dockerfile()
        assert re.search(r"FROM\s+python:3\.11-slim", content), (
            "Dockerfile must use python:3.11-slim as base image"
        )

    def test_has_entrypoint(self) -> None:
        content = self._read_dockerfile()
        assert re.search(r"ENTRYPOINT\s+\[", content), (
            "Dockerfile must have an ENTRYPOINT directive"
        )

    def test_entrypoint_is_ai4se_harness(self) -> None:
        content = self._read_dockerfile()
        assert "ai4se-harness" in content, (
            "Dockerfile ENTRYPOINT must reference ai4se-harness"
        )

    def test_has_workdir(self) -> None:
        content = self._read_dockerfile()
        assert re.search(r"WORKDIR\s+", content), (
            "Dockerfile must set a WORKDIR"
        )

    def test_copies_project_files(self) -> None:
        content = self._read_dockerfile()
        assert "COPY" in content, (
            "Dockerfile must COPY project files into the image"
        )

    def test_installs_project(self) -> None:
        content = self._read_dockerfile()
        assert "pip install" in content, (
            "Dockerfile must pip install the project"
        )

    def test_has_volume(self) -> None:
        content = self._read_dockerfile()
        assert "VOLUME" in content, (
            "Dockerfile must declare a VOLUME for credential persistence"
        )

    def test_no_hardcoded_secrets(self) -> None:
        content = self._read_dockerfile()
        # Must not contain anything that looks like an API key
        assert not re.search(r"sk-[a-zA-Z0-9]{20,}", content), (
            "Dockerfile must not contain hardcoded API keys"
        )
        assert "password" not in content.lower() or "getpass" in content.lower(), (
            "Dockerfile should not contain hardcoded passwords"
        )

    def test_multi_stage_or_single_stage(self) -> None:
        content = self._read_dockerfile()
        # Count FROM lines — multi-stage has 2+, single-stage has 1
        from_lines = [line for line in content.splitlines() if line.strip().startswith("FROM ")]
        assert len(from_lines) >= 1, "Dockerfile must have at least one FROM instruction"


# ---------------------------------------------------------------------------
# .dockerignore
# ---------------------------------------------------------------------------


class TestDockerignoreExists:
    """Verify .dockerignore exists and contains sensible exclusions."""

    def test_dockerignore_exists(self) -> None:
        path = _repo_root() / ".dockerignore"
        assert path.exists(), f".dockerignore not found at {path}"
        assert path.is_file(), f".dockerignore at {path} is not a file"


class TestDockerignoreContent:
    """Verify .dockerignore excludes common unnecessary files."""

    _REQUIRED_PATTERNS = [
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "*.egg-info",
        ".venv",
        "venv",
    ]

    @staticmethod
    def _read_dockerignore() -> str:
        path = _repo_root() / ".dockerignore"
        return path.read_text(encoding="utf-8")

    def test_excludes_pycache(self) -> None:
        content = self._read_dockerignore()
        assert "__pycache__" in content

    def test_excludes_git(self) -> None:
        content = self._read_dockerignore()
        assert ".git" in content

    def test_excludes_virtual_env(self) -> None:
        content = self._read_dockerignore()
        assert ".venv" in content or "venv" in content

    def test_excludes_cache_dirs(self) -> None:
        content = self._read_dockerignore()
        assert ".mypy_cache" in content
        assert ".pytest_cache" in content
        assert ".ruff_cache" in content

    def test_excludes_egg_info(self) -> None:
        content = self._read_dockerignore()
        assert "*.egg-info" in content
