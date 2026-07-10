# Phase 2 — Frontend UI

Status: Complete

This phase delivers the **Log HCP Interaction** screen: a split-screen layout
with a read-only interaction form on the left and an AI assistant chat on the
right. The chat is the only editable input surface; the form is fully controlled
by Redux (populated later by the AI pipeline).

## 1. Layout

`src/App.jsx` renders the shell:

```text
┌──────────────────────────────────────────────────────────┐
│ Header: Log HCP Interaction · AI-First CRM                 │
├───────────────────────────────┬──────────────────────────┤
│ LEFT 65%                      │ RIGHT 35%                 │
│ Interaction Details form      │ AI Assistant chat         │
│ (read-only, AI-controlled)    │ messages · input · Save   │
└───────────────────────────────┴──────────────────────────┘
```

- **Desktop:** split 65% / 35% (`src/App.css`).
- **Tablet (≤1024px):** split 60% / 40%.
- **Mobile (≤720px):** panels stack vertically.

## 2. Visual design

- **Font:** Google **Inter** via `@import` in `src/index.css` (weights 400–700).
- **Theme tokens** in `:root`: brand blue, neutral slate, success/warning/danger
  status colors, sentiment colors, radius + shadow scale. Reads as a
  professional CRM, not a demo template.
- Header has a brand mark (`Rx`) + title + subtitle.

## 3. Left panel — InteractionForm (`src/components/InteractionForm.jsx`)

Read-only form with all required fields, every input `disabled` + `readOnly`:

- HCP Name, Interaction Type, Date, Time
- Attendees (chips), Topics Discussed (textarea)
- Materials Shared (chips), Samples Distributed (chips, formatted as
  `Product ×Qty (Batch)`)
- Observed/Inferred HCP Sentiment (colored pill: Positive/Negative/Unknown)
- Outcomes, Follow-up Actions (chips), AI Suggested Follow-ups (muted chips)

UX details:
- An `AI-controlled · read-only` badge makes the control rule explicit.
- An empty-state hint prompts the rep to use the chat.
- Values are sourced from the Redux `interaction` slice (wired in Phase 3).

## 4. Right panel — AssistantChat (`src/components/AssistantChat.jsx`)

AI assistant chat with:
- **Header** + short subtitle.
- **Message history** (user right-aligned, assistant left-aligned). Assistant
  messages can render tool-call chips (`⚙ tool_name`).
- **Starter message** that explains how to describe an interaction.
- **Composer**: multi-line input (Enter to send, Shift+Enter newline),
  `Send` button, and `Save interaction` button (enabled only when required
  fields are present).
- **Loading state**: animated typing indicator while the agent runs.
- **Error state**: red error bubble driven by `chat.error`.
- Behavior is wired in Phase 3/9 (`sendAgentMessage`, `persistInteraction`).

## 5. Files created / modified

| File | Purpose |
| ---- | ------- |
| `src/index.css` | Theme tokens + Inter font |
| `src/App.jsx` | Split-screen shell |
| `src/App.css` | Split layout + responsive rules |
| `src/components/InteractionForm.jsx` | Left read-only form |
| `src/components/InteractionForm.module.css` | Form styles |
| `src/components/AssistantChat.jsx` | Right chat panel |
| `src/components/AssistantChat.module.css` | Chat styles |
| `vite.config.js` | Dev server pinned to port 5173 |

## 6. Acceptance check (UI)

- [x] Split-screen layout implemented (65/35, responsive).
- [x] Left form present, all fields disabled/read-only.
- [x] Right chat present, the only editable input.
- [x] Form values come from Redux state (Phase 3).
- [x] Loading + error states visible.
- [x] Inter font used.
- [x] Professional CRM appearance.

## 7. Next phase

Phase 3 builds the Redux store (`interactionSlice`, `chatSlice`, actions,
selectors) and connects these components to it so the form renders live state.
