import { createSlice } from '@reduxjs/toolkit'

/**
 * chatSlice — the right panel AI assistant conversation state.
 *
 * Messages are appended as the conversation progresses. `isLoading` drives the typing indicator while the backend agent is running. `error` surfaces backend
 * failures. All chat mutations go through these actions — the UI never mutates the array directly.
 */

const starterMessage = {
  id: 'starter',
  role: 'assistant',
  content:
    'Log interaction details here (e.g., "Met Dr. Smith discussed Product X efficacy, positive sentiment, shared brochure") or ask for help',
}

const initialState = {
  messages: [starterMessage],
  isLoading: false,
  error: null,
}

let messageSeq = 1
const nextId = () => `msg-${Date.now()}-${messageSeq++}`

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({ id: nextId(), role: 'user', content: action.payload })
    },

    addAssistantMessage(state, action) {
      state.messages.push({
        id: nextId(),
        role: 'assistant',
        content: action.payload?.content ?? '',
        toolCalls: action.payload?.toolCalls ?? [],
      })
    },

    setChatLoading(state, action) {
      state.isLoading = Boolean(action.payload)
    },

    setChatError(state, action) {
      state.error = action.payload
    },

    resetChat() {
      return { ...initialState, messages: [starterMessage] }
    },
  },
})

export const { addUserMessage, addAssistantMessage, setChatLoading, setChatError, resetChat } =
  chatSlice.actions

export default chatSlice.reducer
