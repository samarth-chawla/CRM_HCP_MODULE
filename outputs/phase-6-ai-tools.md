# Phase 6 — AI Tools

Status: Complete

Six LangGraph tools are implemented in `backend/app/agent/tools.py` (spec
requires a minimum of five). Each tool returns a dict the agent merges into the
shared state: `{ updatedInteractionState, assistantMessage, suggestedFollowUps,

## 1. Log Interaction (`log_interaction`) — mandatory

- Builds a structured-extraction prompt (`log_interaction_prompt`) and calls
  Groq (`gemma2-9b-it`).
- Extracts: HCP name, interaction type, date, time, attendees, topics,
  materials, samples (with quantity/batch), sentiment, outcomes, follow-ups.
- Missing values are left empty / `null` (never invented).

## 2. Edit Interaction (`edit_interaction`) — mandatory

- Builds an edit prompt with the **current** state and asks Groq for a JSON
  patch of *only* the requested fields.
- Starts from `current.model_copy(deep=True)` and applies only the changed keys,
  so all unchanged fields are preserved (requirement: "Edit Interaction must not
  overwrite unrelated fields").

## 3. HCP Profile Lookup (`hcp_profile_lookup`)

- Looks up the HCP by name in the CRM (`crud.get_hcp_by_name`). If not found,
  creates a lightweight placeholder record so the form can be enriched.
- Returns specialty, territory, preferred channel, previous product interest,
- Sets `hcpId` + `hcpName` on the state.

## 4. Material Recommendation (`material_recommendation`)

- Prompts Groq for approved materials based on discussed topics.
- **Only approved materials** (the `APPROVED` set: Clinical study brochure,
  Safety profile PDF, Product detail aid, Patient subgroup analysis, Dosing
  guide) are kept — non-approved suggestions are dropped. Nothing is invented.
- Appends recommended materials to `materialsShared` if not already present.

## 5. Follow-Up Suggestion (`follow_up_suggestion`)

- Prompts Groq for 2–3 next best actions from the interaction.
- Returns them as `suggestedFollowUps` (kept separate from *confirmed*
  `followUpActions`).


Deterministic life-sciences validation (runs in every relevant flow):

- Missing required fields → warning.
- Non-approved shared material → warning.
- Sample without quantity + batch number → warning.
- HCP restriction (e.g. "No samples") violated → warning.
- Returns `{ status: "Approved" | "Warning", warnings: [...] }`.

## Shared helpers

- `_norm`, `_sentiment`, `_str`, `_coerce_sample`, `_extract_name` keep field
  normalization consistent across tools.
- Each tool is wrapped by the agent's `_run()` so exceptions are captured as
  `errors` rather than breaking the graph.

## Acceptance check (AI tools)

- [x] ≥ 5 tools (we have 6).
- [x] Log Interaction parses NL into structured data (uses Groq).
- [x] Edit Interaction updates only requested fields.
- [x] HCP Profile Lookup enriches records.
- [x] Material Recommendation suggests approved materials only.
- [x] Follow-Up Suggestion generates next actions.
- [x] No invented data; null/empty used for missing values.

## Next phase

Phase 7 covers the Groq client + prompt templates these tools call.
