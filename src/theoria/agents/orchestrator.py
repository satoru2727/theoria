from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from theoria.agents.bibliographos import Bibliographos, SearchState
from theoria.agents.theoretikos import DialogueState, Theoretikos
from theoria.providers import LLMClient, Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from theoria.config import Config


class OrchestratorState(TypedDict, total=False):
    messages: list[Message]
    active_agent: Literal["theoretikos", "bibliographos", "orchestrator"]
    dialogue_state: DialogueState
    search_state: SearchState
    pending_search: str | None
    search_results: list[str]


def _default_state() -> OrchestratorState:
    return {
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


HANDOFF_PATTERNS = [
    r"この主張の根拠を(探して|調べて|検索して)",
    r"(文献|論文|ソース|出典)を(探して|調べて|検索して)",
    r"(evidence|sources?|citations?|references?)\s+(for|about|on)",
    r"find\s+(papers?|sources?|evidence|literature)",
    r"search\s+(for\s+)?(literature|papers?|sources?)",
]

ORCHESTRATOR_SYSTEM = """You are an orchestrator that decides when to hand off between agents.

You coordinate between:
- Theoretikos: Socratic philosophical dialogue and argument examination
- Bibliographos: Academic literature search and citation management

Analyze the user's message and determine:
1. Request for evidence/sources/citations → "HANDOFF:bibliographos:<search query>"
2. Philosophical discussion or argument → "CONTINUE:theoretikos"
3. Search results available, discussion should resume → "CONTINUE:theoretikos"

Be brief. Only output the decision format."""


class Orchestrator:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config
        self.client = LLMClient(config)
        self.theoretikos = Theoretikos(config)
        self.bibliographos = Bibliographos(config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph[OrchestratorState]:
        graph: StateGraph[OrchestratorState] = StateGraph(OrchestratorState)

        graph.add_node("route", self._route_node)
        graph.add_node("theoretikos", self._theoretikos_node)
        graph.add_node("bibliographos", self._bibliographos_node)
        graph.add_node("integrate", self._integrate_node)

        graph.set_entry_point("route")

        graph.add_conditional_edges(
            "route",
            self._decide_route,
            {
                "theoretikos": "theoretikos",
                "bibliographos": "bibliographos",
                "end": END,
            },
        )
        graph.add_edge("theoretikos", END)
        graph.add_edge("bibliographos", "integrate")
        graph.add_edge("integrate", END)

        return graph

    async def _route_node(self, state: OrchestratorState) -> dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {"active_agent": "theoretikos"}

        last_message = messages[-1]
        if last_message.role != "user":
            return {"active_agent": "theoretikos"}

        content = last_message.content.lower()

        for pattern in HANDOFF_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                search_query = self._extract_search_query(last_message.content)
                return {"active_agent": "bibliographos", "pending_search": search_query}

        return {"active_agent": "theoretikos"}

    def _extract_search_query(self, message: str) -> str:
        for pattern in HANDOFF_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                after_match = message[match.end() :].strip()
                if after_match:
                    return after_match[:200]

        return message[:200]

    async def _theoretikos_node(self, state: OrchestratorState) -> dict[str, Any]:
        messages = state.get("messages", [])
        dialogue_state = state.get("dialogue_state", {})

        if not messages:
            return {}

        last_message = messages[-1]
        if last_message.role != "user":
            return {}

        search_results = state.get("search_results", [])
        user_input = last_message.content

        if search_results:
            context = "\n".join(search_results)
            user_input = f"{user_input}\n\n[Available sources from literature search]:\n{context}"
            state["search_results"] = []

        new_dialogue_state = await self.theoretikos.chat(user_input, dialogue_state or None)

        new_messages = new_dialogue_state.get("messages", [])
        if new_messages:
            assistant_msg = new_messages[-1]
            return {
                "messages": [*messages, assistant_msg],
                "dialogue_state": new_dialogue_state,
            }

        return {"dialogue_state": new_dialogue_state}

    async def _bibliographos_node(self, state: OrchestratorState) -> dict[str, Any]:
        pending_search = state.get("pending_search")
        if not pending_search:
            return {}

        search_state = state.get("search_state", {})
        new_search_state = await self.bibliographos.search(pending_search, search_state or None)

        bib_entries = new_search_state.get("bib_entries", [])

        return {
            "search_state": new_search_state,
            "search_results": bib_entries,
            "pending_search": None,
        }

    async def _integrate_node(self, state: OrchestratorState) -> dict[str, Any]:
        messages = state.get("messages", [])
        search_results = state.get("search_results", [])

        if not search_results:
            return {}

        summary = (
            f"[Bibliographos found {len(search_results)} relevant source(s). "
            "The sources have been integrated into the discussion context.]"
        )

        return {"messages": [*messages, Message(role="assistant", content=summary)]}

    def _decide_route(self, state: OrchestratorState) -> str:
        active = state.get("active_agent", "theoretikos")
        if active == "bibliographos":
            return "bibliographos"
        if active == "theoretikos":
            return "theoretikos"
        return "end"

    async def chat(
        self, user_input: str, state: OrchestratorState | None = None
    ) -> OrchestratorState:
        if state is None:
            state = _default_state()

        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]
        state["messages"] = messages

        compiled = self.graph.compile()
        result = await compiled.ainvoke(cast("Any", state))
        return dict(result)  # type: ignore[return-value]

    async def stream_chat(
        self,
        user_input: str,
        state: OrchestratorState | None = None,
    ) -> AsyncIterator[str]:
        if state is None:
            state = _default_state()

        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]

        content_lower = user_input.lower()
        is_search_request = any(
            re.search(pattern, content_lower, re.IGNORECASE) for pattern in HANDOFF_PATTERNS
        )

        if is_search_request:
            search_query = self._extract_search_query(user_input)
            yield f"[Searching for: {search_query}]\n\n"

            search_state = state.get("search_state", {})
            async for chunk in self.bibliographos.stream_search(search_query, search_state or None):
                yield chunk
        else:
            dialogue_state = state.get("dialogue_state", {})

            search_results = state.get("search_results", [])
            if search_results:
                context = "\n".join(search_results)
                user_input = f"{user_input}\n\n[Available sources]:\n{context}"

            async for chunk in self.theoretikos.stream_chat(user_input, dialogue_state or None):
                yield chunk
