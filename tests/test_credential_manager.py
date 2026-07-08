"""Tests for Credential Manager — SPEC §7.1."""

from unittest import mock

import pytest

from harness.credentials.credential_manager import CredentialManager

# ---------------------------------------------------------------------------
# Store / Retrieve
# ---------------------------------------------------------------------------


class TestCredentialStoreRetrieve:
    def test_store_calls_keyring_set_password(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.set_password") as mock_set, mock.patch(
            "keyring.get_password", return_value=None
        ):
            cm.store("deepseek", "sk-test-key-12345")
            mock_set.assert_called_once_with(
                "ai4se-harness", "deepseek", "sk-test-key-12345"
            )

    def test_retrieve_calls_keyring_get_password(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.get_password", return_value="sk-test-key") as mock_get:
            result = cm.retrieve("deepseek")
            mock_get.assert_called_once_with("ai4se-harness", "deepseek")
            assert result == "sk-test-key"

    def test_retrieve_returns_none_when_not_found(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.get_password", return_value=None):
            assert cm.retrieve("nonexistent") is None

    def test_store_overwrites_existing(self) -> None:
        cm = CredentialManager()
        store: dict[tuple[str, str], str] = {}

        def _fake_set(service, username, password):
            store[(service, username)] = password

        def _fake_get(service, username):
            return store.get((service, username))

        with mock.patch("keyring.set_password", side_effect=_fake_set), mock.patch(
            "keyring.get_password", side_effect=_fake_get
        ):
            cm.store("deepseek", "sk-old-key")
            cm.store("deepseek", "sk-new-key")
            assert cm.retrieve("deepseek") == "sk-new-key"

    def test_multiple_providers(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.set_password"), mock.patch(
            "keyring.get_password",
            side_effect=lambda service, username: {
                ("ai4se-harness", "deepseek"): "sk-deepseek-key",
                ("ai4se-harness", "openai"): "sk-openai-key",
            }.get((service, username)),
        ):
            cm.store("deepseek", "sk-deepseek-key")
            cm.store("openai", "sk-openai-key")
            assert cm.retrieve("deepseek") == "sk-deepseek-key"
            assert cm.retrieve("openai") == "sk-openai-key"

    def test_store_empty_key_raises(self) -> None:
        cm = CredentialManager()
        with pytest.raises(ValueError, match="empty"):
            cm.store("deepseek", "")

    def test_store_whitespace_only_key_raises(self) -> None:
        cm = CredentialManager()
        with pytest.raises(ValueError, match="empty"):
            cm.store("deepseek", "   ")


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestCredentialClear:
    def test_clear_calls_keyring_delete_password(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.delete_password") as mock_delete:
            cm.clear("deepseek")
            mock_delete.assert_called_once_with("ai4se-harness", "deepseek")

    def test_clear_nonexistent_no_error(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.delete_password") as mock_delete:
            cm.clear("nonexistent")
            mock_delete.assert_called_once()

    def test_clear_does_not_affect_other_providers(self) -> None:
        cm = CredentialManager()
        store: dict[tuple[str, str], str] = {
            ("ai4se-harness", "deepseek"): "sk-deepseek-key",
            ("ai4se-harness", "openai"): "sk-openai-key",
        }

        def _fake_delete(service, username):
            store.pop((service, username), None)

        def _fake_get(service, username):
            return store.get((service, username))

        with mock.patch("keyring.set_password"), mock.patch(
            "keyring.get_password", side_effect=_fake_get
        ), mock.patch("keyring.delete_password", side_effect=_fake_delete):
            cm.store("deepseek", "sk-deepseek-key")
            cm.store("openai", "sk-openai-key")
            cm.clear("deepseek")
            assert cm.retrieve("deepseek") is None
            assert cm.retrieve("openai") == "sk-openai-key"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestCredentialStatus:
    def test_status_configured(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.get_password", return_value="sk-test-key"):
            status = cm.status("deepseek")
            assert "configured" in status.lower()
            assert "sk-test-key" not in status

    def test_status_not_configured(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.get_password", return_value=None):
            status = cm.status("deepseek")
            assert "not configured" in status.lower()

    def test_status_never_shows_plaintext(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.get_password", return_value="sk-very-secret-key-12345"):
            status = cm.status("deepseek")
            assert "sk-very-secret-key-12345" not in status


# ---------------------------------------------------------------------------
# Sanitize
# ---------------------------------------------------------------------------


class TestSanitize:
    def test_sanitize_redacts_sk_pattern(self) -> None:
        result = CredentialManager.sanitize("Error: sk-abc123 is invalid")
        assert "sk-abc123" not in result

    def test_sanitize_redacts_multiple_keys(self) -> None:
        result = CredentialManager.sanitize("Used keys: sk-abc123 and sk-xyz789")
        assert "sk-abc123" not in result
        assert "sk-xyz789" not in result

    def test_sanitize_preserves_non_key_text(self) -> None:
        result = CredentialManager.sanitize("Error: connection failed")
        assert "Error: connection failed" in result

    def test_sanitize_empty_string(self) -> None:
        result = CredentialManager.sanitize("")
        assert result == ""

    def test_sanitize_redacts_env_var_style(self) -> None:
        result = CredentialManager.sanitize("DEEPSEEK_API_KEY=sk-env-key-12345")
        assert "sk-env-key-12345" not in result

    def test_sanitize_redacts_specific_key(self) -> None:
        result = CredentialManager.sanitize(
            "API key: my-secret-token-999", key="my-secret-token-999"
        )
        assert "my-secret-token-999" not in result


# ---------------------------------------------------------------------------
# Hidden Input
# ---------------------------------------------------------------------------


class TestHiddenInput:
    def test_prompt_and_store(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.set_password") as mock_set, mock.patch(
            "getpass.getpass", return_value="sk-prompted-key"
        ):
            cm.prompt_and_store("deepseek")
            mock_set.assert_called_once_with(
                "ai4se-harness", "deepseek", "sk-prompted-key"
            )

    def test_prompt_overwrites_existing(self) -> None:
        cm = CredentialManager()
        with mock.patch("keyring.set_password") as mock_set, mock.patch(
            "getpass.getpass", return_value="sk-new-key"
        ):
            cm.prompt_and_store("deepseek")
            mock_set.assert_called_once_with(
                "ai4se-harness", "deepseek", "sk-new-key"
            )

    def test_prompt_empty_key_raises(self) -> None:
        cm = CredentialManager()
        with mock.patch("getpass.getpass", return_value=""), pytest.raises(
            ValueError, match="empty"
        ):
            cm.prompt_and_store("deepseek")

    def test_prompt_whitespace_only_key_raises(self) -> None:
        cm = CredentialManager()
        with mock.patch("getpass.getpass", return_value="   "), pytest.raises(
            ValueError, match="empty"
        ):
            cm.prompt_and_store("deepseek")
