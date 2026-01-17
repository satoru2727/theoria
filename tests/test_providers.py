from __future__ import annotations

import pytest

from theoria.errors import (
    AuthenticationError,
    LLMError,
    NetworkError,
    RateLimitError,
)
from theoria.providers import (
    CompletionResponse,
    Message,
    StreamChunk,
    _classify_error,
    _resolve_model_string,
)


class TestMessage:
    def test_create_message(self) -> None:
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"


class TestCompletionResponse:
    def test_create_response(self) -> None:
        resp = CompletionResponse(
            content="response",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
        )
        assert resp.content == "response"
        assert resp.model == "gpt-4"
        assert resp.usage is not None
        assert resp.finish_reason == "stop"

    def test_response_without_usage(self) -> None:
        resp = CompletionResponse(content="response", model="gpt-4")
        assert resp.usage is None
        assert resp.finish_reason is None


class TestStreamChunk:
    def test_create_chunk(self) -> None:
        chunk = StreamChunk(content="hello", finish_reason=None)
        assert chunk.content == "hello"
        assert chunk.finish_reason is None

    def test_chunk_with_finish_reason(self) -> None:
        chunk = StreamChunk(content="", finish_reason="stop")
        assert chunk.finish_reason == "stop"


class TestResolveModelString:
    @pytest.mark.parametrize(
        "provider,model,expected",
        [
            ("openai", "gpt-4", "gpt-4"),
            ("anthropic", "claude-3", "anthropic/claude-3"),
            ("google", "gemini-pro", "gemini/gemini-pro"),
            ("groq", "llama-3", "groq/llama-3"),
            ("mistral", "mistral-large", "mistral/mistral-large"),
            ("cohere", "command", "cohere/command"),
            ("deepseek", "deepseek-chat", "deepseek/deepseek-chat"),
            ("openrouter", "gpt-4", "openrouter/gpt-4"),
            ("ollama", "llama2", "ollama/llama2"),
        ],
    )
    def test_provider_prefixes(self, provider: str, model: str, expected: str) -> None:
        assert _resolve_model_string(provider, model) == expected

    def test_model_with_slash_unchanged(self) -> None:
        result = _resolve_model_string("openai", "openai/gpt-4")
        assert result == "openai/gpt-4"

    def test_unknown_provider_uses_provider_prefix(self) -> None:
        result = _resolve_model_string("custom", "my-model")
        assert result == "custom/my-model"


class TestClassifyError:
    def test_rate_limit_error_detected(self) -> None:
        error = Exception("Rate limit exceeded")
        result = _classify_error(error)
        assert isinstance(result, RateLimitError)

    def test_network_connection_error(self) -> None:
        error = ConnectionError("Connection refused")
        result = _classify_error(error)
        assert isinstance(result, NetworkError)

    def test_timeout_error(self) -> None:
        error = TimeoutError("Request timed out")
        result = _classify_error(error)
        assert isinstance(result, NetworkError)

    def test_network_keyword_in_message(self) -> None:
        error = Exception("Network unreachable")
        result = _classify_error(error)
        assert isinstance(result, NetworkError)

    def test_api_key_error(self) -> None:
        error = Exception("Invalid API key provided")
        result = _classify_error(error)
        assert isinstance(result, AuthenticationError)

    def test_generic_error_becomes_llm_error(self) -> None:
        error = Exception("Something went wrong")
        result = _classify_error(error)
        assert isinstance(result, LLMError)
        assert result.original is error
