"""Shared test fixtures for the AI4SE Harness test suite."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tmp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory that simulates a project root."""
    with tempfile.TemporaryDirectory(prefix="harness_test_") as tmpdir:
        workspace = Path(tmpdir)
        # Create a minimal project structure
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "tests").mkdir(exist_ok=True)
        yield workspace


@pytest.fixture
def sample_config_dict() -> dict[str, Any]:
    """Return a minimal valid configuration dictionary for testing."""
    return {
        "workspace": {"root": "/tmp/test_workspace"},
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_base": "https://api.deepseek.com/v1",
        },
        "loop": {
            "max_iterations": 10,
            "timeout_seconds": 300,
            "convergence_threshold": 3,
        },
        "guard": {
            "hitl_timeout_seconds": 120,
        },
        "tools": {
            "enabled": ["read_file", "write_file", "execute_shell", "task_complete"],
        },
        "memory": {
            "file_path": "./memory.json",
        },
    }


@pytest.fixture
def sample_config_path(tmp_path: Path, sample_config_dict: dict[str, Any]) -> Path:
    """Write a sample config dict to a temporary TOML file and return its path."""

    # tomllib is read-only; we use a simple writer for the fixture
    config_path = tmp_path / "config.toml"
    lines = _dict_to_toml_lines(sample_config_dict)
    config_path.write_text("\n".join(lines))
    return config_path


def _dict_to_toml_lines(d: dict[str, Any], prefix: str = "") -> list[str]:
    """Minimal TOML writer for test fixtures (handles nested dicts, lists, scalars)."""
    lines: list[str] = []
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            lines.append(f"\n[{full_key}]")
            for sub_key, sub_value in value.items():
                lines.append(f"{sub_key} = {_toml_value(sub_value)}")
        elif isinstance(value, list):
            lines.append(f"{key} = {_toml_value(value)}")
        else:
            lines.append(f"{key} = {_toml_value(value)}")
    return lines


def _toml_value(value: object) -> str:
    """Convert a Python value to a TOML string representation."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        items = ", ".join(_toml_value(v) for v in value)
        return f"[{items}]"
    elif isinstance(value, str):
        return f'"{value}"'
    return f'"{value}"'
