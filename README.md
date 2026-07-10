
# AI-First CRM — HCP Module (Log Interaction Screen)

An **AI-first CRM module for life-sciences field representatives**, focused on
logging Healthcare Professional (HCP) interactions. The signature screen is
**Log HCP Interaction**: a split-screen where a rep describes a meeting in
natural language and an AI assistant extracts structured CRM data and populates
the form — or, if they prefer, they can fill the structured form manually.

> **Mandatory tech is wired in end-to-end:** the conversational path runs
> **React → Redux → FastAPI → LangGraph agent → Groq LLM → structured JSON →
> Redux → read-only form**.

---

## Features

- **Split-screen Log Interaction screen** (left form 65% / right AI chat 35%),
  responsive (stacks on mobile).
- **Two logging modes** (toggle in the form header):
  - **AI-controlled (default):** the form is **read-only** and is populated
    *only* by the AI pipeline. The chat is the only input surface — proving the
    form is controlled by AI, not manual typing.
  - **Manual entry:** the rep types directly into the structured form (the
    "structured form" logging option from the assignment).
- **6 LangGraph tools** for sales activities (spec required ≥ 5, with Log +
  Edit mandatory).
- **Google Inter** font, professional CRM styling.

---

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| Frontend | React 19, Redux Toolkit, Vite, CSS Modules, Google Inter |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| AI Agent | **LangGraph** (state graph + tools) |
| LLM | **Groq** — `llama-3.3-70b-versatile` (see model note) |
| Database | PostgreSQL / MySQL (SQLAlchemy ORM); SQLite fallback for quick local runs |

### Model note (important)
The assignment specifies **`gemma2-9b-it`**. That model has been **decommissioned
by Groq**, so live calls return HTTP 400. The code still reads the model from
`GROQ_MODEL` (and the key from `GROQ_API_KEY`), and defaults to **`llama-3.3-70b-versatile`**
(the assignment's explicitly allowed alternative). To try a different model, set
`GROQ_MODEL` in `backend/.env`.

---

## Project Structure

```text
.
├── index.html, package.json, vite.config.js   # React + Vite frontend
├── src/
│   ├── main.jsx, App.jsx, App.css, index.css   # shell + theme (Inter font)
│   ├── app/store.js                            # Redux store
│   ├── api/client.js                          # axios calls to FastAPI
│   ├── features/interaction/                  # interactionSlice + thunks
│   ├── features/chat/                          # chatSlice
│   └── components/                            # InteractionForm, AssistantChat
└── backend/
    ├── requirements.txt, run.py, .env.example
    └── app/
        ├── main.py          # FastAPI app + CORS + endpoints
        ├── config.py        # env (GROQ_*, DATABASE_URL, ...)
        ├── schemas.py       # Pydantic request/response models
        ├── db/              # SQLAlchemy models, session, CRUD, audit
        ├── llm/             # Groq client + prompt templates
        └── agent/           # LangGraph graph + 6 tools
```

---

## How to Run

### 1. Backend (FastAPI + LangGraph + Groq)

```bash
cd backend
python -m venv .venv
# Windows:
. .venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env          # then edit and add your GROQ_API_KEY
python run.py                 # serves on http://localhost:8000
```

`backend/.env` (gitignored):

```text
GROQ_API_KEY=gsk_xxx
DATABASE_URL="sqlite:///./crm_hcp.db"     # or postgresql+psycopg://user:pass@host:5432/crm_hcp
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
GROQ_MODEL=llama-3.3-70b-versatile
```

> Tables are created automatically on startup. Two demo HCPs and the approved
> materials list are seeded so the lookup / recommendation tools return data
> immediately.

#### Resetting the database

If the schema ever drifts from the models, or you just want a clean slate,
`app/db/reset.py` drops every table, rebuilds them from the ORM models (the
single source of truth), and reseeds the demo data — all in one command.
**This destroys all data**, so only run it against a dev/demo database.

```bash
cd backend
# prompts for confirmation
python -m app.db.reset
# or, non-interactive (scripts/CI):
python -m app.db.reset --yes
```

After resetting, restart the backend so it reconnects to the fresh tables.

### 2. Frontend (React + Redux)

```bash
# from the repo root
npm install
npm run dev                   # http://localhost:5173
```

Open http://localhost:5173, type an interaction in the right-hand chat, and the
left form populates automatically. Use **Save interaction** to persist (and
audit-log the record.

---

## LangGraph Agent & Tools

The agent is a LangGraph `StateGraph`:

```text
START -> router (intent classifier) -> <selected tool node>
       -> response_builder (enrich + assemble) -> END
```

The agent **manages HCP interactions** by understanding the user's intent,
selecting the correct tool, calling Groq where needed, extracting structured
data, preserving unchanged fields on edits, and returning validated JSON.

### The 5 tools

1. **Log Interaction** *(mandatory)* — parses natural language into a structured
   record. Uses the LLM for **entity extraction, sentiment inference, summarization,
   and structured-JSON generation**; missing values are left empty (never invented).
2. **Edit Interaction** *(mandatory)* — modifies logged data. Returns a **patch of
   only the requested fields**; all unchanged fields are preserved.
3. **HCP Profile Lookup** — enriches the record from the CRM (specialty, territory,
   preferred channel, prior interest).
4. **Material Recommendation** — suggests **only approved** materials based on
   discussed topics (never invents non-approved content).
5. **Follow-Up Suggestion** — recommends next best actions for the rep.

---

## API Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/interaction/agent` | Run a prompt through LangGraph → updated interaction state |
| POST | `/api/interaction/save` | Persist the finalized interaction + write audit log |
| GET  | `/api/interaction/{id}` | Fetch a saved interaction |
| PATCH| `/api/interaction/{id}` | Partial update |
| GET  | `/api/hcps/search?q=` | Search HCP profiles |
| GET  | `/health` | Health / model info |

---

## Testing / Demo Prompts

Try these in the chat (right panel):

- *Log:* `Met Dr. Priya Sharma today at 10:30 AM for a meeting. Discussed Product X efficacy and safety profile. Shared the clinical study brochure. She seemed positive and asked for elderly patient data.`
- *Edit (preserves other fields):* `Change the sentiment to neutral and add Dr. Mehta as an attendee.`
- *Lookup:* `Look up Dr. Priya Sharma profile.`
- *Materials:* `Recommend materials for a discussion about Product X safety.`
- *Follow-ups:* `What follow-up actions should I plan after this meeting?`

A backend pipeline test lives at `backend/e2e_test.py` (run with
`cd backend && PYTHONPATH=. python e2e_test.py`).

---

## Submission Notes

- All code was generated with AI assistance per the assignment's "no human-written
  code" rule.
- `gemma2-9b-it` is decommissioned by Groq; the working default is
  `llama-3.3-70b-versatile` (assignment-approved alternative). Set `GROQ_MODEL`
  to use any other live Groq model.
- The `.env` file (with secrets) is gitignored; use `.env.example` as a template.
