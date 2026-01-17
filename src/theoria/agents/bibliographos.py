from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from theoria.providers import LLMClient, Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from theoria.config import Config


class Citation(TypedDict):
    key: str
    type: str
    title: str
    authors: list[str]
    year: str
    source: str
    doi: str | None
    url: str | None
    abstract: str | None


class SearchState(TypedDict, total=False):
    messages: list[Message]
    query: str
    phase: Literal["search", "extract", "validate", "end"]
    search_results: list[dict[str, Any]]
    citations: list[Citation]
    bib_entries: list[str]


def _default_state() -> SearchState:
    return {
        "messages": [],
        "query": "",
        "phase": "search",
        "search_results": [],
        "citations": [],
        "bib_entries": [],
    }


SYSTEM_PROMPT = """You are Bibliographos, a scholarly research assistant specializing in \
literature search, citation management, and BibTeX generation.

Your responsibilities:
- Search for relevant academic sources based on user queries
- Extract citation metadata from sources
- Generate properly formatted BibTeX entries
- Validate citation completeness and accuracy
- Maintain citation traceability - every claim needs a source

Current phase: {phase}
- search: Find relevant academic sources
- extract: Extract citation metadata from found sources
- validate: Verify citation completeness and format BibTeX

Respond in the user's language. Be thorough but concise."""

BIBTEX_TEMPLATE = """@{entry_type}{{{key},
  author = {{{authors}}},
  title = {{{title}}},
  year = {{{year}}},
  {optional_fields}
}}"""


class Bibliographos:
    def __init__(self, config: Config | None = None) -> None:
        self.client = LLMClient(config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph[SearchState]:
        graph: StateGraph[SearchState] = StateGraph(SearchState)

        graph.add_node("search", self._search_node)
        graph.add_node("extract", self._extract_node)
        graph.add_node("validate", self._validate_node)

        graph.set_entry_point("search")

        graph.add_conditional_edges(
            "search",
            self._route_from_search,
            {"extract": "extract", "search": "search", "end": END},
        )
        graph.add_conditional_edges(
            "extract",
            self._route_from_extract,
            {"validate": "validate", "extract": "extract", "end": END},
        )
        graph.add_conditional_edges(
            "validate",
            self._route_from_validate,
            {"search": "search", "end": END},
        )

        return graph

    async def _search_node(self, state: SearchState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="search"))
        query = state.get("query", "")
        messages = state.get("messages", [])

        search_prompt = (
            f"Search query: {query}\n\n"
            "Provide a list of relevant academic sources. For each source, include:\n"
            "- Title\n- Authors\n- Year\n- Source (journal/conference/publisher)\n"
            "- DOI if available\n- Brief relevance explanation"
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=search_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        return {"messages": new_messages, "phase": "extract"}

    async def _extract_node(self, state: SearchState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="extract"))
        messages = state.get("messages", [])

        extract_prompt = (
            "Extract structured citation metadata from the search results above.\n"
            "For each citation, provide:\n"
            "- Citation key (author-year format, e.g., smith2023)\n"
            "- Entry type (article, book, inproceedings, etc.)\n"
            "- All bibliographic fields"
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=extract_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        return {"messages": new_messages, "phase": "validate"}

    async def _validate_node(self, state: SearchState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="validate"))
        messages = state.get("messages", [])

        validate_prompt = (
            "Review the extracted citations and generate valid BibTeX entries.\n"
            "Ensure:\n"
            "- All required fields are present\n"
            "- Author names are properly formatted (Last, First and ...)\n"
            "- Special characters are escaped\n"
            "- Keys are unique\n\n"
            "Output the final BibTeX entries."
        )

        all_messages = [
            system,
            *messages,
            Message(role="user", content=validate_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]

        bib_entries = state.get("bib_entries", [])
        new_bib_entries = [*bib_entries, response.content]

        return {"messages": new_messages, "bib_entries": new_bib_entries, "phase": "end"}

    def _route_from_search(self, state: SearchState) -> str:
        if state.get("phase") == "end":
            return "end"
        return "extract"

    def _route_from_extract(self, state: SearchState) -> str:
        if state.get("phase") == "end":
            return "end"
        return "validate"

    def _route_from_validate(self, _state: SearchState) -> str:
        return "end"

    async def search(self, query: str, state: SearchState | None = None) -> SearchState:
        if state is None:
            state = _default_state()

        state["query"] = query
        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=query)]
        state["messages"] = messages

        compiled = self.graph.compile()
        result = await compiled.ainvoke(cast("Any", state))
        return dict(result)  # type: ignore[return-value]

    async def stream_search(
        self,
        query: str,
        state: SearchState | None = None,
    ) -> AsyncIterator[str]:
        if state is None:
            state = _default_state()

        state["query"] = query
        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=query)]

        phase = state.get("phase", "search")
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase=phase))

        search_prompt = (
            f"Search query: {query}\n\n"
            "Find and cite relevant academic sources for this research topic."
        )
        all_messages = [system, *messages, Message(role="user", content=search_prompt)]

        async for chunk in self.client.stream(all_messages):
            yield chunk.content

    def format_bibtex(self, citation: Citation) -> str:
        authors = " and ".join(citation["authors"])
        optional_parts = []

        if citation.get("doi"):
            optional_parts.append(f"doi = {{{citation['doi']}}}")
        if citation.get("url"):
            optional_parts.append(f"url = {{{citation['url']}}}")
        if abstract := citation.get("abstract"):
            optional_parts.append(f"abstract = {{{abstract[:500]}}}")

        optional_fields = ",\n  ".join(optional_parts) if optional_parts else ""

        return BIBTEX_TEMPLATE.format(
            entry_type=citation["type"],
            key=citation["key"],
            authors=authors,
            title=citation["title"],
            year=citation["year"],
            optional_fields=optional_fields,
        )
