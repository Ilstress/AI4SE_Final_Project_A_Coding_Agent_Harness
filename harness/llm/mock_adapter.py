"""SPEC §3.2: MockAdapter — pre-programmed LLM adapter for deterministic testing.

Returns preset responses in order. No network access, no real LLM calls.
"""

import copy

from harness.llm.abstract_llm import AbstractLLM, LLMFatalError
from harness.models.llm_response import LLMResponse


class MockAdapter(AbstractLLM):
    """LLM adapter that returns pre-programmed responses.

    Used for deterministic unit testing of the Main Loop, Feedback
    Pipeline, and Guard modules without real LLM calls or network access.

    Responses are returned in order. When exhausted, the last response
    is repeated indefinitely.

    Supports scenario injection:
        - TextOnly: LLMResponse(content="...", tool_calls=None)
        - ToolCall: LLMResponse(content=None, tool_calls=[...])
        - Malformed: tool_calls with invalid JSON arguments
        - UnknownTool: tool_calls with unregistered tool name
        - Empty: LLMResponse(content=None, tool_calls=None)
    """

    def __init__(self, responses: list[LLMResponse] | None = None) -> None:
        self._responses: list[LLMResponse] = list(responses) if responses else []
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """Number of times ``call()`` has been invoked."""
        return self._call_count

    async def call(self, messages: list[dict]) -> LLMResponse:
        """Return the next pre-programmed response.

        Does not inspect or use ``messages``. Returns responses in order.
        When exhausted, repeats the last response.
        """
        self._call_count += 1

        if not self._responses:
            raise LLMFatalError(
                "MockAdapter has no pre-programmed responses. "
                "Provide at least one LLMResponse in the constructor."
            )

        idx = min(self._call_count - 1, len(self._responses) - 1)
        return copy.deepcopy(self._responses[idx])
