# Phase 4 — FastAPI Backend

Status: Complete

The backend exposes the API the React/Redux client calls. It validates requests
with Pydantic, invokes the LangGraph agent, and persists data via SQLAlchemy.
CORS is enabled for the Vite dev origin (`http://localhost:5173`).

## 1. App (`backend/app/main.py`)

- `CORSMiddleware` allows the frontend origin + localhost:5173.
- On startup, `init_db()` creates tables and seeds reference data.
- `GET /health` reports the active model and whether Groq is configured.

## 2. Endpoints

| Method | Path | Request | Response |
| ------ | ---- | ------- | -------- |
| POST | `/api/interaction/agent` | `AgentRequest {message, currentInteractionState}` | `AgentResponse` |
| POST | `/api/interaction/save` | `SaveRequest {interaction}` | `SaveResponse {interactionId, status}` |
| GET | `/api/interaction/{id}` | – | `InteractionState` |
| PATCH | `/api/interaction/{id}` | `dict` patch | `InteractionState` |
| GET | `/api/hcps/search?q=` | – | `HcpSearchResponse {results[]}` |

### POST /api/interaction/agent

1. Validates `message` is non-empty (422 otherwise).
2. Calls `agent_graph.run_agent(message, currentInteractionState, db)`.
3. Writes an **audit log** of the AI change (prompt, tool, prev/new state, model).
4. Returns `assistantMessage`, `updatedInteractionState`, `toolCalls`,

### POST /api/interaction/save

- Enforces required fields (`hcpName`, `interactionType`, `date`,
  `topicsDiscussed`) → 422 if missing.
- Persists the interaction + attendees/materials/samples/follow-ups.
- Writes an audit log with `tool_called = interaction.save`.
- Returns a generated `interactionId` (e.g. `INT-XXXXXXXX`).

## 3. Schemas (`backend/app/schemas.py`)

- `InteractionState` — mirrors the Redux `interactionSlice` exactly, so the JSON
- `AgentRequest` / `AgentResponse`, `SaveRequest` / `SaveResponse`,
  `HCPProfile` / `HcpSearchResponse`.

## 4. Config (`backend/app/config.py`)

`pydantic-settings` loads `GROQ_API_KEY`, `GROQ_MODEL` (`gemma2-9b-it`),
`DATABASE_URL`, `APP_ENV`, `FRONTEND_ORIGIN` from env / `.env`. Exposes
`has_groq` and `is_sqlite` helpers so the app degrades gracefully without a key.

## 5. Runner

`backend/run.py` launches Uvicorn on port 8000. Also runnable with
`uvicorn app.main:app --reload`.

## 6. Acceptance check (Backend)

- [x] FastAPI app runs; `/health` responds.
- [x] `/api/interaction/agent` accepts chat prompts and returns structured JSON.
- [x] Save endpoint persists interaction data + audit logs.
- [x] Invalid input returns useful 422 errors.
- [x] Pydantic request validation on every endpoint.

## 7. Next phase

Phase 5 builds the LangGraph agent that `/api/interaction/agent` delegates to.
