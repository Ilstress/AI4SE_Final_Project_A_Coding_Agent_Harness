"""Tests for LLM Adapters — SPEC §3.2, PLAN T3.1."""

from collections.abc import Sequence
from typing import Any
from unittest import mock

import httpx
import pytest

from harness.llm.abstract_llm import AbstractLLM, LLMFatalError
from harness.llm.deepseek_adapter import DeepSeekAdapter
from harness.llm.mock_adapter import MockAdapter
from harness.llm.openai_adapter import OpenAIAdapter
from harness.models.llm_response import LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(
    status_code: int = 200,
    content: str | None = "Hello!",
    tool_calls: list[dict[str, Any]] | None = None,
    finish_reason: str = "stop",
    usage: dict[str, Any] | None = None,
) -> mock.MagicMock:
    """Build a mock httpx response object."""
    response = mock.MagicMock()
    response.status_code = status_code
    response.text = ""
    message: dict[str, Any] = {"content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    response.json.return_value = {
        "choices": [
            {
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage or {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    return response


def _setup_mock_client(
    mock_client_cls: mock.MagicMock,
    responses: Sequence[mock.MagicMock | BaseException],
) -> mock.AsyncMock:
    """Configure a mock httpx.AsyncClient to return a sequence of responses.

    Args:
        mock_client_cls: The mock for httpx.AsyncClient (class).
        responses: A list of mock response objects or exceptions to return in order.
    """
    mock_client = mock.AsyncMock()
    mock_client.post = mock.AsyncMock(side_effect=responses)
    mock_client_cls.return_value = mock_client
    return mock_client


# ---------------------------------------------------------------------------
# AbstractLLM
# ---------------------------------------------------------------------------


class TestAbstractLLM:
    def test_cannot_instantiate_abstract_llm(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            AbstractLLM()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_call(self) -> None:
        class Incomplete(AbstractLLM):
            pass

        with pytest.raises(TypeError, match="abstract"):
            Incomplete()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# LLMFatalError
# ---------------------------------------------------------------------------


class TestLLMFatalError:
    def test_is_exception(self) -> None:
        with pytest.raises(LLMFatalError):
            raise LLMFatalError("test error")

    def test_message_preserved(self) -> None:
        try:
            raise LLMFatalError("API key invalid")
        except LLMFatalError as e:
            assert str(e) == "API key invalid"

    def test_can_wrap_cause(self) -> None:
        cause = ValueError("original")
        try:
            raise LLMFatalError("wrapped") from cause
        except LLMFatalError as e:
            assert e.__cause__ is cause


# ---------------------------------------------------------------------------
# DeepSeekAdapter — Construction
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterConstruction:
    def test_default_api_base(self) -> None:
        with mock.patch("httpx.AsyncClient"):
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            assert adapter._api_base == "https://api.deepseek.com/v1"

    def test_custom_api_base(self) -> None:
        with mock.patch("httpx.AsyncClient"):
            adapter = DeepSeekAdapter(
                api_key="sk-test",
                model="deepseek-chat",
                api_base="https://custom.api.com/v1",
            )
            assert adapter._api_base == "https://custom.api.com/v1"

    def test_stores_api_key_and_model(self) -> None:
        with mock.patch("httpx.AsyncClient"):
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            assert adapter._api_key == "sk-test"
            assert adapter._model == "deepseek-chat"


# ---------------------------------------------------------------------------
# DeepSeekAdapter — Successful Call
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterCallSuccess:
    @pytest.mark.asyncio
    async def test_returns_llm_response(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(content="Hello!")])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert isinstance(result, LLMResponse)
            assert result.content == "Hello!"
            assert result.finish_reason == "stop"
            assert result.usage == {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}

    @pytest.mark.asyncio
    async def test_returns_tool_calls(self) -> None:
        tool_calls = [{"id": "1", "name": "read_file", "arguments": {"path": "test.py"}}]
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(content=None, tool_calls=tool_calls)])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "read test.py"}])

            assert result.content is None
            assert result.tool_calls == tool_calls

    @pytest.mark.asyncio
    async def test_sends_correct_request_format(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = _setup_mock_client(mock_cls, [_make_mock_response()])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            messages = [{"role": "user", "content": "hi"}]

            await adapter.call(messages)

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[0][0] == "https://api.deepseek.com/v1/chat/completions"
            assert call_kwargs[1]["json"]["model"] == "deepseek-chat"
            assert call_kwargs[1]["json"]["messages"] == messages
            assert call_kwargs[1]["headers"]["Authorization"] == "Bearer sk-test"


# ---------------------------------------------------------------------------
# DeepSeekAdapter — Retry Logic
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterRetry:
    @pytest.mark.asyncio
    async def test_retries_on_429(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            _setup_mock_client(
                mock_cls,
                [
                    _make_mock_response(status_code=429),
                    _make_mock_response(content="Success after retry"),
                ],
            )
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after retry"

    @pytest.mark.asyncio
    async def test_retries_on_500(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            _setup_mock_client(
                mock_cls,
                [
                    _make_mock_response(status_code=500),
                    _make_mock_response(content="Success after server error"),
                ],
            )
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after server error"

    @pytest.mark.asyncio
    async def test_retries_on_502(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            _setup_mock_client(
                mock_cls,
                [
                    _make_mock_response(status_code=502),
                    _make_mock_response(content="Success after bad gateway"),
                ],
            )
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after bad gateway"

    @pytest.mark.asyncio
    async def test_retries_on_network_timeout(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            mock_client = mock.AsyncMock()
            mock_client.post = mock.AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    _make_mock_response(content="Success after timeout"),
                ]
            )
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after timeout"

    @pytest.mark.asyncio
    async def test_retries_on_network_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            mock_client = mock.AsyncMock()
            mock_client.post = mock.AsyncMock(
                side_effect=[
                    httpx.NetworkError("connection reset"),
                    _make_mock_response(content="Success after network error"),
                ]
            )
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after network error"

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            _setup_mock_client(mock_cls, [_make_mock_response(status_code=429)] * 4)
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Max retries"):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep") as mock_sleep:
            _setup_mock_client(
                mock_cls,
                [
                    _make_mock_response(status_code=429),
                    _make_mock_response(status_code=429),
                    _make_mock_response(status_code=429),
                    _make_mock_response(content="Success"),
                ],
            )
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            await adapter.call([{"role": "user", "content": "hi"}])

            # 3 retries: 1s, 2s, 4s
            assert mock_sleep.call_args_list == [mock.call(1), mock.call(2), mock.call(4)]


# ---------------------------------------------------------------------------
# DeepSeekAdapter — Non-Retryable Errors
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterNonRetryable:
    @pytest.mark.asyncio
    async def test_401_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep") as mock_sleep:
            _setup_mock_client(mock_cls, [_make_mock_response(status_code=401)])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Non-retryable"):
                await adapter.call([{"role": "user", "content": "hi"}])
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_403_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(status_code=403)])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_400_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(status_code=400)])
            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError):
                await adapter.call([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# OpenAIAdapter — Construction
# ---------------------------------------------------------------------------


class TestOpenAIAdapterConstruction:
    def test_default_api_base(self) -> None:
        with mock.patch("httpx.AsyncClient"):
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            assert adapter._api_base == "https://api.openai.com/v1"

    def test_stores_api_key_and_model(self) -> None:
        with mock.patch("httpx.AsyncClient"):
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            assert adapter._api_key == "sk-test"
            assert adapter._model == "gpt-4"


# ---------------------------------------------------------------------------
# OpenAIAdapter — Successful Call
# ---------------------------------------------------------------------------


class TestOpenAIAdapterCallSuccess:
    @pytest.mark.asyncio
    async def test_returns_llm_response(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(content="GPT says hello")])
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert isinstance(result, LLMResponse)
            assert result.content == "GPT says hello"
            assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_sends_correct_request_format(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = _setup_mock_client(mock_cls, [_make_mock_response()])
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            messages = [{"role": "user", "content": "hi"}]

            await adapter.call(messages)

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[0][0] == "https://api.openai.com/v1/chat/completions"
            assert call_kwargs[1]["json"]["model"] == "gpt-4"
            assert call_kwargs[1]["json"]["messages"] == messages
            assert call_kwargs[1]["headers"]["Authorization"] == "Bearer sk-test"


# ---------------------------------------------------------------------------
# OpenAIAdapter — Retry Logic
# ---------------------------------------------------------------------------


class TestOpenAIAdapterRetry:
    @pytest.mark.asyncio
    async def test_retries_on_429(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls, mock.patch("asyncio.sleep"):
            _setup_mock_client(
                mock_cls,
                [
                    _make_mock_response(status_code=429),
                    _make_mock_response(content="Success after retry"),
                ],
            )
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            result = await adapter.call([{"role": "user", "content": "hi"}])

            assert result.content == "Success after retry"

    @pytest.mark.asyncio
    async def test_401_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            _setup_mock_client(mock_cls, [_make_mock_response(status_code=401)])
            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")

            with pytest.raises(LLMFatalError):
                await adapter.call([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Resource Cleanup
# ---------------------------------------------------------------------------


class TestAdapterClose:
    @pytest.mark.asyncio
    async def test_close_calls_aclose(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
            await adapter.close()

            mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_openai_adapter_close(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            mock_cls.return_value = mock_client

            adapter = OpenAIAdapter(api_key="sk-test", model="gpt-4")
            await adapter.close()

            mock_client.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Response Parsing Errors
# ---------------------------------------------------------------------------


class TestParseResponseErrors:
    @pytest.mark.asyncio
    async def test_invalid_json_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.side_effect = __import__("json").JSONDecodeError("msg", "doc", 0)
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Failed to parse API response"):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_missing_choices_key_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = {}  # no "choices" key
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Failed to parse API response"):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_empty_choices_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = {"choices": []}  # empty list
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Failed to parse API response"):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_missing_message_key_raises_fatal_error(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = {"choices": [{}]}  # no "message" key
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="Failed to parse API response"):
                await adapter.call([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Fatal Error Body
# ---------------------------------------------------------------------------


class TestFatalErrorBody:
    @pytest.mark.asyncio
    async def test_400_includes_response_body(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 400
            response.text = '{"error": "invalid model"}'
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="invalid model"):
                await adapter.call([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_401_includes_response_body(self) -> None:
        with mock.patch("httpx.AsyncClient") as mock_cls:
            mock_client = mock.AsyncMock()
            response = mock.MagicMock()
            response.status_code = 401
            response.text = '{"error": "invalid api key"}'
            mock_client.post = mock.AsyncMock(return_value=response)
            mock_cls.return_value = mock_client

            adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")

            with pytest.raises(LLMFatalError, match="invalid api key"):
                await adapter.call([{"role": "user", "content": "hi"}])


# ============================================================================
# MockAdapter — SPEC §3.2, PLAN T3.2
# ============================================================================


# ---------------------------------------------------------------------------
# MockAdapter — Construction
# ---------------------------------------------------------------------------


class TestMockAdapterConstruction:
    def test_implements_abstract_llm(self) -> None:
        adapter = MockAdapter()
        assert isinstance(adapter, AbstractLLM)

    def test_default_call_count_is_zero(self) -> None:
        adapter = MockAdapter()
        assert adapter.call_count == 0

    def test_accepts_response_list(self) -> None:
        responses = [LLMResponse(content="Hello", tool_calls=None, finish_reason="stop", usage={})]
        adapter = MockAdapter(responses=responses)
        assert len(adapter._responses) == 1


# ---------------------------------------------------------------------------
# MockAdapter — Basic Call
# ---------------------------------------------------------------------------


class TestMockAdapterCall:
    @pytest.mark.asyncio
    async def test_returns_first_response(self) -> None:
        r1 = LLMResponse(content="First", tool_calls=None, finish_reason="stop", usage={})
        r2 = LLMResponse(content="Second", tool_calls=None, finish_reason="stop", usage={})
        adapter = MockAdapter(responses=[r1, r2])

        result = await adapter.call([{"role": "user", "content": "hi"}])

        assert result == r1
        assert result is not r1
        assert result.content == "First"

    @pytest.mark.asyncio
    async def test_returns_responses_in_order(self) -> None:
        r1 = LLMResponse(content="First", tool_calls=None, finish_reason="stop", usage={})
        r2 = LLMResponse(content="Second", tool_calls=None, finish_reason="stop", usage={})
        adapter = MockAdapter(responses=[r1, r2])

        result1 = await adapter.call([{"role": "user", "content": "hi"}])
        result2 = await adapter.call([{"role": "user", "content": "hi"}])

        assert result1 == r1
        assert result1 is not r1
        assert result2 == r2
        assert result2 is not r2

    @pytest.mark.asyncio
    async def test_returns_last_response_when_exhausted(self) -> None:
        r1 = LLMResponse(content="Only", tool_calls=None, finish_reason="stop", usage={})
        adapter = MockAdapter(responses=[r1])

        await adapter.call([])  # consume r1
        result = await adapter.call([])  # exhausted → repeat last
        result2 = await adapter.call([])  # still exhausted → repeat last

        assert result == r1
        assert result is not r1
        assert result2 == r1
        assert result2 is not r1

    @pytest.mark.asyncio
    async def test_call_count_increments(self) -> None:
        r1 = LLMResponse(content="A", tool_calls=None, finish_reason="stop", usage={})
        r2 = LLMResponse(content="B", tool_calls=None, finish_reason="stop", usage={})
        adapter = MockAdapter(responses=[r1, r2])

        assert adapter.call_count == 0
        await adapter.call([])
        assert adapter.call_count == 1
        await adapter.call([])
        assert adapter.call_count == 2
        await adapter.call([])
        assert adapter.call_count == 3

    @pytest.mark.asyncio
    async def test_empty_responses_raises(self) -> None:
        adapter = MockAdapter(responses=[])

        with pytest.raises(LLMFatalError, match="no pre-programmed"):
            await adapter.call([])

        assert adapter.call_count == 1


# ---------------------------------------------------------------------------
# MockAdapter — Scenarios
# ---------------------------------------------------------------------------


class TestMockAdapterScenarios:
    """Pre-programmed responses for testing specific Agent behaviours."""

    @pytest.mark.asyncio
    async def test_text_only_response(self) -> None:
        """Simulates LLM returning plain text (no tool call)."""
        r = LLMResponse(
            content="I think we should read the file first.",
            tool_calls=None,
            finish_reason="stop",
            usage={"total_tokens": 15},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.content is not None
        assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_tool_call_response(self) -> None:
        """Simulates LLM requesting a known tool call."""
        r = LLMResponse(
            content=None,
            tool_calls=[
                {"id": "call_1", "name": "read_file", "arguments": {"path": "src/main.py"}}
            ],
            finish_reason="tool_calls",
            usage={"total_tokens": 20},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.tool_calls is not None
        assert result.tool_calls[0]["name"] == "read_file"

    @pytest.mark.asyncio
    async def test_malformed_response(self) -> None:
        """Simulates LLM returning tool call with invalid JSON arguments."""
        r = LLMResponse(
            content=None,
            tool_calls=[
                {"id": "call_2", "name": "write_file", "arguments": "not valid json {{{"}
            ],
            finish_reason="tool_calls",
            usage={"total_tokens": 10},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.tool_calls is not None
        assert "not valid json" in result.tool_calls[0]["arguments"]

    @pytest.mark.asyncio
    async def test_unknown_tool_response(self) -> None:
        """Simulates LLM requesting a tool not in the registry."""
        r = LLMResponse(
            content=None,
            tool_calls=[
                {"id": "call_3", "name": "delete_all_files", "arguments": {}}
            ],
            finish_reason="tool_calls",
            usage={"total_tokens": 8},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.tool_calls is not None
        assert result.tool_calls[0]["name"] == "delete_all_files"

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        """Simulates LLM returning no content and no tool calls (edge case)."""
        r = LLMResponse(
            content=None,
            tool_calls=None,
            finish_reason="stop",
            usage={"total_tokens": 0},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.content is None
        assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_task_complete_response(self) -> None:
        """Simulates LLM declaring task completion."""
        r = LLMResponse(
            content=None,
            tool_calls=[
                {"id": "call_4", "name": "task_complete", "arguments": {}}
            ],
            finish_reason="tool_calls",
            usage={"total_tokens": 5},
        )
        adapter = MockAdapter(responses=[r])

        result = await adapter.call([])

        assert result.tool_calls is not None
        assert result.tool_calls[0]["name"] == "task_complete"


# ---------------------------------------------------------------------------
# MockAdapter — No Network
# ---------------------------------------------------------------------------


class TestMockAdapterNoNetwork:
    """Verify MockAdapter does not import or use httpx."""

    def test_no_httpx_import(self) -> None:
        import sys

        from harness.llm import mock_adapter

        assert "httpx" not in sys.modules or "httpx" not in dir(mock_adapter)

    @pytest.mark.asyncio
    async def test_no_network_request(self) -> None:
        """Calling MockAdapter must not trigger any network access."""
        r = LLMResponse(content="OK", tool_calls=None, finish_reason="stop", usage={})
        adapter = MockAdapter(responses=[r])

        # Should complete without any network I/O
        result = await adapter.call([])

        assert result.content == "OK"
