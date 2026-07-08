"""Tests for Configuration Manager — SPEC §3.8."""

from pathlib import Path

import pytest

from harness.models.config import Config, LoopConfig, MemoryConfig, ToolsConfig


class TestLoadConfigValid:
    """Tests for successful config loading."""

    def test_load_valid_config(self, sample_config_path: Path) -> None:
        from harness.config.config_manager import load_config

        config = load_config(sample_config_path)

        assert config.workspace.root == "/tmp/test_workspace"
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-chat"
        assert config.llm.api_base == "https://api.deepseek.com/v1"
        assert config.loop.max_iterations == 10
        assert config.loop.timeout_seconds == 300
        assert config.loop.convergence_threshold == 3
        assert config.guard.hitl_timeout_seconds == 120
        assert config.tools.enabled == ["read_file", "write_file", "execute_shell", "task_complete"]
        assert config.memory.file_path == "./memory.json"

    def test_config_is_frozen(self, sample_config_path: Path) -> None:
        from dataclasses import FrozenInstanceError

        from harness.config.config_manager import load_config

        config = load_config(sample_config_path)
        with pytest.raises(FrozenInstanceError):
            config.workspace.root = "/other"  # type: ignore[misc]

    def test_minimal_config_with_defaults(self, tmp_path: Path) -> None:
        from harness.config.config_manager import load_config

        config_path = tmp_path / "minimal.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "openai"\nmodel = "gpt-4"\n'
        )

        config = load_config(config_path)

        assert config.workspace.root == "/tmp/proj"
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4"
        assert config.llm.api_base is None
        # Defaults
        assert config.loop.max_iterations == 10
        assert config.loop.timeout_seconds == 300
        assert config.loop.convergence_threshold == 3
        assert config.guard.hitl_timeout_seconds == 120
        assert config.guard.rules == []
        assert config.tools.enabled == ["read_file", "write_file", "execute_shell", "task_complete"]
        assert config.memory.file_path == "./memory.json"

    def test_config_no_api_key_field(self, sample_config_path: Path) -> None:
        from harness.config.config_manager import load_config

        config = load_config(sample_config_path)
        assert not hasattr(config, "api_key")

    def test_optional_api_base_omitted(self, tmp_path: Path) -> None:
        from harness.config.config_manager import load_config

        config_path = tmp_path / "no_api_base.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n'
        )

        config = load_config(config_path)
        assert config.llm.api_base is None

    def test_custom_loop_config(self, tmp_path: Path) -> None:
        from harness.config.config_manager import load_config

        config_path = tmp_path / "custom_loop.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n\n'
            "[loop]\nmax_iterations = 20\ntimeout_seconds = 600\nconvergence_threshold = 5\n"
        )

        config = load_config(config_path)
        assert config.loop.max_iterations == 20
        assert config.loop.timeout_seconds == 600
        assert config.loop.convergence_threshold == 5

    def test_custom_guard_config(self, tmp_path: Path) -> None:
        from harness.config.config_manager import load_config

        config_path = tmp_path / "custom_guard.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n\n'
            "[guard]\nhitl_timeout_seconds = 60\nrules = [{name = \"custom_rule\"}]\n"
        )

        config = load_config(config_path)
        assert config.guard.hitl_timeout_seconds == 60
        assert config.guard.rules == [{"name": "custom_rule"}]

    def test_custom_tools_config(self, tmp_path: Path) -> None:
        from harness.config.config_manager import load_config

        config_path = tmp_path / "custom_tools.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n\n'
            '[tools]\nenabled = ["read_file", "write_file"]\n'
        )

        config = load_config(config_path)
        assert config.tools.enabled == ["read_file", "write_file"]


class TestLoadConfigErrors:
    """Tests for error handling in config loading."""

    def test_missing_workspace_root(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "no_workspace.toml"
        config_path.write_text('[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n')

        with pytest.raises(ConfigError, match="workspace.root"):
            load_config(config_path)

    def test_missing_llm_provider(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "no_provider.toml"
        config_path.write_text('[workspace]\nroot = "/tmp/proj"\n\n[llm]\nmodel = "deepseek-chat"\n')

        with pytest.raises(ConfigError, match="llm.provider"):
            load_config(config_path)

    def test_missing_llm_model(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "no_model.toml"
        config_path.write_text('[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\n')

        with pytest.raises(ConfigError, match="llm.model"):
            load_config(config_path)

    def test_missing_llm_section(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "no_llm.toml"
        config_path.write_text('[workspace]\nroot = "/tmp/proj"\n')

        with pytest.raises(ConfigError, match="llm"):
            load_config(config_path)

    def test_missing_workspace_section(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "no_workspace.toml"
        config_path.write_text('[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n')

        with pytest.raises(ConfigError, match="workspace"):
            load_config(config_path)

    def test_file_not_found(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        nonexistent = tmp_path / "nonexistent.toml"
        with pytest.raises(ConfigError, match="not found"):
            load_config(nonexistent)

    def test_invalid_toml_syntax(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "bad.toml"
        config_path.write_text("this is not valid toml {{{")

        with pytest.raises(ConfigError, match="TOML"):
            load_config(config_path)

    def test_invalid_value_type_for_max_iterations(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "bad_type.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n\n'
            "[loop]\nmax_iterations = \"not_a_number\"\n"
        )

        with pytest.raises(ConfigError, match="max_iterations"):
            load_config(config_path)

    def test_unknown_keys_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        from harness.config.config_manager import load_config

        caplog.set_level(logging.WARNING)

        config_path = tmp_path / "unknown_key.toml"
        config_path.write_text(
            '[workspace]\nroot = "/tmp/proj"\n\n[llm]\nprovider = "deepseek"\nmodel = "deepseek-chat"\n\n'
            "[unknown_section]\nfoo = \"bar\"\n"
        )

        config = load_config(config_path)
        assert config is not None  # Should still load successfully
        # Check that unknown key warning was logged
        assert "unknown_section" in caplog.text.lower() or "unknown" in caplog.text.lower()

    def test_empty_config_file(self, tmp_path: Path) -> None:
        from harness.config.config_manager import ConfigError, load_config

        config_path = tmp_path / "empty.toml"
        config_path.write_text("")

        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_load_config_returns_config_type(self, sample_config_path: Path) -> None:
        from harness.config.config_manager import load_config

        config = load_config(sample_config_path)
        assert isinstance(config, Config)
        assert isinstance(config.loop, LoopConfig)
        assert isinstance(config.memory, MemoryConfig)
        assert isinstance(config.tools, ToolsConfig)
