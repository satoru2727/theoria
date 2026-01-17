from __future__ import annotations

import pytest

from theoria.errors import (
    AuthenticationError,
    ConfigurationError,
    LLMError,
    NetworkError,
    RateLimitError,
    TheoriaError,
    format_auth_error,
    format_llm_error,
    format_network_error,
    format_rate_limit_error,
    get_setup_hint,
)


class TestErrorHierarchy:
    def test_theoria_error_is_exception(self) -> None:
        assert issubclass(TheoriaError, Exception)

    def test_configuration_error_inherits_theoria(self) -> None:
        assert issubclass(ConfigurationError, TheoriaError)

    def test_authentication_error_inherits_configuration(self) -> None:
        assert issubclass(AuthenticationError, ConfigurationError)

    def test_network_error_inherits_theoria(self) -> None:
        assert issubclass(NetworkError, TheoriaError)

    def test_rate_limit_error_inherits_theoria(self) -> None:
        assert issubclass(RateLimitError, TheoriaError)

    def test_llm_error_inherits_theoria(self) -> None:
        assert issubclass(LLMError, TheoriaError)


class TestAuthenticationError:
    def test_stores_provider(self) -> None:
        error = AuthenticationError("openai")
        assert error.provider == "openai"

    def test_message_includes_provider(self) -> None:
        error = AuthenticationError("anthropic")
        assert "anthropic" in str(error)


class TestRateLimitError:
    def test_stores_retry_after(self) -> None:
        error = RateLimitError(30.0)
        assert error.retry_after == 30.0

    def test_retry_after_in_message(self) -> None:
        error = RateLimitError(60.0)
        assert "60" in str(error)

    def test_no_retry_after(self) -> None:
        error = RateLimitError()
        assert error.retry_after is None


class TestLLMError:
    def test_stores_original_exception(self) -> None:
        original = ValueError("original error")
        error = LLMError("wrapped", original=original)
        assert error.original is original

    def test_message_without_original(self) -> None:
        error = LLMError("something failed")
        assert "something failed" in str(error)


class TestSetupHints:
    @pytest.mark.parametrize(
        "provider,expected_domain",
        [
            ("openai", "openai.com"),
            ("anthropic", "anthropic.com"),
            ("google", "google.com"),
            ("groq", "groq.com"),
        ],
    )
    def test_known_providers_have_urls(self, provider: str, expected_domain: str) -> None:
        hint = get_setup_hint(provider)
        assert expected_domain in hint

    def test_unknown_provider_fallback(self) -> None:
        hint = get_setup_hint("unknown_provider")
        assert "unknown_provider" in hint


class TestFormatAuthError:
    def test_includes_provider_name(self) -> None:
        msg = format_auth_error("openai")
        assert "openai" in msg

    def test_includes_setup_command(self) -> None:
        msg = format_auth_error("anthropic")
        assert "theoria auth add" in msg

    def test_includes_env_var_option(self) -> None:
        msg = format_auth_error("openai")
        assert "OPENAI_API_KEY" in msg


class TestFormatNetworkError:
    def test_includes_error_details(self) -> None:
        error = ConnectionError("Connection refused")
        msg = format_network_error(error)
        assert "Connection refused" in msg

    def test_includes_retry_suggestion(self) -> None:
        error = TimeoutError("timed out")
        msg = format_network_error(error)
        assert "try again" in msg.lower()


class TestFormatRateLimitError:
    def test_with_retry_after(self) -> None:
        msg = format_rate_limit_error(30.0)
        assert "30" in msg

    def test_without_retry_after(self) -> None:
        msg = format_rate_limit_error(None)
        assert "wait" in msg.lower()


class TestFormatLLMError:
    def test_includes_error_message(self) -> None:
        error = ValueError("invalid response")
        msg = format_llm_error(error)
        assert "invalid response" in msg

    def test_suggests_retry(self) -> None:
        error = Exception("api error")
        msg = format_llm_error(error)
        assert "try again" in msg.lower()
