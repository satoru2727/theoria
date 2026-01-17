from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from theoria.providers import LLMClient, Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from theoria.config import Config


class EditOperation(TypedDict):
    type: Literal["insert", "replace", "delete"]
    line_start: int
    line_end: int | None
    content: str | None


class LatexState(TypedDict, total=False):
    messages: list[Message]
    file_path: str
    content: str
    phase: Literal["analyze", "edit", "repair", "end"]
    edits: list[EditOperation]
    errors: list[str]


def _default_state() -> LatexState:
    return {
        "messages": [],
        "file_path": "",
        "content": "",
        "phase": "analyze",
        "edits": [],
        "errors": [],
    }


SYSTEM_PROMPT = """You are Graphos, a LaTeX editing assistant specializing in academic document \
preparation.

Your responsibilities:
- Edit LaTeX documents based on user instructions
- Maintain document structure and formatting consistency
- Repair common LaTeX syntax errors
- Preserve existing style and conventions
- Handle citations, references, and cross-references properly

Current phase: {phase}
- analyze: Understand the document structure and user request
- edit: Make requested changes to the document
- repair: Fix syntax errors and validate structure

Respond in the user's language. Preserve document integrity."""


LATEX_ERROR_PATTERNS = [
    (r"\\begin\{([^}]+)\}(?![\s\S]*\\end\{\1\})", "Unclosed environment: {0}"),
    (r"(?<!\\)\$(?!.*(?<!\\)\$)", "Unclosed math mode"),
    (r"\{(?![^{}]*\})", "Unclosed brace"),
    (r"\\cite\{\s*\}", "Empty citation"),
    (r"\\ref\{\s*\}", "Empty reference"),
]


class Graphos:
    def __init__(self, config: Config | None = None) -> None:
        self.client = LLMClient(config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph[LatexState]:
        graph: StateGraph[LatexState] = StateGraph(LatexState)

        graph.add_node("analyze", self._analyze_node)
        graph.add_node("edit", self._edit_node)
        graph.add_node("repair", self._repair_node)

        graph.set_entry_point("analyze")

        graph.add_conditional_edges(
            "analyze",
            self._route_from_analyze,
            {"edit": "edit", "repair": "repair", "end": END},
        )
        graph.add_conditional_edges(
            "edit",
            self._route_from_edit,
            {"repair": "repair", "end": END},
        )
        graph.add_conditional_edges(
            "repair",
            self._route_from_repair,
            {"edit": "edit", "end": END},
        )

        return graph

    async def _analyze_node(self, state: LatexState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="analyze"))
        content = state.get("content", "")
        messages = state.get("messages", [])

        errors = self._check_syntax(content)

        analyze_prompt = (
            f"Analyze this LaTeX document:\n\n```latex\n{content[:2000]}\n```\n\n"
            "Identify:\n"
            "1. Document class and structure\n"
            "2. Packages used\n"
            "3. Any potential issues or improvements"
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=analyze_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        next_phase: Literal["edit", "repair"] = "repair" if errors else "edit"
        return {"messages": new_messages, "errors": errors, "phase": next_phase}

    async def _edit_node(self, state: LatexState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="edit"))
        content = state.get("content", "")
        messages = state.get("messages", [])

        edit_prompt = (
            "Based on the analysis, provide the edited LaTeX content.\n"
            "Output ONLY the complete modified LaTeX document, no explanations.\n\n"
            f"Current document:\n```latex\n{content}\n```"
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=edit_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        edited_content = self._extract_latex(response.content)
        new_errors = self._check_syntax(edited_content)

        return {
            "messages": new_messages,
            "content": edited_content,
            "errors": new_errors,
            "phase": "repair" if new_errors else "end",
        }

    async def _repair_node(self, state: LatexState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="repair"))
        content = state.get("content", "")
        errors = state.get("errors", [])
        messages = state.get("messages", [])

        error_list = "\n".join(f"- {e}" for e in errors)
        repair_prompt = (
            f"Fix these LaTeX syntax errors:\n{error_list}\n\n"
            "In this document:\n```latex\n{content}\n```\n\n"
            "Output ONLY the corrected LaTeX document."
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=repair_prompt.format(content=content)),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        repaired_content = self._extract_latex(response.content)
        new_errors = self._check_syntax(repaired_content)

        return {
            "messages": new_messages,
            "content": repaired_content,
            "errors": new_errors,
            "phase": "end",
        }

    def _route_from_analyze(self, state: LatexState) -> str:
        if state.get("phase") == "end":
            return "end"
        errors = state.get("errors", [])
        return "repair" if errors else "edit"

    def _route_from_edit(self, state: LatexState) -> str:
        if state.get("phase") == "end":
            return "end"
        errors = state.get("errors", [])
        return "repair" if errors else "end"

    def _route_from_repair(self, _state: LatexState) -> str:
        return "end"

    def _check_syntax(self, content: str) -> list[str]:
        errors: list[str] = []
        for pattern, message in LATEX_ERROR_PATTERNS:
            match = re.search(pattern, content)
            if match:
                groups = match.groups()
                formatted = message.format(*groups) if groups else message
                errors.append(formatted)
        return errors

    def _extract_latex(self, response: str) -> str:
        latex_match = re.search(r"```latex\n([\s\S]*?)\n```", response)
        if latex_match:
            return latex_match.group(1)
        tex_match = re.search(r"```tex\n([\s\S]*?)\n```", response)
        if tex_match:
            return tex_match.group(1)
        code_match = re.search(r"```\n([\s\S]*?)\n```", response)
        if code_match:
            return code_match.group(1)
        return response

    async def edit(
        self,
        instruction: str,
        content: str | None = None,
        file_path: str | Path | None = None,
    ) -> LatexState:
        state = _default_state()

        if file_path:
            path = Path(file_path)
            if path.exists():
                content = path.read_text()
                state["file_path"] = str(path)

        if content:
            state["content"] = content

        messages = [Message(role="user", content=instruction)]
        state["messages"] = messages

        compiled = self.graph.compile()
        result = await compiled.ainvoke(cast("Any", state))
        return dict(result)  # type: ignore[return-value]

    async def stream_edit(
        self,
        instruction: str,
        content: str | None = None,
        file_path: str | Path | None = None,
    ) -> AsyncIterator[str]:
        if file_path:
            path = Path(file_path)
            if path.exists():
                content = path.read_text()

        if not content:
            content = ""

        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="edit"))
        edit_prompt = (
            f"{instruction}\n\nDocument:\n```latex\n{content}\n```\n\nProvide the edited LaTeX."
        )
        messages = [system, Message(role="user", content=edit_prompt)]

        async for chunk in self.client.stream(messages):
            yield chunk.content

    def repair(self, content: str) -> tuple[str, list[str]]:
        errors = self._check_syntax(content)
        if not errors:
            return content, []

        repaired = content
        repaired = re.sub(
            r"\\begin\{([^}]+)\}([\s\S]*?)(?=\\begin\{|\Z)",
            lambda m: (
                f"\\begin{{{m.group(1)}}}{m.group(2)}\\end{{{m.group(1)}}}\n"
                if f"\\end{{{m.group(1)}}}" not in m.group(2)
                else m.group(0)
            ),
            repaired,
        )

        remaining_errors = self._check_syntax(repaired)
        return repaired, remaining_errors
