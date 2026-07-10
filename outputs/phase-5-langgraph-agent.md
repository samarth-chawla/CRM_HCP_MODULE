# Phase 5 — LangGraph Agent

Status: Complete

The LangGraph agent orchestrates the AI workflow: understand intent, select the
correct tool, run it, and assemble the structured response. It is invoked by the
FastAPI `/api/interaction/agent` endpoint.

## 1. Agent state (`AgentState`)

```python
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
    _db: Session          # runtime-only (not part of the public contract)
    _llm: GroqClient
```

## 2. Graph topology

```text
START
  -> router                 (classify intent, pick tool)
  -> END
```

- `router` returns the selected `ToolName`; `add_conditional_edges` routes to
  that node.
- Every tool node connects to `response_builder`.
- `response_builder` -> `END`.

## 3. Router / intent classification

`classify_intent(message, current)` maps keywords to intents:

| Intent | Triggers | Tool |
| ------ | -------- | ---- |
| lookup | "lookup", "profile", "who is" | `hcp_profile_lookup` |
| material | "recommend", "suggest material" | `material_recommendation` |
| followup | "follow up", "next step" | `follow_up_suggestion` |
| edit | "change/update/edit/add" **and** existing state | `edit_interaction` |
| log | (default) | `log_interaction` |

Edit is only chosen when prior state already exists; otherwise an "edit-style"
prompt is treated as a fresh log.

## 4. Tool nodes & merge logic

Each tool node delegates to `app/agent/tools.py` and returns a dict
(`updatedInteractionState`, `assistantMessage`, `suggestedFollowUps`,
state. Errors are caught in `_run()` so a single tool failure never crashes the
graph — it records the error and returns the unchanged state.

For a **log** intent, `response_builder` additionally runs `follow_up_suggestion`
the requirements). `toolCalls` accumulates all tools invoked.

## 5. Response builder

Produces the final payload consumed by FastAPI:
`updatedInteractionState`, `assistantMessage`, `suggestedFollowUps`,
frontend's edit-vs-log decision.

## 6. Public entry point

```python
run_agent(message, current: InteractionState, db=None) -> AgentResponse
```

Builds the initial `AgentState`, calls `graph.invoke(init)`, and adapts the
result into an `AgentResponse`.

## 7. Acceptance check (AI orchestration)

- [x] Agent state defined per spec.
- [x] Intent router selects the correct tool.
- [x] Tool nodes run through LangGraph.
- [x] Merge logic preserves/updates fields correctly.
- [x] Response builder returns structured JSON.
- [x] Graph compiled and exercised end-to-end (see Phase 10).

## 8. Next phase

Phase 6 implements the six tools the graph routes between.
