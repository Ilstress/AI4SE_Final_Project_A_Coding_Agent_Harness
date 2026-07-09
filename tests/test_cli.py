"""Tests for CLI Entry Point — SPEC §7.1.2, §8.5, PLAN T11.1."""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harness.cli.main import main, parse_args
from harness.loop.main_loop import LoopState
from harness.models.config import Config, LLMConfig, LoopConfig, WorkspaceConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_config(workspace_root: str | None = None) -> Config:
    if workspace_root is None:
        workspace_root = tempfile.gettempdir()
    return Config(
        workspace=WorkspaceConfig(root=workspace_root),
        llm=LLMConfig(provider="deepseek", model="deepseek-chat"),
        loop=LoopConfig(max_iterations=10, timeout_seconds=300.0),
    )


def _setup_cred_mock(mock_cm: MagicMock) -> None:
    """Configure a CredentialManager mock to return a fake API key."""
    mock_instance = MagicMock()
    mock_instance.retrieve.return_value = "sk-test-fake-key"
    mock_cm.return_value = mock_instance


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestArgumentParsing:
    def test_default_config_path(self) -> None:
        args = parse_args(["run", "--task", "hello"])
        assert args.config == "./config.toml"

    def test_custom_config_path(self) -> None:
        args = parse_args(["run", "--task", "hello", "--config", "/path/to/config.toml"])
        assert args.config == "/path/to/config.toml"

    def test_run_subcommand_parses_task(self) -> None:
        args = parse_args(["run", "--task", "write a function"])
        assert args.command == "run"
        assert args.task == "write a function"

    def test_setup_flag(self) -> None:
        args = parse_args(["--setup"])
        assert args.setup is True

    def test_clear_credentials_flag(self) -> None:
        args = parse_args(["--clear-credentials"])
        assert args.clear_credentials is True


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


class TestSetup:
    @patch("harness.cli.main.CredentialManager")
    def test_setup_calls_prompt_and_store(self, mock_cm: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_cm.return_value = mock_instance

        with pytest.raises(SystemExit):
            main(["--setup"])

        mock_instance.prompt_and_store.assert_called_once()


# ---------------------------------------------------------------------------
# Clear credentials
# ---------------------------------------------------------------------------


class TestClearCredentials:
    @patch("harness.cli.main.CredentialManager")
    def test_clear_credentials_calls_clear(self, mock_cm: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_cm.return_value = mock_instance

        with pytest.raises(SystemExit):
            main(["--clear-credentials"])

        mock_instance.clear.assert_called_once()


# ---------------------------------------------------------------------------
# Run — exit codes
# ---------------------------------------------------------------------------


class TestRunExitCodes:
    @patch("harness.cli.main.CredentialManager")
    @patch("harness.cli.main.MainLoop")
    @patch("harness.cli.main.load_config")
    def test_completed_exit_code_0(
        self, mock_load: MagicMock, mock_ml: MagicMock, mock_cm: MagicMock
    ) -> None:
        mock_load.return_value = _make_test_config()
        _setup_cred_mock(mock_cm)
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=LoopState.COMPLETED)
        mock_ml.return_value = mock_instance

        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--task", "test"])
        assert exc_info.value.code == 0

    @patch("harness.cli.main.CredentialManager")
    @patch("harness.cli.main.MainLoop")
    @patch("harness.cli.main.load_config")
    def test_failed_exit_code_1(
        self, mock_load: MagicMock, mock_ml: MagicMock, mock_cm: MagicMock
    ) -> None:
        mock_load.return_value = _make_test_config()
        _setup_cred_mock(mock_cm)
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=LoopState.FAILED)
        mock_ml.return_value = mock_instance

        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--task", "test"])
        assert exc_info.value.code == 1

    @patch("harness.cli.main.CredentialManager")
    @patch("harness.cli.main.MainLoop")
    @patch("harness.cli.main.load_config")
    def test_cancelled_exit_code_2(
        self, mock_load: MagicMock, mock_ml: MagicMock, mock_cm: MagicMock
    ) -> None:
        mock_load.return_value = _make_test_config()
        _setup_cred_mock(mock_cm)
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=LoopState.CANCELLED)
        mock_ml.return_value = mock_instance

        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--task", "test"])
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Run — error handling
# ---------------------------------------------------------------------------


class TestRunErrors:
    @patch("harness.cli.main.load_config")
    def test_missing_config_file_error(self, mock_load: MagicMock) -> None:
        mock_load.side_effect = FileNotFoundError("config.toml not found")

        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--task", "test"])
        assert exc_info.value.code == 1

    def test_no_command_shows_help(self) -> None:
        with pytest.raises(SystemExit):
            main([])
