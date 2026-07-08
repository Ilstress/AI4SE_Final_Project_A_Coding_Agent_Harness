"""Configuration Manager — TOML config loading and validation (SPEC §3.8)."""

import logging
import tomllib
from pathlib import Path
from typing import Any

from harness.models.config import (
    Config,
    GuardConfig,
    LLMConfig,
    LoopConfig,
    MemoryConfig,
    ToolsConfig,
    WorkspaceConfig,
)

logger = logging.getLogger(__name__)

# Known top-level sections per SPEC §3.8
_KNOWN_SECTIONS = frozenset({"workspace", "llm", "loop", "guard", "tools", "memory"})


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""


def load_config(path: str | Path) -> Config:
    """Load and validate a TOML configuration file.

    Returns an immutable Config object. API Key is excluded.
    """
    config_path = Path(path)

    # Parse TOML
    raw = _read_toml(config_path)

    # Warn about unknown sections
    _warn_unknown_sections(raw)

    # Extract sections with defaults
    workspace_raw = _get_section(raw, "workspace", config_path)
    llm_raw = _get_section(raw, "llm", config_path)
    loop_raw = raw.get("loop", {})
    guard_raw = raw.get("guard", {})
    tools_raw = raw.get("tools", {})
    memory_raw = raw.get("memory", {})

    # Build immutable config objects
    workspace = _build_workspace(workspace_raw)
    llm = _build_llm(llm_raw)
    loop = _build_loop(loop_raw)
    guard = _build_guard(guard_raw)
    tools = _build_tools(tools_raw)
    memory = _build_memory(memory_raw)

    return Config(
        workspace=workspace,
        llm=llm,
        loop=loop,
        guard=guard,
        tools=tools,
        memory=memory,
    )


def _read_toml(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML syntax in {path}: {e}") from e


def _warn_unknown_sections(raw: dict[str, Any]) -> None:
    """Log warnings for unknown top-level sections (forward-compatible)."""
    for key in raw:
        if key not in _KNOWN_SECTIONS:
            logger.warning(
                "Unknown configuration section '%s' — ignored (forward-compatible).", key
            )


def _get_section(raw: dict[str, Any], name: str, path: Path) -> dict[str, Any]:
    """Get a required section, raising ConfigError if missing."""
    if name not in raw:
        raise ConfigError(f"Missing required section '[{name}]' in {path}")
    section = raw[name]
    if not isinstance(section, dict):
        raise ConfigError(
            f"Invalid type for '[{name}]' in {path}: expected table, got {type(section).__name__}"
        )
    return section


def _validate_required_str(section: dict[str, Any], key: str, section_name: str) -> str:
    """Validate that a required string field exists and is a string."""
    if key not in section:
        raise ConfigError(f"Missing required field '{section_name}.{key}'")
    value = section[key]
    if not isinstance(value, str):
        raise ConfigError(
            f"Invalid type for '{section_name}.{key}': expected str, got {type(value).__name__}"
        )
    return value


def _validate_optional_str(section: dict[str, Any], key: str, section_name: str) -> str | None:
    """Validate an optional string field if present."""
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, str):
        raise ConfigError(
            f"Invalid type for '{section_name}.{key}': expected str, got {type(value).__name__}"
        )
    return value


def _validate_optional_int(section: dict[str, Any], key: str, section_name: str) -> int | None:
    """Validate an optional int field if present."""
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(
            f"Invalid type for '{section_name}.{key}': expected int, got {type(value).__name__}"
        )
    return value


def _validate_optional_list(section: dict[str, Any], key: str, section_name: str) -> list[Any] | None:
    """Validate an optional list field if present."""
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, list):
        raise ConfigError(
            f"Invalid type for '{section_name}.{key}': expected list, got {type(value).__name__}"
        )
    return value


def _build_workspace(raw: dict[str, Any]) -> WorkspaceConfig:
    root = _validate_required_str(raw, "root", "workspace")
    return WorkspaceConfig(root=root)


def _build_llm(raw: dict[str, Any]) -> LLMConfig:
    provider = _validate_required_str(raw, "provider", "llm")
    model = _validate_required_str(raw, "model", "llm")
    api_base = _validate_optional_str(raw, "api_base", "llm")
    return LLMConfig(provider=provider, model=model, api_base=api_base)


def _build_loop(raw: dict[str, Any]) -> LoopConfig:
    max_iterations = _validate_optional_int(raw, "max_iterations", "loop")
    timeout_seconds = _validate_optional_int(raw, "timeout_seconds", "loop")
    convergence_threshold = _validate_optional_int(raw, "convergence_threshold", "loop")

    kwargs: dict[str, Any] = {}
    if max_iterations is not None:
        kwargs["max_iterations"] = max_iterations
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = timeout_seconds
    if convergence_threshold is not None:
        kwargs["convergence_threshold"] = convergence_threshold
    return LoopConfig(**kwargs)


def _build_guard(raw: dict[str, Any]) -> GuardConfig:
    hitl_timeout_seconds = _validate_optional_int(raw, "hitl_timeout_seconds", "guard")
    rules = _validate_optional_list(raw, "rules", "guard")

    kwargs: dict[str, Any] = {}
    if hitl_timeout_seconds is not None:
        kwargs["hitl_timeout_seconds"] = hitl_timeout_seconds
    if rules is not None:
        kwargs["rules"] = rules
    return GuardConfig(**kwargs)


def _build_tools(raw: dict[str, Any]) -> ToolsConfig:
    enabled = _validate_optional_list(raw, "enabled", "tools")
    if enabled is not None:
        return ToolsConfig(enabled=enabled)
    return ToolsConfig()


def _build_memory(raw: dict[str, Any]) -> MemoryConfig:
    file_path = _validate_optional_str(raw, "file_path", "memory")
    if file_path is not None:
        return MemoryConfig(file_path=file_path)
    return MemoryConfig()
