from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from theoria.cli.display import GOODBYE_MSG
from theoria.errors import (
    LLMError,
    NetworkError,
    RateLimitError,
    format_llm_error,
    format_network_error,
    format_rate_limit_error,
)

if TYPE_CHECKING:
    from theoria.config import Config

StateT = TypeVar("StateT")

console = Console()


class BaseSession(ABC, Generic[StateT]):
    running: bool
    config: Config
    state: StateT

    agent_name: str
    prompt_style: str
    prompt_label: str

    @abstractmethod
    def _get_help_rows(self) -> list[tuple[str, str]]: ...

    @abstractmethod
    def _handle_session_command(self, cmd: str) -> bool | str: ...

    @abstractmethod
    def _get_welcome_panel(self) -> Panel: ...

    @abstractmethod
    async def _process_input(self, user_input: str) -> None: ...

    def _show_help(self) -> None:
        help_table = Table(show_header=False, box=None)
        help_table.add_column(style="cyan")
        help_table.add_column(style="dim")

        help_table.add_row("/exit, /quit, /q", "Exit session")
        help_table.add_row("/help, /?", "Show this help")

        for cmd, desc in self._get_help_rows():
            help_table.add_row(cmd, desc)

        console.print(Panel(help_table, title="Commands", border_style="dim"))

    def _handle_common_commands(self, cmd: str) -> bool | None:
        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("/exit", "/quit", "/q"):
            console.print(f"\n{GOODBYE_MSG}")
            self.running = False
            return True

        if cmd_lower in ("/help", "/?"):
            self._show_help()
            return True

        return None

    def handle_slash_command(self, cmd: str) -> bool | str:
        result = self._handle_common_commands(cmd)
        if result is not None:
            return result
        return self._handle_session_command(cmd)

    def _handle_command_result(self, cmd_result: bool | str) -> bool:
        return bool(cmd_result)

    async def run(self) -> None:
        console.print(self._get_welcome_panel())
        console.print()

        while self.running:
            try:
                prompt = (
                    f"[bold {self.prompt_style}]{self.prompt_label}:[/bold {self.prompt_style}] "
                )
                user_input = console.input(prompt).strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self.handle_slash_command(user_input)
                    if self._handle_command_result(cmd_result):
                        continue

                console.print()
                console.print(
                    f"[bold {self.prompt_style}]{self.agent_name}:[/bold {self.prompt_style}]"
                )
                await self._process_input(user_input)
                console.print()

            except EOFError:
                console.print(f"\n{GOODBYE_MSG}")
                break
            except RateLimitError as e:
                console.print(f"\n{format_rate_limit_error(e.retry_after)}\n")
            except NetworkError as e:
                console.print(f"\n{format_network_error(e)}\n")
            except LLMError as e:
                console.print(f"\n{format_llm_error(e)}\n")
