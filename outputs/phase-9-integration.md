# Phase 9 — Integration

Status: Complete

This phase connects all the layers into one working system: React → Redux →
FastAPI → LangGraph → Groq → PostgreSQL/SQLite, with audit logging on every
AI-driven change.

## 1. Wiring map

```text
React (chat input)
  -> dispatch(sendAgentMessage)            [src/features/interaction/interactionThunks.js]
  -> axios POST /api/interaction/agent     [src/api/client.js]
  -> FastAPI /api/interaction/agent        [backend/app/main.py]
  -> agent_graph.run_agent(...)            [backend/app/agent/graph.py]
  -> router -> tool node -> response_builder
  -> Groq (gemma2-9b-it)                   [backend/app/llm/groq_client.py]
  -> structured JSON
  -> AgentResponse -> Redux update
  -> read-only form auto-populates        [InteractionForm.jsx]
```

Save flow: `Save interaction` → `persistInteraction()` → `POST /api/interaction/save`
→ `crud.save_interaction()` + `write_audit()`.

## 2. Frontend ↔ backend contract

- `src/api/client.js` sets `baseURL` from `VITE_API_BASE` (default
  `http://localhost:8000`). All calls are JSON.
- `AgentResponse` matches the Redux `interactionSlice` shape 1:1 (verified by the
  shared `InteractionState` schema), so the thunk can dispatch
  `updateInteractionState` (log) or `mergeInteractionPatch` (edit) directly.
- CORS in `main.py` allows `http://localhost:5173`.

## 3. The "AI controls the form" guarantee

The Redux slice exposes **no** action that accepts raw field typing. The only
mutation paths are `updateInteractionState` / `mergeInteractionPatch`, which are
dispatched exclusively from `sendAgentMessage` after the backend returns. The
form inputs are `disabled` + `readOnly`. The chat textarea is the single editable
surface.

## 4. Edit vs log

The thunk inspects `res.intent` / `res.selectedTool` from the backend:
- `edit` / `edit_interaction` → `mergeInteractionPatch` (preserves untouched fields).
- otherwise → `updateInteractionState` (full replace).

## 5. How to run

```text
# Terminal 1 — backend
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY (optional; fallback works without it)
python run.py               # http://localhost:8000

# Terminal 2 — frontend
npm install
npm run dev                 # http://localhost:5173
```

Open the frontend, type an interaction in the chat, and watch the left form
populate. Click **Save interaction** to persist + audit.

## 6. Acceptance check (Integration)

- [x] React → Redux → FastAPI → LangGraph → Groq → JSON → Redux → form.
- [x] Single editable surface (chat); form is read-only.
- [x] Save persists to DB + writes audit log.
- [x] CORS + shared JSON schema keep frontend/backend in sync.

## 7. Next phase
