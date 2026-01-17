from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
import litellm
from litellm import acompletion

from theoria.auth import store
from theoria.config import Config, load_config
from theoria.errors import AuthenticationError, LLMError, NetworkError, RateLimitError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

MAX_RETRIES = 3
RETRY_DELAY = 1.0
RETRY_MULTIPLIER = 2.0


@dataclass
class Message:
    role: str
    content: str


@dataclass
class CompletionResponse:
    content: str
    model: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: str | None = None


def _resolve_model_string(provider: str, model: str) -> str:
    provider_prefixes: dict[str, str] = {
        "openai": "",
        "anthropic": "anthropic/",
        "google": "gemini/",
        "groq": "groq/",
        "mistral": "mistral/",
        "cohere": "cohere/",
        "deepseek": "deepseek/",
        "openrouter": "openrouter/",
        "ollama": "ollama/",
    }
    prefix = provider_prefixes.get(provider, f"{provider}/")
    if model.startswith(prefix) or "/" in model:
        return model
    return f"{prefix}{model}"


def _setup_api_key(provider: str) -> None:
    api_key = store.resolve_api_key(provider)
    if not api_key:
        raise AuthenticationError(provider)

    env_var_map: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    env_var = env_var_map.get(provider, f"{provider.upper()}_API_KEY")
    litellm.api_key = api_key
    os.environ[env_var] = api_key


def _classify_error(error: Exception) -> Exception:
    error_str = str(error).lower()

    if "rate" in error_str and "limit" in error_str:
        retry_after = None
        if hasattr(error, "response"):
            retry_header = getattr(error.response, "headers", {}).get("retry-after")
            if retry_header:
                with contextlib.suppress(ValueError):
                    retry_after = float(retry_header)
        return RateLimitError(retry_after)

    if isinstance(
        error, (httpx.ConnectError, httpx.TimeoutException, ConnectionError, TimeoutError)
    ):
        return NetworkError(str(error))

    if "connection" in error_str or "timeout" in error_str or "network" in error_str:
        return NetworkError(str(error))

    if "api" in error_str and "key" in error_str:
        return AuthenticationError("unknown")

    return LLMError(str(error), original=error)


class LLMClient:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self._setup_provider()

    def _setup_provider(self) -> None:
        provider = self.config.agent.provider
        _setup_api_key(provider)

        provider_config = self.config.providers.get(provider)
        if provider_config and provider_config.api_base:
            litellm.api_base = provider_config.api_base

    @property
    def model(self) -> str:
        return _resolve_model_string(
            self.config.agent.provider,
            self.config.agent.model,
        )

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResponse:
        msg_dicts: list[dict[str, str]] = [{"role": m.role, "content": m.content} for m in messages]

        delay = RETRY_DELAY
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response: Any = await acompletion(
                    model=self.model,
                    messages=msg_dicts,
                    temperature=temperature or self.config.agent.temperature,
                    max_tokens=max_tokens or self.config.agent.max_tokens,
                )

                choice = response.choices[0]
                usage = None
                if hasattr(response, "usage") and response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                return CompletionResponse(
                    content=choice.message.content or "",
                    model=response.model,
                    usage=usage,
                    finish_reason=choice.finish_reason,
                )
            except Exception as e:
                classified = _classify_error(e)
                last_error = classified

                if isinstance(classified, RateLimitError):
                    wait_time = classified.retry_after or delay
                    await asyncio.sleep(wait_time)
                    delay *= RETRY_MULTIPLIER
                elif isinstance(classified, NetworkError) and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    delay *= RETRY_MULTIPLIER
                else:
                    raise classified from e

        raise last_error or LLMError("Unknown error after retries")

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        msg_dicts: list[dict[str, str]] = [{"role": m.role, "content": m.content} for m in messages]

        delay = RETRY_DELAY
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response: Any = await acompletion(
                    model=self.model,
                    messages=msg_dicts,
                    temperature=temperature or self.config.agent.temperature,
                    max_tokens=max_tokens or self.config.agent.max_tokens,
                    stream=True,
                )

                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        content = delta.content or ""
                        finish_reason = chunk.choices[0].finish_reason
                        if content or finish_reason:
                            yield StreamChunk(content=content, finish_reason=finish_reason)
                return
            except Exception as e:
                classified = _classify_error(e)
                last_error = classified

                if isinstance(classified, RateLimitError):
                    wait_time = classified.retry_after or delay
                    await asyncio.sleep(wait_time)
                    delay *= RETRY_MULTIPLIER
                elif isinstance(classified, NetworkError) and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    delay *= RETRY_MULTIPLIER
                else:
                    raise classified from e

        if last_error:
            raise last_error
