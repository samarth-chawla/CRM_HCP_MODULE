"""LangGraph agent for the HCP interaction pipeline.

Graph:
    START -> router -> (selected tool node) -> response_builder -> END

State is the shared working memory passed between nodes. The router decides
which tool(s) to run; tool nodes mutate `updatedInteractionState`; the response
builder assembles the final payload for the FastAPI endpoint.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.agent import tools as t
from app.llm.groq_client import groq_client
from app.schemas import AgentResponse, InteractionState

ToolName = Literal[
    "log_interaction",
    "edit_interaction",
    "hcp_profile_lookup",
    "material_recommendation",
    "follow_up_suggestion",
    "summarize_interactions",
    "schedule_followup",
    "generate_insights",
]


class AgentState(TypedDict, total=False):
    message: str
    currentInteractionState: InteractionState
    intent: str
    selectedTool: str
    toolResults: dict
    updatedInteractionState: InteractionState
    assistantMessage: str
    suggestedFollowUps: list[str]
    toolCalls: list[str]
    errors: list[str]
    _db: Any  # runtime-only: DB session (not part of the public contract)
    _llm: Any  # runtime-only: Groq client


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def classify_intent(message: str, current: InteractionState) -> tuple[str, ToolName]:
    m = message.lower()
    has_state = bool(current.hcpName or current.topicsDiscussed)

    # Does this message DESCRIBE an interaction? If so it should be logged, even
    # if it also mentions a follow-up. Logging then enriches with suggestions.
    describes_interaction = bool(
        t._extract_name(message)
        or any(k in m for k in ("visited", "met ", "called", "emailed", "field visit"))
    )

    # 1) Scheduling an ACTION (create a follow-up). Must be checked BEFORE the
    #    follow-up-suggestion branch so "schedule a follow-up" is not treated as
    #    a mere suggestion request.
    if any(k in m for k in ("schedule", "book a", "book the", "set up", "arrange", "plan a follow", "schedule a follow")):
        return "schedule", "schedule_followup"

    # 2) Explicit HCP *profile* lookups only.
    if any(k in m for k in ("look up", "lookup", "hcp profile", "find the hcp", "tell me about the hcp", "profile of")):
        return "lookup", "hcp_profile_lookup"

    # 3) Insights / analysis over interactions. Checked BEFORE the plain
    #    summarize branch, because insight requests also mention "summary".
    if any(k in m for k in (
        "insight", "insights", "analyze", "analysis", "overall sentiment",
        "key concerns", "generate a report", "interaction insights",
    )):
        return "insights", "generate_insights"

    # 4) Reading / summarizing interactions (NOT a profile lookup).
    if any(k in m for k in (
        "summarize", "summary", "summarise", "recap", "review",
        "my interactions", "recent interactions", "list interactions",
        "show interactions", "all interactions", "show all", "list all",
        "show me", "list of",
    )):
        return "read", "summarize_interactions"

    # 4) Material recommendations.
    if any(k in m for k in ("recommend", "suggest material", "what material", "which material")):
        return "material", "material_recommendation"

    # 5) Edits (only when there is state to edit).
    if any(k in m for k in ("change", "update", "edit", "modify", "set the", "make it", "add ")) and has_state:
        return "edit", "edit_interaction"

    # 6) Pure follow-up *suggestion* questions (not scheduling).
    if (
        any(k in m for k in ("follow-up", "follow up", "next step", "should i", "what next", "suggest follow"))
        and not describes_interaction
    ):
        return "followup", "follow_up_suggestion"

    # 7) Default: anything describing an interaction is a new log.
    return "log", "log_interaction"


def router(state: AgentState) -> Command:
    # Decide which tool runs and branch to it via a Command (explicit routing).
    # The router returns no state mutation other than recording the decision.
    intent, tool = classify_intent(state["message"], state["currentInteractionState"])
    state["intent"] = intent
    state["selectedTool"] = tool
    return Command(update={"intent": intent, "selectedTool": tool}, goto=tool)


# ---------------------------------------------------------------------------
# Tool nodes — each delegates to the tools module
# ---------------------------------------------------------------------------

def _run(name: ToolName, state: AgentState) -> dict:
    db = state.get("_db")
    llm = state.get("_llm", groq_client)
    try:
        return _dispatch(name, state, db, llm)
    except Exception as exc:  # keep the graph alive on tool failure
        current = state["currentInteractionState"]
        return {
            "updatedInteractionState": current,
            "assistantMessage": f"Tool {name} failed: {exc}",
            "suggestedFollowUps": current.suggestedFollowUps,
            "toolCalls": [name],
            "errors": [str(exc)],
        }


def _dispatch(name: ToolName, state: AgentState, db, llm) -> dict:
    msg = state["message"]
    cur = state["currentInteractionState"]
    if name == "log_interaction":
        return t.log_interaction(msg, cur, db, llm)
    if name == "edit_interaction":
        return t.edit_interaction(msg, cur, db, llm)
    if name == "hcp_profile_lookup":
        return t.hcp_profile_lookup(msg, cur, db, llm)
    if name == "summarize_interactions":
        return t.summarize_interactions(msg, cur, db, llm)
    if name == "schedule_followup":
        return t.schedule_followup(msg, cur, db, llm)
    if name == "generate_insights":
        return t.generate_insights(msg, cur, db, llm)
    if name == "material_recommendation":
        return t.material_recommendation(msg, cur, db, llm)
    if name == "follow_up_suggestion":
        return t.follow_up_suggestion(msg, cur, db, llm)
    raise ValueError(f"Unknown tool {name}")


# One node function per tool keeps the graph topology explicit.
def node_log(state): return _run("log_interaction", state)
def node_edit(state): return _run("edit_interaction", state)
def node_lookup(state): return _run("hcp_profile_lookup", state)
def node_summarize(state): return _run("summarize_interactions", state)
def node_schedule(state): return _run("schedule_followup", state)
def node_insights(state): return _run("generate_insights", state)
def node_material(state): return _run("material_recommendation", state)
def node_followup(state): return _run("follow_up_suggestion", state)


_NODES: dict[ToolName, Any] = {
    "log_interaction": node_log,
    "edit_interaction": node_edit,
    "hcp_profile_lookup": node_lookup,
    "summarize_interactions": node_summarize,
    "schedule_followup": node_schedule,
    "generate_insights": node_insights,
    "material_recommendation": node_material,
    "follow_up_suggestion": node_followup,
}


# ---------------------------------------------------------------------------
# Response builder (enriches a log with follow-up suggestions)
# ---------------------------------------------------------------------------

def response_builder(state: AgentState) -> dict:
    tool_calls: list[str] = list(state.get("toolCalls", []))
    updated = state.get("updatedInteractionState") or state["currentInteractionState"]
    sugg = state.get("suggestedFollowUps", updated.suggestedFollowUps)

    db = state.get("_db")
    llm = state.get("_llm", groq_client)

    # For a log intent, enrich with follow-up suggestions.
    if state.get("intent") == "log" and "log_interaction" in tool_calls:
        fu = t.follow_up_suggestion(state["message"], updated, db, llm)
        updated = fu["updatedInteractionState"]
        sugg = fu.get("suggestedFollowUps", sugg)
        tool_calls = tool_calls + ["follow_up_suggestion"]

    return {
        "updatedInteractionState": updated,
        "assistantMessage": state.get("assistantMessage", "Done."),
        "suggestedFollowUps": sugg,
        "toolCalls": tool_calls,
        "errors": state.get("errors", []),
    }


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("router", router)
    for name, fn in _NODES.items():
        g.add_node(name, fn)
    g.add_node("response_builder", response_builder)

    g.set_entry_point("router")
    for name in _NODES:
        g.add_edge(name, "response_builder")
    g.add_edge("response_builder", END)
    return g.compile()


graph = build_graph()


# ---------------------------------------------------------------------------
# Public entry point used by the FastAPI endpoint
# ---------------------------------------------------------------------------

def run_agent(message: str, current: InteractionState, db=None) -> AgentResponse:
    init: AgentState = {
        "message": message,
        "currentInteractionState": current,
        "intent": "",
        "selectedTool": "",
        "toolResults": {},
        "updatedInteractionState": current,
        "assistantMessage": "",
        "suggestedFollowUps": current.suggestedFollowUps,
        "toolCalls": [],
        "errors": [],
        "_db": db,
        "_llm": groq_client,
    }
    result = graph.invoke(init)

    updated = result.get("updatedInteractionState") or current
    return AgentResponse(
        assistantMessage=result.get("assistantMessage", "Done."),
        updatedInteractionState=updated,
        toolCalls=result.get("toolCalls", []),
        suggestedFollowUps=result.get("suggestedFollowUps", []),
        intent=result.get("intent", ""),
        selectedTool=result.get("selectedTool", ""),
        errors=result.get("errors", []),
    )
