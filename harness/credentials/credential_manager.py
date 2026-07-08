"""Credential Manager — secure API Key storage and retrieval (SPEC §7.1).

Primary storage: OS keychain via keyring library.
"""

import getpass
import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal keyring wrapper
# ---------------------------------------------------------------------------


class _KeyringBackend:
    """Internal wrapper around the keyring library.

    Encapsulates keyring calls so that CredentialManager does not depend
    on the keyring API directly.

    NOTE (MVP): Only the keyring backend is implemented. The encrypted-file
    fallback described in SPEC §7.1 is not yet implemented.
    """

    @staticmethod
    def store(service: str, username: str, password: str) -> None:
        import keyring

        keyring.set_password(service, username, password)

    @staticmethod
    def retrieve(service: str, username: str) -> str | None:
        import keyring

        return keyring.get_password(service, username)

    @staticmethod
    def delete(service: str, username: str) -> None:
        import contextlib

        import keyring

        with contextlib.suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(service, username)


# ---------------------------------------------------------------------------
# Credential Manager
# ---------------------------------------------------------------------------


class CredentialManager:
    """Manages API Key credentials across supported LLM providers.

    Primary storage: OS keychain (via keyring).
    NOTE (MVP): Encrypted-file fallback (SPEC §7.1) is not yet implemented.

    API Keys are never stored in config.toml, never logged in plaintext,
    and never passed as CLI arguments.
    """

    SERVICE_NAME = "ai4se-harness"

    # Regex patterns for automatic key redaction in log output
    _KEY_PATTERN = re.compile(r"\b(sk-[a-zA-Z0-9_-]{4,})\b")

    def __init__(self) -> None:
        self._backend = _KeyringBackend()

    # ---- core CRUD ----

    def store(self, provider: str, key: str) -> None:
        """Securely store an API Key for a provider."""
        if not key.strip():
            raise ValueError("API Key must not be empty")
        self._backend.store(self.SERVICE_NAME, provider, key)

    def retrieve(self, provider: str) -> str | None:
        """Retrieve the stored API Key for a provider, or None."""
        return self._backend.retrieve(self.SERVICE_NAME, provider)

    def clear(self, provider: str) -> None:
        """Remove the stored API Key for a provider."""
        self._backend.delete(self.SERVICE_NAME, provider)

    def status(self, provider: str) -> str:
        """Return a human-readable status string.

        Never includes the plaintext key.
        """
        key = self.retrieve(provider)
        if key is None:
            return f"Provider '{provider}': not configured"
        return f"Provider '{provider}': configured"

    # ---- prompt ----

    def prompt_and_store(self, provider: str) -> None:
        """Prompt the user for an API Key via hidden input and store it."""
        key = getpass.getpass(f"Enter API Key for {provider} (input hidden): ")
        if not key.strip():
            raise ValueError("API Key must not be empty")
        self.store(provider, key.strip())

    # ---- sanitization ----

    @staticmethod
    def sanitize(text: str, key: str | None = None) -> str:
        """Redact API keys from text for safe logging.

        Args:
            text: The text to sanitize.
            key: An optional specific key to redact. If not provided,
                 common key patterns (sk-...) are automatically redacted.

        Returns:
            The sanitized text with keys replaced by '***'.
        """
        if key:
            text = text.replace(key, "***")
        # Redact common API key patterns regardless
        text = CredentialManager._KEY_PATTERN.sub("***", text)
        return text
