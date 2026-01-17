from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from theoria.auth import store
from theoria.auth.oauth import (
    DEFAULT_REDIRECT_URI,
    PROVIDER_CONFIGS,
    OAuthTokens,
    build_authorize_url,
    exchange_code_for_tokens,
    generate_pkce,
    poll_for_token,
    request_device_code,
    start_oauth_flow,
    wait_for_callback,
)

console = Console()


def auth_add(
    provider: Annotated[str, typer.Argument(help="Provider ID (e.g., openai, anthropic)")],
    key: Annotated[str, typer.Option("--key", "-k", help="API key", prompt=True, hide_input=True)],
) -> None:
    """Add an API key for a provider."""
    store.set_api_key(provider, key)
    console.print(f"[green]✓[/green] API key saved for [bold]{provider}[/bold]")


def auth_remove(
    provider: Annotated[str, typer.Argument(help="Provider ID to remove")],
) -> None:
    """Remove authentication for a provider."""
    if store.remove(provider):
        console.print(f"[green]✓[/green] Removed authentication for [bold]{provider}[/bold]")
    else:
        console.print(f"[yellow]![/yellow] No authentication found for [bold]{provider}[/bold]")


def auth_list() -> None:
    """List all configured providers."""
    providers = store.list_providers()
    if not providers:
        msg = "[dim]No providers configured. Use 'theoria auth add <provider>'[/dim]"
        console.print(msg)
        return

    table = Table(title="Configured Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Source", style="dim")

    for provider_id in providers:
        auth = store.get(provider_id)
        if auth:
            auth_type = auth.type.value.upper()
            source = "config"
        else:
            auth_type = "?"
            source = "?"

        env_key = store.get_api_key_from_env(provider_id)
        if env_key:
            source = "env (overrides)"

        table.add_row(provider_id, auth_type, source)

    console.print(table)


def auth_status(
    provider: Annotated[str, typer.Argument(help="Provider ID to check")],
) -> None:
    """Check authentication status for a provider."""
    env_key = store.get_api_key_from_env(provider)
    stored_auth = store.get(provider)

    if env_key:
        console.print(f"[green]✓[/green] [bold]{provider}[/bold]: API key from env")
    elif stored_auth:
        if isinstance(stored_auth, store.ApiAuth):
            key = stored_auth.key
            masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            console.print(f"[green]✓[/green] [bold]{provider}[/bold]: API key ({masked})")
        elif isinstance(stored_auth, store.OAuthAuth):
            exp = stored_auth.expires
            console.print(f"[green]✓[/green] [bold]{provider}[/bold]: OAuth (expires: {exp})")
    else:
        console.print(f"[red]✗[/red] [bold]{provider}[/bold]: Not configured")
        console.print(f"[dim]  Use 'theoria auth add {provider}' or set environment variable[/dim]")


def auth_login(
    provider: Annotated[str, typer.Argument(help="Provider ID (must have OAuth configured)")],
    device: Annotated[
        bool, typer.Option("--device", "-d", help="Use device code flow instead of browser")
    ] = False,
    client_id: Annotated[str | None, typer.Option("--client-id", help="OAuth client ID")] = None,
    authorize_url: Annotated[
        str | None, typer.Option("--authorize-url", help="OAuth authorize endpoint")
    ] = None,
    token_url: Annotated[
        str | None, typer.Option("--token-url", help="OAuth token endpoint")
    ] = None,
    device_code_url: Annotated[
        str | None, typer.Option("--device-code-url", help="Device code endpoint (for --device)")
    ] = None,
    scope: Annotated[str, typer.Option("--scope", help="OAuth scope")] = "openid profile email",
) -> None:
    """Login via OAuth (browser or device code flow)."""
    config = PROVIDER_CONFIGS.get(provider)

    effective_client_id: str | None
    effective_authorize_url: str | None
    effective_token_url: str | None
    effective_device_code_url: str | None
    effective_scope: str

    if config:
        effective_client_id = client_id or config.client_id
        effective_authorize_url = authorize_url or config.authorize_endpoint
        effective_token_url = token_url or config.token_endpoint
        effective_device_code_url = device_code_url or config.device_code_endpoint
        effective_scope = scope or config.scope
    else:
        effective_client_id = client_id
        effective_authorize_url = authorize_url
        effective_token_url = token_url
        effective_device_code_url = device_code_url
        effective_scope = scope

    if not effective_client_id:
        console.print(f"[red]✗[/red] No OAuth configuration for [bold]{provider}[/bold]")
        console.print(
            "[dim]Provide --client-id and endpoint URLs, or use 'auth add' for API keys[/dim]"
        )
        raise typer.Exit(1)

    if device:
        _run_device_code_flow(
            provider,
            effective_client_id,
            effective_token_url,
            effective_device_code_url,
            effective_scope,
        )
    else:
        _run_browser_flow(
            provider,
            effective_client_id,
            effective_authorize_url,
            effective_token_url,
            effective_scope,
        )


