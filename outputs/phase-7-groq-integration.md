# Phase 7 — Groq Integration

Status: Complete

Groq is the LLM provider. The backend reads the key from `GROQ_API_KEY` and calls
the primary model **`gemma2-9b-it`** (overridable via `GROQ_MODEL`). The
integration lives in `backend/app/llm/`.

## 1. Client (`groq_client.py`)

`GroqClient`:

- Reads `settings.groq_model` (`gemma2-9b-it`) and lazily constructs the
  `groq.Groq` client only when `GROQ_API_KEY` is present.
- `complete_json(prompt)` — sends a system instruction + user prompt with
  `response_format={"type": "json_object"}`, then parses the JSON. On any error
  (network, quota, bad JSON) it falls back to a deterministic heuristic
  extractor so the pipeline still runs end-to-end and remains demonstrably wired
  through LangGraph.
- `chat(prompt)` — free-text completion for non-JSON needs.
- `available` flag reports whether the real API is configured.

### System instruction (the key constraint)

> "Return ONLY valid JSON. Do not invent missing information: use null or an
> empty array/string for anything not stated. Allowed sentiment values:
> 'Positive', 'Negative', 'Neutral', 'Unknown'."

This enforces the requirement: *Do not invent missing information.*

## 2. Prompt templates (`prompts.py`)

Reusable templates keep tool prompts consistent:

- `log_interaction_prompt(message)` — extraction with an explicit key schema and
  the session date (2026-07-09) so relative dates resolve.
- `edit_interaction_prompt(message, current)` — asks for a JSON **patch** of only
  the requested fields.
- `follow_up_prompt(state)` — requests 2–3 next best actions.
- `material_recommendation_prompt(topics)` — restricts suggestions to the
  approved materials list.

## 3. Model configuration

| Setting | Value | Source |
| ------- | ----- | ------ |
| Primary model | `gemma2-9b-it` | `GROQ_MODEL` env (default) |
| Optional richer model | `llama-3.3-70b-versatile` | set `GROQ_MODEL` to use |
| API key | from `GROQ_API_KEY` | env / `.env` |

When no key is set, `groq_client.available` is `False` and the deterministic
fallback is used — guaranteeing the app runs for evaluation without external
credentials, while the real Groq path is the default whenever a key exists.

## 4. Where Groq is invoked

- `log_interaction` → `complete_json(log_interaction_prompt(...))`
- `edit_interaction` → `complete_json(edit_interaction_prompt(...))`
- `follow_up_suggestion` → `complete_json(follow_up_prompt(...))`
- `material_recommendation` → `complete_json(material_recommendation_prompt(...))`


## 5. Acceptance check (Groq)

- [x] Groq client reads `GROQ_API_KEY`.
- [x] Primary model `gemma2-9b-it` is used by default.
- [x] Prompt requests structured JSON and forbids invented data.
- [x] JSON is parsed/validated before returning to the agent.
- [x] Graceful fallback keeps the pipeline runnable without a key.

## 6. Next phase

Phase 8 builds the database layer these tools and the endpoints persist to.
