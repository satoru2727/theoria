from __future__ import annotations


class TheoriaError(Exception):
    """Base exception for all Theoria errors."""


class ConfigurationError(TheoriaError):
    """Configuration-related errors (API keys, settings, etc.)."""


class AuthenticationError(ConfigurationError):
    """API key or authentication not configured."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"No API key configured for provider: {provider}")


class NetworkError(TheoriaError):
    """Network-related errors (connection, timeout)."""


class RateLimitError(TheoriaError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f". Retry after {retry_after:.1f}s"
        super().__init__(msg)


class LLMError(TheoriaError):
    """LLM provider-related errors."""

    def __init__(self, message: str, original: Exception | None = None) -> None:
        self.original = original
        super().__init__(message)


def get_setup_hint(provider: str) -> str:
    """Get user-friendly setup instructions for a provider."""
    hints: dict[str, str] = {
        "openai": "Get your API key at https://platform.openai.com/api-keys",
        "anthropic": "Get your API key at https://console.anthropic.com/settings/keys",
        "google": "Get your API key at https://makersuite.google.com/app/apikey",
        "groq": "Get your API key at https://console.groq.com/keys",
        "mistral": "Get your API key at https://console.mistral.ai/api-keys",
        "cohere": "Get your API key at https://dashboard.cohere.com/api-keys",
        "deepseek": "Get your API key at https://platform.deepseek.com/api_keys",
        "openrouter": "Get your API key at https://openrouter.ai/keys",
    }
    return hints.get(provider, f"Set up your {provider} API key")


def format_auth_error(provider: str) -> str:
    """Format a user-friendly authentication error message."""
    hint = get_setup_hint(provider)
    return (
        f"[red]✗[/red] No API key found for [cyan]{provider}[/cyan]\n\n"
        f"[dim]To set up:[/dim]\n"
        f"  1. {hint}\n"
        f"  2. Run: [cyan]theoria auth add {provider} --key YOUR_KEY[/cyan]\n"
        f"     Or set: [cyan]export {provider.upper()}_API_KEY=YOUR_KEY[/cyan]"
    )


def format_network_error(error: Exception) -> str:
    """Format a user-friendly network error message."""
    return (
        f"[red]✗[/red] Network error\n\n"
        f"[dim]Details:[/dim] {error!s}\n\n"
        "[dim]Check your internet connection and try again.[/dim]"
    )


def format_rate_limit_error(retry_after: float | None = None) -> str:
    """Format a user-friendly rate limit error message."""
    msg = "[yellow]![/yellow] Rate limit exceeded\n\n"
    if retry_after:
        msg += f"[dim]Try again in {retry_after:.0f} seconds.[/dim]"
    else:
        msg += "[dim]Please wait a moment and try again.[/dim]"
    return msg


def format_llm_error(error: Exception) -> str:
    """Format a user-friendly LLM error message."""
    return (
        f"[red]✗[/red] LLM request failed\n\n"
        f"[dim]Details:[/dim] {error!s}\n\n"
        "[dim]This might be a temporary issue. Try again.[/dim]"
    )
