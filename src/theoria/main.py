from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from theoria import __version__
from theoria.bibliography import BibManager
from theoria.cli.auth_commands import (
    auth_add,
    auth_list,
    auth_login,
    auth_remove,
    auth_status,
)
from theoria.cli.compile import (
    display_compile_result,
    find_latex_compiler,
    get_compiler_args,
)
from theoria.cli.constants import DEFAULT_HISTORY_LIMIT
from theoria.cli.export import format_session_markdown
from theoria.cli.runner import run_session
from theoria.cli.sessions import ChatSession, EditSession, ResearchSession, SearchSession
from theoria.config.loader import init_project_config
from theoria.latex import check_label_ref_integrity, parse_document
from theoria.storage import SessionStorage

app = typer.Typer(
    name="theoria",
    help="Humanities research & LaTeX drafting agentic CLI",
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Manage authentication for LLM providers")
app.add_typer(auth_app, name="auth")

console = Console()

auth_app.command("add")(auth_add)
auth_app.command("remove")(auth_remove)
auth_app.command("list")(auth_list)
auth_app.command("status")(auth_status)
auth_app.command("login")(auth_login)


@app.command()
def version() -> None:
    console.print(f"theoria {__version__}")


@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing config")] = False,
) -> None:
    cwd = Path.cwd()
    config_file = cwd / "config.theoria.yaml"

    if config_file.exists() and not force:
        console.print(f"[yellow]![/yellow] Config already exists: {config_file}")
        console.print("[dim]Use --force to overwrite[/dim]")
        return

    bib_files = list(cwd.glob("*.bib"))
    tex_files = list(cwd.glob("**/*.tex"))

    init_project_config(cwd)
    console.print(f"[green]✓[/green] Created {config_file}")

    if bib_files:
        console.print(f"[dim]  Found .bib files: {', '.join(f.name for f in bib_files[:3])}[/dim]")
    if tex_files:
        console.print(f"[dim]  Found .tex files: {len(tex_files)} file(s)[/dim]")


@app.command()
def chat(
    session: Annotated[
        str | None,
        typer.Option("--session", "-s", help="Resume existing session by ID"),
    ] = None,
) -> None:
    run_session(ChatSession(session), console)


@app.command()
def history(
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Max sessions to show")
    ] = DEFAULT_HISTORY_LIMIT,
) -> None:
    async def show_history() -> None:
        storage = SessionStorage()
        table = Table(title="Saved Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Messages", justify="right")
        table.add_column("Updated", style="dim")

        count = 0
        async for sess in storage.list_sessions(limit):
            table.add_row(
                sess["id"],
                sess["title"][:40] + ("..." if len(sess["title"]) > 40 else ""),
                str(sess["message_count"]),
                sess["updated_at"][:19].replace("T", " "),
            )
            count += 1

        await storage.close()

        if count == 0:
            console.print("[dim]No saved sessions. Use /save in chat to save a session.[/dim]")
            return

        console.print(table)
        console.print("\n[dim]Resume with: theoria chat --session <ID>[/dim]")

    asyncio.run(show_history())


@app.command()
def export(
    session_id: Annotated[str, typer.Argument(help="Session ID to export")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (default: stdout)"),
    ] = None,
    summary: Annotated[
        bool, typer.Option("--summary", "-s", help="Generate AI summary with citations")
    ] = False,
) -> None:
    async def do_export() -> str | None:
        storage = SessionStorage()
        result = await storage.load_session(session_id)
        await storage.close()

        if result is None:
            console.print(f"[red]✗[/red] Session not found: {session_id}")
            return None

        messages_data, state_data = result
        return format_session_markdown(session_id, messages_data, state_data, summary)

    md_content = asyncio.run(do_export())
    if md_content is None:
        raise typer.Exit(1)

    if output:
        output.write_text(md_content)
        console.print(f"[green]✓[/green] Exported to {output}")
    else:
        console.print(md_content)


@app.command()
def search(
    bib: Annotated[
        Path | None,
        typer.Option("--bib", "-b", help="Path to .bib file for adding entries"),
    ] = None,
) -> None:
    run_session(SearchSession(bib), console)


@app.command()
def research(
    bib: Annotated[
        Path | None,
        typer.Option("--bib", "-b", help="Path to .bib file for adding entries"),
    ] = None,
) -> None:
    run_session(ResearchSession(bib), console)


