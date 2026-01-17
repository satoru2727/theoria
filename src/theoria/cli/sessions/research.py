from __future__ import annotations

from pathlib import Path

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from theoria.agents.orchestrator import Orchestrator, OrchestratorState
from theoria.bibliography import BibManager
from theoria.cli.sessions.base import BaseSession, console
from theoria.config import load_config
from theoria.providers import Message


class ResearchSession(BaseSession[OrchestratorState]):
    agent_name = "Research"
    prompt_style = "cyan"
    prompt_label = "You"

    def __init__(self, bib_path: Path | None = None) -> None:
        self.config = load_config()
        self.orchestrator = Orchestrator(self.config)
        self.bib_manager = BibManager(bib_path) if bib_path else None
        self.state: OrchestratorState = {
            "messages": [],
            "active_agent": "theoretikos",
            "dialogue_state": {
                "messages": [],
                "phase": "clarify",
                "thesis": "",
                "objections": [],
                "refinements": [],
            },
            "search_state": {
                "messages": [],
                "query": "",
                "phase": "search",
                "search_results": [],
                "citations": [],
                "bib_entries": [],
            },
            "pending_search": None,
            "search_results": [],
        }
        self.running = True

    def _get_help_rows(self) -> list[tuple[str, str]]:
        return [
            ("/search <query>", "Search for sources"),
            ("/status", "Show current session status"),
        ]

    def _handle_session_command(self, cmd: str) -> bool | str:
        cmd_lower = cmd.lower().strip()

        if cmd_lower == "/status":
            self._show_status()
            return True

        if cmd_lower.startswith("/search "):
            return "search:" + cmd_lower[8:].strip()

        return False

    def _show_status(self) -> None:
        active = self.state.get("active_agent", "theoretikos")
        dialogue = self.state.get("dialogue_state", {})
        search = self.state.get("search_state", {})
        msg_count = len(self.state.get("messages", []))

        status_lines = [
            f"[cyan]Active Agent:[/cyan] {active}",
            f"[cyan]Messages:[/cyan] {msg_count}",
            f"[cyan]Dialogue Phase:[/cyan] {dialogue.get('phase', 'clarify')}",
            f"[cyan]Thesis:[/cyan] {dialogue.get('thesis', '') or '[dim]not set[/dim]'}",
            f"[cyan]Search Results:[/cyan] {len(search.get('bib_entries', []))}",
        ]
        console.print(Panel("\n".join(status_lines), title="Research Status", border_style="dim"))

    def _get_welcome_panel(self) -> Panel:
        return Panel(
            "[bold]Research Session[/bold] - Integrated Dialogue & Literature Search\n\n"
            "[dim]Chat naturally. Ask for sources anytime.[/dim]\n"
            "[dim]Try: 'Find evidence for...' or 'Search for papers on...'[/dim]\n"
            "[dim]Type /help for commands.[/dim]",
            border_style="cyan",
        )

    async def _process_input(self, user_input: str) -> None:
        messages = self.state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]
        self.state["messages"] = messages

        response_text = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            async for chunk in self.orchestrator.stream_chat(user_input, self.state):
                response_text += chunk
                live.update(Markdown(response_text))

        messages = [*messages, Message(role="assistant", content=response_text)]
        self.state["messages"] = messages

    async def run(self) -> None:
        console.print(self._get_welcome_panel())
        console.print()

        while self.running:
            try:
                user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self.handle_slash_command(user_input)
                    if isinstance(cmd_result, str) and cmd_result.startswith("search:"):
                        query = cmd_result[7:]
                        console.print()
                        console.print("[bold green]Bibliographos:[/bold green]")
                        await self._process_input(f"Search for sources on: {query}")
                        console.print()
                        continue
                    if cmd_result:
                        continue

                console.print()
                active = self.state.get("active_agent", "theoretikos")
                agent_name = "Theoretikos" if active == "theoretikos" else "Bibliographos"
                color = "blue" if active == "theoretikos" else "green"
                console.print(f"[bold {color}]{agent_name}:[/bold {color}]")
                await self._process_input(user_input)
                console.print()

            except EOFError:
                console.print("\n[dim]Goodbye.[/dim]")
                break
