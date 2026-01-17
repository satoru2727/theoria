from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from theoria import __version__
from theoria.auth import store

app = typer.Typer(
    name="theoria",
    help="Humanities research & LaTeX drafting agentic CLI",
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Manage authentication for LLM providers")
app.add_typer(auth_app, name="auth")

console = Console()


@app.command()
def version() -> None:
    console.print(f"theoria {__version__}")


@app.command()
def init() -> None:
    console.print("[yellow]Initializing theoria project...[/yellow]")


@app.command()
def chat() -> None:
    console.print("[yellow]Starting chat session...[/yellow]")


@auth_app.command("add")
def auth_add(
    provider: Annotated[str, typer.Argument(help="Provider ID (e.g., openai, anthropic)")],
    key: Annotated[str, typer.Option("--key", "-k", help="API key", prompt=True, hide_input=True)],
) -> None:
    """Add an API key for a provider."""
    store.set_api_key(provider, key)
    console.print(f"[green]✓[/green] API key saved for [bold]{provider}[/bold]")


@auth_app.command("remove")
def auth_remove(
    provider: Annotated[str, typer.Argument(help="Provider ID to remove")],
) -> None:
    """Remove authentication for a provider."""
    if store.remove(provider):
        console.print(f"[green]✓[/green] Removed authentication for [bold]{provider}[/bold]")
    else:
        console.print(f"[yellow]![/yellow] No authentication found for [bold]{provider}[/bold]")


@auth_app.command("list")
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

        # Check if env var is available
        env_key = store.get_api_key_from_env(provider_id)
        if env_key:
            source = "env (overrides)"

        table.add_row(provider_id, auth_type, source)

    console.print(table)


@auth_app.command("status")
def auth_status(
    provider: Annotated[str, typer.Argument(help="Provider ID to check")],
) -> None:
    """Check authentication status for a provider."""
    # Check env first
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


if __name__ == "__main__":
    app()
