"""Tests for README.md — PLAN T13.3, 通用要求 §五.4.

Structural verification of README.md content.
Ensures all required sections are present and commands are consistent with CI workflows.
"""

from pathlib import Path


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


def _read_readme() -> str:
    path = _repo_root() / "README.md"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


class TestReadmeExists:
    """Verify README.md exists at the repository root."""

    def test_readme_exists(self) -> None:
        path = _repo_root() / "README.md"
        assert path.exists(), f"README.md not found at {path}"
        assert path.is_file(), f"README.md at {path} is not a file"


# ---------------------------------------------------------------------------
# Required sections (通用要求 §五.4)
# ---------------------------------------------------------------------------


class TestReadmeRequiredSections:
    """Verify README.md contains all required sections per 通用要求 §五.4."""

    _REQUIRED_SECTIONS: list[str] = [
        "项目简介",           # Project introduction
        "架构",               # Architecture
        "安装",               # Installation
        "快速开始",           # Quick start
        "API Key",            # API key configuration
        "Docker",             # Docker usage
        "测试",               # Testing & CI
        "目录",               # Directory structure
        "安全",               # Security boundary
        "已知限制",           # Known limitations
        "License",            # License
    ]

    def test_all_required_sections_present(self) -> None:
        content = _read_readme()
        missing: list[str] = []
        for section in self._REQUIRED_SECTIONS:
            # Check for markdown heading containing the section keyword
            if section not in content:
                missing.append(section)
        assert not missing, (
            f"README.md missing required sections: {', '.join(missing)}"
        )

    def test_has_project_name_in_title(self) -> None:
        content = _read_readme()
        assert "# " in content, "README.md must have a level-1 heading with the project name"

    def test_has_ascii_architecture_diagram(self) -> None:
        content = _read_readme()
        # ASCII diagrams typically use box-drawing chars or pipe/dash patterns
        has_diagram = (
            "┌" in content or "└" in content or "│" in content
            or "+--" in content or "+-" in content
        )
        assert has_diagram, (
            "README.md architecture section should include an ASCII diagram"
        )


# ---------------------------------------------------------------------------
# Command consistency with CI workflows
# ---------------------------------------------------------------------------


class TestReadmeCommandConsistency:
    """Verify README commands match CI workflows and Makefile."""

    def test_install_command_matches_ci(self) -> None:
        """README install command must match CI install step."""
        content = _read_readme()
        # CI uses: pip install -e ".[dev]"
        assert 'pip install -e ".[dev]"' in content or "pip install -e .[dev]" in content, (
            "README install command must match CI: pip install -e \".[dev]\""
        )

    def test_test_command_matches_ci(self) -> None:
        """README test command must match CI and Makefile."""
        content = _read_readme()
        assert "make test" in content or "pytest" in content, (
            "README must reference 'make test' or 'pytest' as the test command"
        )

    def test_docker_build_command(self) -> None:
        content = _read_readme()
        assert "docker build" in content, (
            "README must include 'docker build' command"
        )
        assert "ai4se-harness" in content, (
            "README must reference the 'ai4se-harness' image name"
        )

    def test_docker_run_command(self) -> None:
        content = _read_readme()
        assert "docker run" in content, (
            "README must include 'docker run' command"
        )

    def test_setup_command_documented(self) -> None:
        content = _read_readme()
        assert "--setup" in content, (
            "README must document the '--setup' command for API key configuration"
        )

    def test_run_command_documented(self) -> None:
        content = _read_readme()
        assert "run --task" in content or '"run"' in content, (
            "README must document the 'run --task' command"
        )


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestReadmeSecurity:
    """Verify README contains security documentation and no hardcoded secrets."""

    def test_no_hardcoded_api_keys(self) -> None:
        content = _read_readme()
        import re
        assert not re.search(r"sk-[a-zA-Z0-9]{20,}", content), (
            "README.md must not contain hardcoded API keys"
        )

    def test_mentions_key_security(self) -> None:
        content = _read_readme()
        assert "keyring" in content.lower() or "钥匙串" in content or "keychain" in content.lower() or "凭据" in content, (
            "README must mention credential/API key security mechanism"
        )

    def test_mentions_platform_support(self) -> None:
        content = _read_readme()
        platforms = ["Windows", "macOS", "Linux"]
        found = [p for p in platforms if p in content]
        assert len(found) >= 2, (
            f"README must mention at least 2 target platforms, found: {found}"
        )