def _run_browser_flow(
    provider: str,
    client_id: str,
    authorize_url: str | None,
    token_url: str | None,
    scope: str,
) -> None:
    if not authorize_url or not token_url:
        console.print("[red]✗[/red] --authorize-url and --token-url are required for browser flow")
        raise typer.Exit(1)

    pkce = generate_pkce()
    auth_url = build_authorize_url(authorize_url, client_id, DEFAULT_REDIRECT_URI, pkce, scope)

    console.print("[dim]Opening browser for authentication...[/dim]")
    if not start_oauth_flow(auth_url):
        console.print("[yellow]![/yellow] Could not open browser. Visit this URL:")
        console.print(f"  {auth_url}")

    console.print("[dim]Waiting for callback (timeout: 5 minutes)...[/dim]")
    code, state, error = wait_for_callback(timeout=300)

    if error:
        console.print(f"[red]✗[/red] OAuth error: {error}")
        raise typer.Exit(1)

    if not code or state != pkce.state:
        console.print("[red]✗[/red] Invalid or missing authorization code")
        raise typer.Exit(1)

    async def exchange() -> None:
        tokens = await exchange_code_for_tokens(
            token_url, client_id, code, DEFAULT_REDIRECT_URI, pkce.verifier
        )
        _save_oauth_tokens(provider, tokens)

    asyncio.run(exchange())
    console.print(f"[green]✓[/green] Logged in to [bold]{provider}[/bold] via OAuth")


def _run_device_code_flow(
    provider: str,
    client_id: str,
    token_url: str | None,
    device_code_url: str | None,
    scope: str,
) -> None:
    if not device_code_url or not token_url:
        console.print("[red]✗[/red] --device-code-url and --token-url required for device flow")
        raise typer.Exit(1)

    async def device_flow() -> None:
        device_resp = await request_device_code(device_code_url, client_id, scope)

        console.print(
            Panel(
                f"[bold]Enter this code:[/bold] {device_resp.user_code}\n\n"
                f"[dim]Visit:[/dim] {device_resp.verification_uri}",
                title="Device Authorization",
                border_style="cyan",
            )
        )

        with console.status("[bold cyan]Waiting for authorization...[/bold cyan]"):
            tokens = await poll_for_token(
                token_url,
                client_id,
                device_resp.device_code,
                device_resp.interval,
                device_resp.expires_in,
            )

        if tokens:
            _save_oauth_tokens(provider, tokens)
            console.print(f"[green]✓[/green] Logged in to [bold]{provider}[/bold] via device code")
        else:
            console.print("[red]✗[/red] Authorization timed out or was denied")
            raise typer.Exit(1)

    asyncio.run(device_flow())


def _save_oauth_tokens(provider: str, tokens: OAuthTokens) -> None:
    expires_timestamp = int(datetime.now(UTC).timestamp()) + tokens.expires_in
    store.set_oauth(provider, tokens.access_token, tokens.refresh_token, expires_timestamp)
