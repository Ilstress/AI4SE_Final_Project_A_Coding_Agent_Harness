"""SPEC §6.13: Configuration — immutable session configuration loaded at startup.

Configuration fields are defined in SPEC §3.8.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkspaceConfig:
    """Workspace configuration."""

    root: str


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration.

    api_base is optional (defaults to provider's default endpoint).
    """

    provider: str
    model: str
    api_base: str | None = None


@dataclass(frozen=True)
class LoopConfig:
    """Main Loop configuration."""

    max_iterations: int = 10
    timeout_seconds: float = 300.0
    convergence_threshold: int = 3


@dataclass(frozen=True)
class GuardConfig:
    """Guardrail configuration."""

    hitl_timeout_seconds: int = 120
    rules: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ToolsConfig:
    """Tools configuration."""

    enabled: list[str] = field(
        default_factory=lambda: ["read_file", "write_file", "execute_shell", "task_complete"]
    )


@dataclass(frozen=True)
class MemoryConfig:
    """Memory configuration."""

    file_path: str = "./memory.json"


@dataclass(frozen=True)
class Config:
    """Immutable session configuration loaded at startup.

    Constraints:
        - Immutable after loading.
        - API Key is excluded from this object.
        - Missing required fields trigger startup failure.
    """

    workspace: WorkspaceConfig
    llm: LLMConfig
    loop: LoopConfig = field(default_factory=LoopConfig)
    guard: GuardConfig = field(default_factory=GuardConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
