# Phase 1 — Requirements

Status: Complete

This phase consolidates the project definition that drives every later phase. The
authoritative source is [`complete-project-requirements.md`](./complete-project-requirements.md);
this document is the working summary the build follows.

---

## 1. Objective

Build an **AI-first CRM HCP module** for life-sciences field representatives. The
signature screen is **Log HCP Interaction**, where a rep describes a meeting in
natural language and an AI assistant extracts structured CRM data and populates a
**read-only** interaction form.

The system must *prove* the form is controlled by AI — not by manual typing.

## 2. Primary User

Life-sciences field representative who needs to log HCP meetings quickly, capture
discussion detail, materials, samples, sentiment, outcomes and follow-ups, and

## 3. Core Functional Requirement

A split-screen **Log HCP Interaction** screen:

| Side  | Content                              | Editable?                     |
| ----- | ------------------------------------ | ----------------------------- |
| Left  | Interaction Details form             | **No** — read-only, AI-driven |
| Right | AI assistant chat                    | Yes — the only input surface  |

## 4. Critical Assessment Rule (non-negotiable)

The left form is never manually editable. Every value flows through:

```text
User prompt in AI chat
 -> React frontend
 -> Redux action
 -> FastAPI backend
 -> LangGraph agent
 -> LangGraph tool
 -> Groq LLM
 -> Structured JSON response
 -> Redux state update
 -> Read-only form auto-populates
```

Hard-coding the interaction logic without these technologies is not acceptable.

## 5. Tech Stack

**Frontend:** React, Redux Toolkit, Vite, JavaScript, Google Inter font, CSS Modules.

**Backend:** Python, FastAPI, Pydantic, Uvicorn.

**AI:** LangGraph agent + tools.

**LLM:** Groq — primary model `gemma2-9b-it`, optional `llama-3.3-70b-versatile`.

**Database:** PostgreSQL (recommended).

**Environment variables:**

```text
GROQ_API_KEY=
DATABASE_URL=
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
```

## 6. Form Fields (left panel)

HCP Name · Interaction Type · Date · Time · Attendees · Topics Discussed ·
Materials Shared · Samples Distributed · Observed/Inferred HCP Sentiment ·

All fields: `readOnly`, `disabled`, Redux-controlled, AI-updated.

## 7. Required LangGraph Tools (min 5, we build 6)

1. **Log Interaction** (mandatory) — parse NL into a structured record.
2. **Edit Interaction** (mandatory) — patch only requested fields, preserve the rest.
3. **HCP Profile Lookup** — enrich HCP details from the CRM.
4. **Material Recommendation** — suggest approved materials by topic.
5. **Follow-Up Suggestion** — recommend next best actions.

## 8. Backend Endpoints

```text
POST  /api/interaction/agent      # run prompt through LangGraph, return updated state
POST  /api/interaction/save       # persist finalized interaction + audit log
GET   /api/interaction/{id}       # fetch a saved interaction
PATCH /api/interaction/{id}       # update a saved interaction
GET   /api/hcps/search            # search HCP profiles
```

## 9. Redux Shape

Slices: `interactionSlice`, `chatSlice`.

Actions: `updateInteractionState`, `mergeInteractionPatch`, `resetInteraction`,
`addAssistantMessage`, `setChatLoading`, `setChatError`.

## 10. Acceptance Criteria (summary)

- **UI:** split-screen, read-only form, chat-only input, Redux-sourced values,
  auto-populate on AI response, Save works, loading/error visible, Inter font,
  professional CRM feel.
- **Backend:** FastAPI runs, `/agent` invokes LangGraph, Groq called via
  `GROQ_API_KEY`, structured JSON out, save persists, audit logs created.
- **AI:** ≥5 tools, Log from NL, Edit patches only requested fields, lookup /
  before Redux update.

## 11. Build Plan (phase → deliverable doc)

| Phase | Deliverable                          | Doc                              |
| ----- | ------------------------------------ | -------------------------------- |
| 1     | Requirements                         | `phase-1-requirements.md`        |
| 2     | Frontend UI (layout, form, chat)     | `phase-2-frontend-ui.md`         |
| 3     | Redux state (store, slices)          | `phase-3-redux-state.md`         |
| 4     | FastAPI backend (endpoints, schemas) | `phase-4-fastapi-backend.md`     |
| 5     | LangGraph agent (graph, nodes)       | `phase-5-langgraph-agent.md`     |
| 6     | AI tools (six tools)                 | `phase-6-ai-tools.md`            |
| 7     | Groq integration (client, prompts)   | `phase-7-groq-integration.md`    |
| 8     | Database (schema, ORM, audit)        | `phase-8-database.md`            |
| 9     | Integration (wire it all together)   | `phase-9-integration.md`         |
| 10    | Testing (flows, routing, errors)     | `phase-10-testing.md`            |

## 12. Repository Layout (target)

```text
task-ai-first-crm-hcp-module/
├── index.html                # Vite entry
├── package.json              # frontend deps
├── src/                      # React + Redux frontend
│   ├── main.jsx
│   ├── App.jsx
│   ├── app/store.js
│   ├── features/interaction/
│   ├── features/chat/
│   ├── components/
│   └── api/
├── backend/                  # FastAPI + LangGraph + Groq
│   ├── app/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── config.py
│   │   ├── db/
│   │   ├── agent/
│   │   └── llm/
│   ├── requirements.txt
│   └── .env.example
└── outputs/                  # phase docs (this folder)
```
