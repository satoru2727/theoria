from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.panel import Panel

from theoria.cli.constants import MAX_ERRORS_DISPLAY, MAX_WARNINGS_DISPLAY

if TYPE_CHECKING:
    from rich.console import Console

LATEX_COMPILERS = [
    ("latexmk", ["-pdf", "-interaction=nonstopmode", "-halt-on-error"]),
    ("tectonic", []),
    ("pdflatex", ["-interaction=nonstopmode", "-halt-on-error"]),
]

COMPILER_ARGS_MAP = {
    "latexmk": ["-pdf", "-interaction=nonstopmode", "-halt-on-error"],
    "pdflatex": ["-interaction=nonstopmode", "-halt-on-error"],
}


def find_latex_compiler() -> tuple[str, list[str]] | None:
    for compiler, args in LATEX_COMPILERS:
        if shutil.which(compiler):
            return (compiler, args)
    return None


def get_compiler_args(compiler: str) -> list[str]:
    return COMPILER_ARGS_MAP.get(compiler, [])


def parse_latex_log(log_content: str, source_file: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    lines = log_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("!"):
            error_msg = line[1:].strip()
            line_num = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith("l."):
                    line_num = next_line.split()[0][2:]
            if line_num:
                errors.append(f"{source_file.name}:{line_num}: {error_msg}")
            else:
                errors.append(f"{source_file.name}: {error_msg}")
            i += 1

        elif "LaTeX Warning:" in line or line.startswith(("Overfull", "Underfull")):
            warnings.append(line.strip())

        i += 1

    return errors, warnings


def display_verbose_output(result: subprocess.CompletedProcess[str], console: Console) -> None:
    if result.stdout:
        console.print(Panel(result.stdout, title="Output", border_style="dim"))
    if result.stderr:
        console.print(Panel(result.stderr, title="Stderr", border_style="yellow"))


def display_log_issues(file: Path, console: Console) -> None:
    log_file = file.with_suffix(".log")
    if not log_file.exists():
        return

    log_content = log_file.read_text(errors="ignore")
    errors, warnings = parse_latex_log(log_content, file)

    if errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in errors[:MAX_ERRORS_DISPLAY]:
            console.print(f"  [red]✗[/red] {err}")
        if len(errors) > MAX_ERRORS_DISPLAY:
            console.print(f"  [dim]... and {len(errors) - MAX_ERRORS_DISPLAY} more errors[/dim]")
    elif warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warn in warnings[:MAX_WARNINGS_DISPLAY]:
            console.print(f"  [yellow]![/yellow] {warn}")
        if len(warnings) > MAX_WARNINGS_DISPLAY:
            console.print(
                f"  [dim]... and {len(warnings) - MAX_WARNINGS_DISPLAY} more warnings[/dim]"
            )


def display_compile_status(
    result: subprocess.CompletedProcess[str], file: Path, console: Console
) -> None:
    if result.returncode == 0:
        pdf_file = file.with_suffix(".pdf")
        if pdf_file.exists():
            console.print(f"\n[green]✓[/green] Compiled successfully: {pdf_file}")
        else:
            console.print("\n[green]✓[/green] Compilation finished (exit code 0)")
    else:
        console.print(f"\n[red]✗[/red] Compilation failed (exit code {result.returncode})")


def display_compile_result(
    result: subprocess.CompletedProcess[str],
    file: Path,
    verbose: bool,
    console: Console,
) -> None:
    if verbose:
        display_verbose_output(result, console)
    display_log_issues(file, console)
    display_compile_status(result, file, console)
