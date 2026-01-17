from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from theoria.providers import LLMClient, Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from theoria.config import Config


class DialogueState(TypedDict, total=False):
    messages: list[Message]
    phase: Literal["clarify", "challenge", "synthesize", "end"]
    thesis: str
    objections: list[str]
    refinements: list[str]


def _default_state() -> DialogueState:
    return {
        "messages": [],
        "phase": "clarify",
        "thesis": "",
        "objections": [],
        "refinements": [],
    }


SYSTEM_PROMPT = """You are Theoretikos, a Socratic philosophical dialogue partner.

Your role:
- Help the user clarify, examine, and refine their arguments
- Ask probing questions to uncover assumptions
- Present counter-arguments and objections
- Never simply agree - always push for deeper thinking
- Guide toward well-supported conclusions with traceable reasoning

Current phase: {phase}
- clarify: Help user articulate their thesis clearly
- challenge: Present objections and counter-arguments
- synthesize: Help integrate insights into refined position

Respond in the user's language. Be rigorous but not hostile."""


class Theoretikos:
    def __init__(self, config: Config | None = None) -> None:
        self.client = LLMClient(config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph[DialogueState]:
        graph: StateGraph[DialogueState] = StateGraph(DialogueState)

        graph.add_node("clarify", self._clarify_node)
        graph.add_node("challenge", self._challenge_node)
        graph.add_node("synthesize", self._synthesize_node)

        graph.set_entry_point("clarify")

        graph.add_conditional_edges(
            "clarify",
            self._route_from_clarify,
            {"challenge": "challenge", "clarify": "clarify", "end": END},
        )
        graph.add_conditional_edges(
            "challenge",
            self._route_from_challenge,
            {"synthesize": "synthesize", "challenge": "challenge", "end": END},
        )
        graph.add_conditional_edges(
            "synthesize",
            self._route_from_synthesize,
            {"clarify": "clarify", "end": END},
        )

        return graph

    async def _clarify_node(self, state: DialogueState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="clarify"))
        messages = state.get("messages", [])
        all_messages = [system, *messages]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]
        return {"messages": new_messages}

    async def _challenge_node(self, state: DialogueState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="challenge"))
        thesis = state.get("thesis", "")
        messages = state.get("messages", [])
        objections = state.get("objections", [])

        challenge_prompt = (
            f"The user's thesis: {thesis}\n\nPresent a thoughtful objection or counter-argument."
        )
        all_messages = [
            system,
            *messages,
            Message(role="user", content=challenge_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]
        new_objections = [*objections, response.content]
        return {"messages": new_messages, "objections": new_objections}

    async def _synthesize_node(self, state: DialogueState) -> dict[str, Any]:
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase="synthesize"))
        thesis = state.get("thesis", "")
        messages = state.get("messages", [])
        objections = state.get("objections", [])
        refinements = state.get("refinements", [])

        synthesis_prompt = (
            f"Original thesis: {thesis}\n"
            f"Objections raised: {len(objections)}\n\n"
            "Help the user synthesize insights into a refined position."
        )
        all_messages = [
            system,
            *messages,
            Message(role="user", content=synthesis_prompt),
        ]

        response = await self.client.complete(all_messages)
        new_messages = [*messages, Message(role="assistant", content=response.content)]
        new_refinements = [*refinements, response.content]
        return {"messages": new_messages, "refinements": new_refinements}

    def _route_from_clarify(self, state: DialogueState) -> str:
        if state.get("phase") == "end":
            return "end"
        if state.get("thesis"):
            return "challenge"
        return "clarify"

    def _route_from_challenge(self, state: DialogueState) -> str:
        if state.get("phase") == "end":
            return "end"
        objections = state.get("objections", [])
        if len(objections) >= 3:
            return "synthesize"
        return "challenge"

    def _route_from_synthesize(self, state: DialogueState) -> str:
        if state.get("phase") == "end":
            return "end"
        return "clarify"

    async def chat(self, user_input: str, state: DialogueState | None = None) -> DialogueState:
        if state is None:
            state = _default_state()

        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]
        state["messages"] = messages

        if not state.get("thesis") and "thesis:" in user_input.lower():
            thesis_start = user_input.lower().index("thesis:")
            state["thesis"] = user_input[thesis_start + 7 :].strip()

        compiled = self.graph.compile()
        result = await compiled.ainvoke(cast("Any", state))
        return dict(result)  # type: ignore[return-value]

    async def stream_chat(
        self,
        user_input: str,
        state: DialogueState | None = None,
    ) -> AsyncIterator[str]:
        if state is None:
            state = _default_state()

        messages = state.get("messages", [])
        messages = [*messages, Message(role="user", content=user_input)]

        phase = state.get("phase", "clarify")
        system = Message(role="system", content=SYSTEM_PROMPT.format(phase=phase))
        all_messages = [system, *messages]

        async for chunk in self.client.stream(all_messages):
            yield chunk.content
