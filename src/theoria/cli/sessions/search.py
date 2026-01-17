from __future__ import annotations

from pathlib import Path

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from theoria.agents.bibliographos import Bibliographos, SearchState
from theoria.bibliography import BibManager, parse_bibtex
from theoria.cli.constants import DEFAULT_ENTRIES_DISPLAY_LIMIT
from theoria.cli.display import truncate
from theoria.cli.sessions.base import BaseSession, console
from theoria.config import load_config
from theoria.providers import Message


class SearchSession(BaseSession[SearchState]):
    agent_name = "Bibliographos"
    prompt_style = "green"
    prompt_label = "Search"

    def __init__(self, bib_path: Path | None = None) -> None:
        self.config = load_config()
        self.agent = Bibliographos(self.config)
        self.bib_manager = BibManager(bib_path) if bib_path else None
        self.state: SearchState = {
            "messages": [],
            "query": "",
            "phase": "search",
            "search_results": [],
            "citations": [],
            "bib_entries": [],
        }
        self.running = True

    def _get_help_rows(self) -> list[tuple[str, str]]:
        return [
            ("/add", "Add last results to .bib file"),
            ("/show", "Show current .bib entries"),
        ]

    def _handle_session_command(self, cmd: str) -> bool | str:
        cmd_lower = cmd.lower().strip()

        if cmd_lower == "/add":
            return "add"

        if cmd_lower == "/show":
            return "show"

        return False

    def _get_welcome_panel(self) -> Panel:
        return Panel(
            "[bold]Bibliographos[/bold] - Research Assistant\n\n"
            "[dim]Search for academic sources and generate BibTeX entries.[/dim]\n"
            "[dim]Type /help for commands.[/dim]",
            border_style="green",
        )

    async def _process_input(self, user_input: str) -> None:
        self.state["query"] = user_input
        messages = self.state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]
        self.state["messages"] = messages

        response_text = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            async for chunk in self.agent.stream_search(user_input, self.state):
                response_text += chunk
                live.update(Markdown(response_text))

        messages = [*messages, Message(role="assistant", content=response_text)]
        self.state["messages"] = messages
        self.state["bib_entries"] = [*self.state.get("bib_entries", []), response_text]

    def add_to_bib(self) -> None:
        if not self.bib_manager:
            console.print("[yellow]![/yellow] No .bib file specified. Use --bib option.")
            return

        bib_entries = self.state.get("bib_entries", [])
        if not bib_entries:
            console.print("[dim]No entries to add.[/dim]")
            return

        last_response = bib_entries[-1]
        try:
            entries = parse_bibtex(last_response)
            if entries:
                added = self.bib_manager.add_many(entries)
                self.bib_manager.save()
                console.print(
                    f"[green]✓[/green] Added {added} entries to {self.bib_manager.bib_path}"
                )
            else:
                console.print("[yellow]![/yellow] No valid BibTeX entries found in response.")
        except (ValueError, KeyError):
            console.print("[yellow]![/yellow] Could not parse BibTeX from response.")

    def show_bib(self) -> None:
        if not self.bib_manager:
            console.print("[yellow]![/yellow] No .bib file specified.")
            return

        entries = self.bib_manager.entries
        if not entries:
            console.print("[dim]No entries in .bib file.[/dim]")
            return

        table = Table(title=f"Entries in {self.bib_manager.bib_path}")
        table.add_column("Key", style="cyan")
        table.add_column("Author", style="white")
        table.add_column("Year", style="dim")
        table.add_column("Title", style="white")

        for entry in entries[:DEFAULT_ENTRIES_DISPLAY_LIMIT]:
            table.add_row(
                entry.key,
                truncate(entry.author, 30),
                entry.year,
                truncate(entry.title, 40),
            )

        console.print(table)
        if len(entries) > DEFAULT_ENTRIES_DISPLAY_LIMIT:
            console.print(
                f"[dim]... and {len(entries) - DEFAULT_ENTRIES_DISPLAY_LIMIT} more entries[/dim]"
            )

    async def run(self) -> None:
        console.print(self._get_welcome_panel())
        console.print()

        while self.running:
            try:
                user_input = console.input("[bold green]Search:[/bold green] ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self.handle_slash_command(user_input)
                    if cmd_result == "add":
                        self.add_to_bib()
                        continue
                    if cmd_result == "show":
                        self.show_bib()
                        continue
                    if cmd_result:
                        continue

                console.print()
                console.print("[bold cyan]Bibliographos:[/bold cyan]")
                await self._process_input(user_input)
                console.print()

            except EOFError:
                console.print("\n[dim]Goodbye.[/dim]")
                break
