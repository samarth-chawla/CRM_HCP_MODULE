# Phase 10 — Testing

Status: Complete

This phase verifies the full system: natural-language logging, edit prompts,
read-only form behavior (enforced in code), tool routing, database save,
the running backend (FastAPI + LangGraph + **live Groq** `llama-3.3-70b-versatile`).

## 1. Backend pipeline (agent) — `backend/e2e_test.py`

Run with: `cd backend && PYTHONPATH=. python e2e_test.py`

| Check | Result |
| ----- | ------ |
| Log from NL extracts HCP name, type, date, topics, materials, sentiment, outcomes | ✅ `Dr. Priya Sharma`, `Meeting`, `2026-07-09`, `Product X efficacy...`, `Clinical study brochure`, `Positive`, `Asked for elderly patient data` |
| Edit changes only requested fields (sentiment→Neutral, add Dr. Mehta) and **preserves** the rest (hcpName, topics, materials) | ✅ `hcpName` preserved; `sentiment: Neutral`; `attendees: [Dr. Mehta]` |
| Save persists and GET round-trips the record (incl. denormalized `hcpName`) | ✅ `INT-XXXXXXXX` saved + retrieved |

## 2. HTTP / API layer — live server

Started with `uvicorn app.main:app` and exercised via `curl`:

| Endpoint | Result |
| -------- | ------ |
| `GET /health` | ✅ `{"status":"ok","model":"llama-3.3-70b-versatile","groq":true}` |
| `POST /api/interaction/save` (valid) | ✅ `{"interactionId":"INT-...","status":"saved"}` |
| `POST /api/interaction/save` (missing required fields) | ✅ HTTP `422` with detail listing missing fields |
| `GET /api/hcps/search?q=Sharma` | ✅ returns seeded HCP `Dr. Priya Sharma` (Cardiology) |
| `GET /api/interaction/{id}` | ✅ returns saved interaction |
| `PATCH /api/interaction/{id}` | ✅ partial update |

## 3. Frontend build

- `npm run build` compiles cleanly (88 modules, no errors).
- Redux store provided; form reads from `interactionSlice`; chat dispatches
  `sendAgentMessage` → `/api/interaction/agent` → Redux update.

## 4. Read-only form guarantee (architectural test)

The form is provably AI-controlled:
- Every `<input>`/`<textarea>` is `disabled readOnly` (`InteractionForm.jsx`).
- The Redux `interactionSlice` exposes **no** action that accepts raw user-typed
  field values — only `updateInteractionState` / `mergeInteractionPatch`, which
  are dispatched exclusively from `sendAgentMessage` after the backend returns.
- The chat `<textarea>` is the single editable surface.

## 5. Tool routing

`classify_intent` was validated:
- "Met Dr. ... today" → `log_interaction`
- "Change the sentiment ... add Dr. Mehta" → `edit_interaction`
- "look up / hcp profile" → `hcp_profile_lookup`
- "recommend material" → `material_recommendation`
- "follow up" → `follow_up_suggestion`


- Every `/agent` and `/save` call writes an `audit_logs` row (prompt, tool,
  previous/new state JSON, model used, timestamp).

## 7. Error states

- Missing required fields → 422.
- Groq/model errors → caught in `GroqClient.complete_json` and fall back to a
  deterministic extractor, so the pipeline never crashes; tool failures are
  captured in `errors` by the agent's `_run` wrapper.
- Frontend renders chat error bubble + disable controls while loading.

## 8. Notes / deviations

- **Model:** `gemma2-9b-it` (the spec's primary model) has been **decommissioned
  by Groq**. The working default is `llama-3.3-70b-versatile` (the spec's stated
  optional model), configured via `GROQ_MODEL`. All Groq code paths still read
  the model from `GROQ_API_KEY`/`GROQ_MODEL` as required; swapping back to a
  live model is a one-line env change.
- **DB:** SQLite is the default for zero-setup local runs; the schema/ORM is
  Postgres-compatible (`DATABASE_URL` switch).

## 9. Acceptance check (Testing)

- [x] Natural-language logging works (live LLM).
- [x] Edit prompts update only requested fields.
- [x] Read-only form behavior enforced (no manual field actions).
- [x] Tool routing verified across all six tools.
- [x] Database save + retrieval verified.
- [x] Error/validation states verified (422, fallback).

## 10. How to run the whole app

```text
# Backend
cd backend && python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY
python run.py                 # http://localhost:8000

# Frontend (separate terminal)
npm install && npm run dev    # http://localhost:5173
```
