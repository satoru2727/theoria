from __future__ import annotations

import asyncio

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from theoria.agents.theoretikos import DialogueState, Theoretikos
from theoria.cli.sessions.base import BaseSession, console
from theoria.config import load_config
from theoria.providers import Message
from theoria.storage import SessionStorage, generate_session_id


class ChatSession(BaseSession[DialogueState]):
    agent_name = "Theoretikos"
    prompt_style = "blue"
    prompt_label = "You"

    def __init__(self, session_id: str | None = None) -> None:
        self.config = load_config()
        self.agent = Theoretikos(self.config)
        self.storage = SessionStorage()
        self.session_id = session_id or generate_session_id()
        self.state: DialogueState = {
            "messages": [],
            "phase": "clarify",
            "thesis": "",
            "objections": [],
            "refinements": [],
        }
        self.running = True
        self._loaded_from_storage = False

    async def load_if_exists(self) -> bool:
        result = await self.storage.load_session(self.session_id)
        if result is None:
            return False

        messages_data, state_data = result
        self.state = {
            "messages": [Message(role=m["role"], content=m["content"]) for m in messages_data],
            "phase": state_data.get("phase", "clarify"),
            "thesis": state_data.get("thesis", ""),
            "objections": state_data.get("objections", []),
            "refinements": state_data.get("refinements", []),
        }
        self._loaded_from_storage = True
        return True

    async def save(self) -> None:
        messages = self.state.get("messages", [])
        await self.storage.save_session(self.session_id, messages, dict(self.state))
        console.print(f"[dim]Session saved: {self.session_id}[/dim]\n")

    def _get_help_rows(self) -> list[tuple[str, str]]:
        return [
            ("/clear, /reset", "Clear conversation history"),
            ("/save", "Save session to disk"),
            ("/status", "Show current dialogue state"),
        ]

    def _handle_session_command(self, cmd: str) -> bool | str:
        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("/clear", "/reset"):
            self.state = {
                "messages": [],
                "phase": "clarify",
                "thesis": "",
                "objections": [],
                "refinements": [],
            }
            console.print("[dim]Session cleared.[/dim]\n")
            return True

        if cmd_lower == "/save":
            return "save"

        if cmd_lower == "/status":
            self._show_status()
            return True

        return False

    def _show_status(self) -> None:
        phase = self.state.get("phase", "clarify")
        thesis = self.state.get("thesis", "")
        msg_count = len(self.state.get("messages", []))
        obj_count = len(self.state.get("objections", []))

        status_lines = [
            f"[cyan]Session:[/cyan] {self.session_id}",
            f"[cyan]Phase:[/cyan] {phase}",
            f"[cyan]Thesis:[/cyan] {thesis or '[dim]not set[/dim]'}",
            f"[cyan]Messages:[/cyan] {msg_count}",
            f"[cyan]Objections:[/cyan] {obj_count}",
        ]
        console.print(Panel("\n".join(status_lines), title="Session Status", border_style="dim"))

    def _get_welcome_panel(self) -> Panel:
        if self._loaded_from_storage:
            return Panel(
                f"[bold]Theoretikos[/bold] - Resumed Session\n\n"
                f"[dim]Session: {self.session_id}[/dim]\n"
                f"[dim]Messages: {len(self.state.get('messages', []))}[/dim]\n"
                f"[dim]Type /help for commands.[/dim]",
                border_style="blue",
            )
        return Panel(
            "[bold]Theoretikos[/bold] - Socratic Dialogue Partner\n\n"
            "[dim]I'll help you clarify, examine, and refine your arguments.[/dim]\n"
            "[dim]Type /help for commands.[/dim]",
            border_style="blue",
        )

    async def _process_input(self, user_input: str) -> None:
        messages = self.state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]
        self.state["messages"] = messages

        if not self.state.get("thesis") and "thesis:" in user_input.lower():
            thesis_start = user_input.lower().index("thesis:")
            self.state["thesis"] = user_input[thesis_start + 7 :].strip()

        response_text = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            async for chunk in self.agent.stream_chat(user_input, self.state):
                response_text += chunk
                live.update(Markdown(response_text))

        messages = [*messages, Message(role="assistant", content=response_text)]
        self.state["messages"] = messages

    def _handle_command_result(self, cmd_result: bool | str) -> bool:
        if cmd_result == "save":
            asyncio.get_event_loop().run_until_complete(self.save())
            return True
        return bool(cmd_result)

    async def run(self) -> None:
        console.print(self._get_welcome_panel())
        console.print()

        while self.running:
            try:
                user_input = console.input("[bold blue]You:[/bold blue] ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self.handle_slash_command(user_input)
                    if cmd_result == "save":
                        await self.save()
                        continue
                    if cmd_result:
                        continue

                console.print()
                console.print("[bold green]Theoretikos:[/bold green]")
                await self._process_input(user_input)
                console.print()

            except EOFError:
                console.print("\n[dim]Goodbye.[/dim]")
                break

        await self.storage.close()
