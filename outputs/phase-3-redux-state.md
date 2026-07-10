# Phase 3 — Redux State

Status: Complete

This phase owns all client-side state with **Redux Toolkit**. The two slices are
the single source of truth for the screen: the `interaction` slice drives the
read-only form, and the `chat` slice drives the assistant panel. The form is
deliberately *not* directly editable — its only mutation paths are the slice
reducers, which are dispatched after the AI pipeline returns.

## 1. Store (`src/app/store.js`)

```js
configureStore({
  reducer: { interaction: interactionReducer, chat: chatReducer },
})
```

Wrapped in `<Provider store={store}>` in `src/main.jsx`.

## 2. interactionSlice (`src/features/interaction/interactionSlice.js`)

Initial state matches the required shape exactly:

```js
{
  hcpId: null, hcpName: '', interactionType: '', date: '', time: '',
  attendees: [], topicsDiscussed: '', materialsShared: [], samplesDistributed: [],
  sentiment: 'Unknown', outcomes: '', followUpActions: [], suggestedFollowUps: [],
}
```

### Actions (all required actions implemented)

| Action | Behavior |
| ------ | -------- |
| `updateInteractionState` | Replace whole state with payload (Log Interaction pass). Resets to defaults first so stale fields don't linger. |
| `setSuggestedFollowUps` | Overwrite only AI-suggested follow-ups (never the confirmed ones). |
| `resetInteraction` | Return to empty defaults (New interaction). |

> There is **no** action accepting raw user-typed field values — that is the
> enforcement of the "form is AI-controlled" rule at the state layer.

## 3. chatSlice (`src/features/chat/chatSlice.js`)

```js
{ messages: [starterMessage], isLoading: false, error: null }
```

The starter message teaches the rep how to describe an interaction.

| Action | Behavior |
| ------ | -------- |
| `addUserMessage` | Append a user message (auto id). |
| `addAssistantMessage` | Append an assistant message (with optional `toolCalls` for display). |
| `setChatLoading` | Toggle the typing indicator / button disabled state. |
| `setChatError` | Set an error string (rendered as a red bubble). |
| `resetChat` | Restore the starter conversation. |

## 4. Thunks / orchestration (`src/features/interaction/interactionThunks.js`)

These connect Redux to the backend (Phase 9) and are the actual mutation entry
points used by the UI:

- `sendAgentMessage(message)` — appends user msg, calls `/api/interaction/agent`
  with the current state, then dispatches `updateInteractionState` (log) or
  and `addAssistantMessage`. Handles error + loading states.
- `persistInteraction()` — calls `/api/interaction/save` and confirms in chat.
- `startNewInteraction()` — resets the form.

The edit-vs-log decision uses the backend `intent` / `selectedTool` so edits
preserve unchanged fields (requirement: "Edit Interaction must not overwrite
unrelated fields").

## 5. Selectors (used in components)

- `InteractionForm` selects `state.interaction`.
- `AssistantChat` selects `state.chat` (messages, isLoading, error) and
  `state.interaction` (to enable Save when required fields are present).

## 6. Data flow (the required chain, enforced in code)

```text
User prompt (chat input)
 -> dispatch(sendAgentMessage)
 -> Redux: addUserMessage, setChatLoading
 -> FastAPI -> LangGraph -> Groq -> JSON
 -> Redux: updateInteractionState / mergeInteractionPatch
 -> read-only form auto-populates
```

## 7. Files

| File | Purpose |
| ---- | ------- |
| `src/app/store.js` | Store configuration |
| `src/features/interaction/interactionSlice.js` | Form state + actions |
| `src/features/chat/chatSlice.js` | Chat state + actions |
| `src/features/interaction/interactionThunks.js` | Agent + save orchestration |
| `src/main.jsx` | Provider wraps App |

## 8. Acceptance check (Redux)

- [x] Redux Toolkit store created.
- [x] `interactionSlice` + `chatSlice` present.
- [x] All required actions implemented.
- [x] Form controlled by Redux, no raw field typing.
- [x] Edit merges (preserves untouched fields); log replaces.
- [x] `main.jsx` provides the store to the UI.

## 9. Next phase

Phase 4 builds the FastAPI backend (`/api/interaction/agent`,
`/api/interaction/save`, etc.) that the thunks call.