@app.command()
def cite(
    query: Annotated[str, typer.Argument(help="Search query for citation key")],
    bib: Annotated[
        Path,
        typer.Option("--bib", "-b", help="Path to .bib file"),
    ] = Path("references.bib"),
    copy: Annotated[bool, typer.Option("--copy", "-c", help="Copy to clipboard")] = False,
) -> None:
    if not bib.exists():
        console.print(f"[red]✗[/red] File not found: {bib}")
        raise typer.Exit(1)

    manager = BibManager(bib)
    results = manager.search(query)

    if not results:
        console.print(f"[dim]No matches for '{query}'[/dim]")
        return

    table = Table(title=f"Matches for '{query}'")
    table.add_column("Key", style="cyan")
    table.add_column("Author", style="white")
    table.add_column("Year", style="dim")
    table.add_column("Title", style="white")

    for entry in results[:10]:
        table.add_row(
            entry.key,
            entry.author[:25] + ("..." if len(entry.author) > 25 else ""),
            entry.year,
            entry.title[:35] + ("..." if len(entry.title) > 35 else ""),
        )

    console.print(table)

    if len(results) == 1 or copy:
        key = results[0].key
        cite_str = f"\\cite{{{key}}}"
        if copy:
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=cite_str.encode(),
                    check=True,
                )
                console.print(f"\n[green]✓[/green] Copied to clipboard: [cyan]{cite_str}[/cyan]")
            except (FileNotFoundError, subprocess.CalledProcessError):
                try:
                    subprocess.run(
                        ["pbcopy"],
                        input=cite_str.encode(),
                        check=True,
                    )
                    console.print(
                        f"\n[green]✓[/green] Copied to clipboard: [cyan]{cite_str}[/cyan]"
                    )
                except (FileNotFoundError, subprocess.CalledProcessError):
                    console.print(f"\n[dim]Citation: {cite_str}[/dim]")
        else:
            console.print(f"\n[dim]Citation: {cite_str}[/dim]")


@app.command()
def edit(
    file: Annotated[Path, typer.Argument(help="LaTeX file to edit")],
) -> None:
    run_session(EditSession(file), console)


@app.command()
def compile(
    file: Annotated[Path, typer.Argument(help="Main LaTeX file to compile")],
    compiler: Annotated[
        str | None,
        typer.Option("--compiler", "-c", help="Compiler to use (latexmk, tectonic, pdflatex)"),
    ] = None,
    clean: Annotated[bool, typer.Option("--clean", help="Clean auxiliary files after")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show full output")] = False,
) -> None:
    if not file.exists():
        console.print(f"[red]✗[/red] File not found: {file}")
        raise typer.Exit(1)

    if compiler:
        if not shutil.which(compiler):
            console.print(f"[red]✗[/red] Compiler not found: {compiler}")
            raise typer.Exit(1)
        compiler_cmd = compiler
        compiler_args = get_compiler_args(compiler)
    else:
        found = find_latex_compiler()
        if not found:
            console.print("[red]✗[/red] No LaTeX compiler found.")
            console.print("[dim]Install latexmk, tectonic, or pdflatex.[/dim]")
            raise typer.Exit(1)
        compiler_cmd, compiler_args = found

    console.print(f"[dim]Using {compiler_cmd}...[/dim]")

    cmd = [compiler_cmd, *compiler_args, str(file.name)]

    with console.status(f"[bold cyan]Compiling {file.name}...[/bold cyan]"):
        result = subprocess.run(
            cmd,
            cwd=file.parent,
            capture_output=True,
            text=True,
            check=False,
        )

    display_compile_result(result, file, verbose, console)

    if clean and compiler_cmd == "latexmk":
        subprocess.run(
            ["latexmk", "-c"],
            cwd=file.parent,
            capture_output=True,
            check=False,
        )
        console.print("[dim]Cleaned auxiliary files.[/dim]")


@app.command()
def check(
    file: Annotated[Path, typer.Argument(help="Main LaTeX file to check")],
) -> None:
    if not file.exists():
        console.print(f"[red]✗[/red] File not found: {file}")
        raise typer.Exit(1)

    console.print(f"[dim]Analyzing {file}...[/dim]\n")

    structure = parse_document(file)

    console.print(f"[cyan]Document class:[/cyan] {structure.document_class or 'unknown'}")
    console.print(f"[cyan]Files:[/cyan] {len(structure.files)}")
    console.print(f"[cyan]Sections:[/cyan] {len(structure.sections)}")
    console.print(f"[cyan]Labels:[/cyan] {len(structure.labels)}")
    console.print(f"[cyan]References:[/cyan] {len(structure.refs)}")
    console.print()

    issues = check_label_ref_integrity(structure)

    if not issues:
        console.print("[green]✓[/green] No issues found.")
        return

    undefined = [i for i in issues if i.issue_type == "undefined"]
    duplicate = [i for i in issues if i.issue_type == "duplicate"]
    unused = [i for i in issues if i.issue_type == "unused"]

    if undefined:
        console.print("[bold red]Undefined references:[/bold red]")
        for issue in undefined:
            loc_str = ", ".join(f"{p.name}:{ln}" for p, ln in issue.locations[:3])
            console.print(f"  [red]✗[/red] {issue.name} at {loc_str}")
        console.print()

    if duplicate:
        console.print("[bold yellow]Duplicate labels:[/bold yellow]")
        for issue in duplicate:
            loc_str = ", ".join(f"{p.name}:{ln}" for p, ln in issue.locations)
            console.print(f"  [yellow]![/yellow] {issue.name} at {loc_str}")
        console.print()

    if unused:
        console.print("[dim]Unused labels:[/dim]")
        for issue in unused[:10]:
            loc_str = ", ".join(f"{p.name}:{ln}" for p, ln in issue.locations)
            console.print(f"  [dim]-[/dim] {issue.name} at {loc_str}")
        if len(unused) > 10:
            console.print(f"  [dim]... and {len(unused) - 10} more unused labels[/dim]")


if __name__ == "__main__":
    app()
