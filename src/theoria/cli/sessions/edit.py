from __future__ import annotations

import difflib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from theoria.agents.graphos import Graphos
from theoria.cli.constants import MAX_ISSUES_DISPLAY
from theoria.cli.sessions.base import BaseSession, console
from theoria.config import load_config
from theoria.latex import check_label_ref_integrity, parse_document


class EditSession(BaseSession[dict[str, Any]]):
    agent_name = "Graphos"
    prompt_style = "magenta"
    prompt_label = "Edit"

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path.resolve()
        self.config = load_config()
        self.agent = Graphos(self.config)
        self.original_content = ""
        self.current_content = ""
        self.running = True
        self.state: dict[str, Any] = {}

    def create_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.file_path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(self.file_path, backup_path)
        return backup_path

    def show_diff(self, original: str, modified: str) -> None:
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{self.file_path.name}",
            tofile=f"b/{self.file_path.name}",
            lineterm="",
        )

        diff_text = "".join(diff)
        if diff_text:
            console.print(Syntax(diff_text, "diff", theme="monokai"))
        else:
            console.print("[dim]No changes[/dim]")

    def _get_help_rows(self) -> list[tuple[str, str]]:
        return [
            ("/diff", "Show current changes"),
            ("/apply", "Apply changes to file"),
            ("/revert", "Revert to original content"),
            ("/check", "Check label/ref integrity"),
        ]

    def _handle_session_command(self, cmd: str) -> bool | str:
        command_map = {"/diff": "diff", "/apply": "apply", "/revert": "revert", "/check": "check"}
        return command_map.get(cmd.lower().strip(), False)

    def _get_welcome_panel(self) -> Panel:
        return Panel(
            f"[bold]Graphos[/bold] - LaTeX Editor\n\n"
            f"[dim]Editing: {self.file_path}[/dim]\n"
            f"[dim]Type instructions or /help for commands.[/dim]",
            border_style="magenta",
        )

    async def _process_input(self, user_input: str) -> None:
        response_text = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            async for chunk in self.agent.stream_edit(
                user_input, content=self.current_content, file_path=self.file_path
            ):
                response_text += chunk
                live.update(Markdown(response_text))

        edited_content = self.agent._extract_latex(response_text)
        if edited_content and edited_content != response_text:
            self.current_content = edited_content
            console.print("\n[dim]Use /diff to see changes, /apply to save.[/dim]")

    def apply_changes(self) -> None:
        if self.current_content == self.original_content:
            console.print("[dim]No changes to apply.[/dim]")
            return

        backup = self.create_backup()
        console.print(f"[dim]Backup created: {backup}[/dim]")

        self.file_path.write_text(self.current_content)
        console.print(f"[green]✓[/green] Changes applied to {self.file_path}")
        self.original_content = self.current_content

    def revert_changes(self) -> None:
        self.current_content = self.original_content
        console.print("[dim]Reverted to original content.[/dim]")

    def check_integrity(self) -> None:
        structure = parse_document(self.file_path)
        issues = check_label_ref_integrity(structure)

        if not issues:
            console.print("[green]✓[/green] No label/ref issues found.")
            return

        table = Table(title="Label/Ref Issues")
        table.add_column("Type", style="yellow")
        table.add_column("Name", style="cyan")
        table.add_column("Location", style="dim")

        for issue in issues:
            loc_str = ", ".join(f"{p.name}:{ln}" for p, ln in issue.locations[:MAX_ISSUES_DISPLAY])
            if len(issue.locations) > MAX_ISSUES_DISPLAY:
                loc_str += f" (+{len(issue.locations) - MAX_ISSUES_DISPLAY} more)"
            table.add_row(issue.issue_type, issue.name, loc_str)

        console.print(table)

    async def run(self) -> None:
        if not self.file_path.exists():
            console.print(f"[red]✗[/red] File not found: {self.file_path}")
            return

        self.original_content = self.file_path.read_text()
        self.current_content = self.original_content

        console.print(self._get_welcome_panel())
        console.print()

        while self.running:
            try:
                user_input = console.input("[bold magenta]Edit:[/bold magenta] ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self.handle_slash_command(user_input)
                    if cmd_result == "diff":
                        self.show_diff(self.original_content, self.current_content)
                        continue
                    if cmd_result == "apply":
                        self.apply_changes()
                        continue
                    if cmd_result == "revert":
                        self.revert_changes()
                        continue
                    if cmd_result == "check":
                        self.check_integrity()
                        continue
                    if cmd_result:
                        continue

                console.print()
                console.print("[bold cyan]Graphos:[/bold cyan]")
                await self._process_input(user_input)
                console.print()

            except EOFError:
                console.print("\n[dim]Goodbye.[/dim]")
                break
