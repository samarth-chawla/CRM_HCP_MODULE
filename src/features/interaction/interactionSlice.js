import { createSlice } from '@reduxjs/toolkit'

/**
 * interactionSlice — the single source of truth for the LEFT panel form.
 * The form is READ-ONLY in the UI. The only way these fields change is through the Redux actions defined here, which are dispatched after the FastAPI /LangGraph / Groq pipeline returns structured JSON. There is intentionally no action that accepts raw user-typed field values.
 */

export const initialInteractionState = {
  hcpId: null,
  hcpName: '',
  interactionType: '',
  date: '',
  time: '',
  attendees: [],
  topicsDiscussed: '',
  materialsShared: [],
  samplesDistributed: [],
  sentiment: 'Unknown',
  outcomes: '',
  followUpActions: [],
  suggestedFollowUps: [],
  // 'ai' = form is AI-controlled / read-only; 'manual' = rep may type directly.
  mode: 'ai',
}

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: { ...initialInteractionState },
  reducers: {
    /**
     * Switch between AI-controlled (read-only) and Manual entry modes.
     */
    setInteractionMode(state, action) {
      state.mode = action.payload === 'manual' ? 'manual' : 'ai'
    },

    /**
     * Set a single field directly (only used in Manual entry mode, where the rep types into the structured form). In AI mode the form stays read-only and is driven exclusively by updateInteractionState / mergeInteractionPatch.
     */
    setInteractionField(state, action) {
      const { field, value } = action.payload || {}
      if (!field || !(field in state)) return
      state[field] = value
    },

    /**
     * Replace the entire interaction state (used after a Log Interaction pass).
     */
    updateInteractionState(state, action) {
      return { ...initialInteractionState, ...action.payload }
    },

    /**
     * Deep-merge a partial patch (used after an Edit Interaction pass).
     * Arrays from the patch replace their counterparts.
     */
    mergeInteractionPatch(state, action) {
      const patch = action.payload || {}
      for (const key of Object.keys(patch)) {
        state[key] = patch[key]
      }
    },

    /**
     * Overwrite only the AI-suggested follow-ups (never the user-confirmed ones).
     */
    setSuggestedFollowUps(state, action) {
      state.suggestedFollowUps = action.payload || []
    },

    /**
     * Clear the form back to its empty starting point.
     */
    resetInteraction() {
      return { ...initialInteractionState }
    },
  },
})

export const {
  setInteractionMode,
  setInteractionField,
  updateInteractionState,
  mergeInteractionPatch,
  setSuggestedFollowUps,
  resetInteraction,
} = interactionSlice.actions

export default interactionSlice.reducer
