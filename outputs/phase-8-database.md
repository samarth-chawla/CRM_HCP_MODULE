# Phase 8 — Database

Status: Complete

Persistence is built on SQLAlchemy with a schema matching the requirements
(section 17). PostgreSQL is recommended; SQLite is supported out-of-the-box for
local runs (no server required). All AI-driven changes are captured in an audit

## 1. Schema (`backend/app/db/models.py`)

| Table | Key columns |
| ----- | ----------- |
| `users` | id, name, email |
| `interactions` | id, hcp_id (FK), interaction_type, interaction_date, interaction_time, topics_discussed, sentiment, outcomes, created_by, timestamps |
| `interaction_attendees` | id, interaction_id (FK), name |
| `interaction_materials` | id, interaction_id (FK), material_id, material_name |
| `interaction_samples` | id, interaction_id (FK), product_name, quantity, batch_number |
| `follow_up_actions` | id, interaction_id (FK), action_text, due_date, status, owner_id, timestamps |
| `chat_messages` | id, interaction_id (FK), role, message |
| `audit_logs` | id, interaction_id, user_id, user_prompt, tool_called, previous_state, new_state, model_used, created_at |
| `approved_materials` | id, name (unique), category, approved |

`Interaction` has relationships to attendees/materials/samples/follow-ups
(cascade delete-orphan) and to `HCP`.

## 2. Session (`backend/app/db/session.py`)

- `engine` created from `DATABASE_URL` (SQLite gets `check_same_thread=False`).
- `SessionLocal` sessionmaker + `get_db()` FastAPI dependency.
- `init_db()` calls `create_all` and seeds `approved_materials` (5 approved
  items) and two demo HCPs so the lookup tool has data to return.

## 3. Persistence layer (`backend/app/db/crud.py`)

- `save_interaction(db, state, user_id)` → creates the `interactions` row and all
  child rows (attendees, materials, samples, follow-ups); returns `interactionId`.
- `get_interaction(db, id)` / `patch_interaction(db, id, patch)` → returns/
  updates `InteractionState`.
- `search_hcps(db, query)` / `get_hcp_by_name(db, name)` → HCP lookup.
- `write_audit(...)` → records prompt, tool called, previous/new state (JSON),
  model used, and timestamp — satisfying the audit requirements.

## 4. Audit logging

Every agent call and every save writes an `audit_logs` row: user prompt, tool
called, previous state, new state, model used, timestamp, user id. This preserves
requirement.

## 5. Configuration

```text
# .env
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/crm_hcp
# or, for quick local runs:
DATABASE_URL=sqlite:///./crm_hcp.db
```

`psycopg` (or `psycopg2`) is required for Postgres; SQLite needs no extra driver.

## 6. Acceptance check (Database)

- [x] SQL schema with all required tables.
- [x] ORM models defined (SQLAlchemy 2.0 style).
- [x] Persistence layer saves/reads interactions + children.
- [x] Audit logging implemented and called from endpoints.
- [x] Seeds approved materials + demo HCPs.

## 7. Next phase

Phase 9 wires the frontend API client to these endpoints and documents the full
integration.
