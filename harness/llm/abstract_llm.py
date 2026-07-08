"""SPEC §3.2: AbstractLLM — unified interface for LLM providers."""

from abc import ABC, abstractmethod

from harness.models.llm_response import LLMResponse


class LLMFatalError(Exception):
    """Non-retryable fatal error from an LLM provider.

    Raised when the adapter encounters an error that cannot be recovered
    by retrying (e.g. 401, 403, 400) or when max retries are exhausted.
    """


class AbstractLLM(ABC):
    """Abstract interface for LLM provider adapters.

    Each provider adapter implements the async ``call`` method, which
    sends a list of messages to the LLM and returns a standardized
    ``LLMResponse``.

    Retry logic is built into each adapter and does not consume Main
    Loop iteration counts.
    """

    @abstractmethod
    async def call(self, messages: list[dict]) -> LLMResponse:
        """Send messages to the LLM and return a standardized response.

        Args:
            messages: List of message dicts in OpenAI-compatible format.

        Returns:
            A frozen LLMResponse with content, tool_calls, finish_reason,
            and usage.

        Raises:
            LLMFatalError: When a non-retryable error occurs or max
                retries are exhausted.
        """
        ...
