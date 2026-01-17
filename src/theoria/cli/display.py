from __future__ import annotations

GOODBYE_MSG = "[dim]Goodbye.[/dim]"
INTERRUPTED_MSG = "\n\n[dim]Interrupted. Goodbye.[/dim]"


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
