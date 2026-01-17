from __future__ import annotations

import asyncio
from typing import Any

from theoria.config import load_config
from theoria.providers import LLMClient, Message


def format_session_markdown(
    session_id: str,
    messages: list[dict[str, str]],
    state: dict[str, Any],
    include_summary: bool = False,
) -> str:
    lines: list[str] = []

    lines.append(f"# Session: {session_id}")
    lines.append("")

    thesis = state.get("thesis", "")
    if thesis:
        lines.append(f"**Thesis:** {thesis}")
        lines.append("")

    objections = state.get("objections", [])
    if objections and isinstance(objections, list):
        lines.append(f"**Objections raised:** {len(objections)}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Dialogue")
    lines.append("")

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            lines.append("### User")
        elif role == "assistant":
            lines.append("### Assistant")
        else:
            lines.append(f"### {role.capitalize()}")

        lines.append("")
        lines.append(content)
        lines.append("")

    if include_summary:
        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        summary_text = generate_summary_sync(messages, state)
        lines.append(summary_text)
        lines.append("")

    return "\n".join(lines)


def generate_summary_sync(messages: list[dict[str, str]], state: dict[str, Any]) -> str:
    config = load_config()
    client = LLMClient(config)

    dialogue_text = "\n".join(
        f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}" for m in messages
    )

    thesis = state.get("thesis", "")
    thesis_info = f"Main thesis: {thesis}\n\n" if thesis else ""

    prompt = (
        f"{thesis_info}Dialogue:\n{dialogue_text}\n\n"
        "Provide a concise summary (2-3 paragraphs) of this academic dialogue. "
        "Include key arguments, objections raised, and conclusions reached. "
        "If sources or citations were discussed, reference them appropriately."
    )

    async def run() -> str:
        response = await client.complete(
            [
                Message(role="system", content="You are a scholarly summarizer."),
                Message(role="user", content=prompt),
            ]
        )
        return response.content

    return asyncio.run(run())
