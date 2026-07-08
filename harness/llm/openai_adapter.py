"""SPEC §3.2: OpenAIAdapter — LLM adapter for the OpenAI API.

Uses the standard OpenAI Chat Completions endpoint.
"""

import asyncio
import json
import logging

import httpx

from harness.llm.abstract_llm import AbstractLLM, LLMFatalError
from harness.models.llm_response import LLMResponse

logger = logging.getLogger(__name__)

_OPENAI_API_BASE = "https://api.openai.com/v1"

# HTTP status codes that trigger a retry
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
# HTTP status codes that immediately fail
_FATAL_STATUS = frozenset({400, 401, 403})
# Max total attempts: 1 initial + 3 retries
_MAX_ATTEMPTS = 4


class OpenAIAdapter(AbstractLLM):
    """LLM adapter for the OpenAI API.

    Handles request formatting, response parsing, and retry logic
    internally. Does not cache, store, or modify messages.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        api_base: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._api_base = api_base or _OPENAI_API_BASE
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Release the underlying HTTP client resources."""
        await self._client.aclose()

    async def call(self, messages: list[dict]) -> LLMResponse:
        """Send messages to OpenAI and return a standardized response.

        Retries on 429, 5xx, and network errors with exponential backoff
        (1s, 2s, 4s). Fails immediately on 401, 403, 400.
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.post(
                    f"{self._api_base}/chat/completions",
                    json={
                        "model": self._model,
                        "messages": messages,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code in _RETRYABLE_STATUS:
                    if attempt < _MAX_ATTEMPTS - 1:
                        delay = 2**attempt
                        logger.debug(
                            "OpenAI API returned %d, retrying in %ds (attempt %d/%d)",
                            response.status_code,
                            delay,
                            attempt + 1,
                            _MAX_ATTEMPTS,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise LLMFatalError(
                        f"Max retries exceeded for OpenAI API. "
                        f"Last status: {response.status_code}"
                    )

                if response.status_code in _FATAL_STATUS:
                    body = response.text
                    raise LLMFatalError(
                        f"Non-retryable error from OpenAI API: "
                        f"HTTP {response.status_code}"
                        + (f" — {body}" if body else "")
                    )

                # Success — parse response
                return self._parse_response(response)

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                if attempt < _MAX_ATTEMPTS - 1:
                    delay = 2**attempt
                    logger.debug(
                        "Network error for OpenAI API, retrying in %ds: %s",
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise LLMFatalError(
                        f"Max retries exceeded for OpenAI API after network error: {e}"
                    ) from e

        # Should be unreachable — safety net
        raise LLMFatalError(
            f"Max retries exceeded for OpenAI API: {last_error}"
        )

    def _parse_response(self, response: httpx.Response) -> LLMResponse:
        """Parse a successful API response into an LLMResponse."""
        try:
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise LLMFatalError(
                f"Failed to parse API response: {type(e).__name__}: {e}"
            ) from e
        return LLMResponse(
            content=message.get("content"),
            tool_calls=message.get("tool_calls"),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
        )
