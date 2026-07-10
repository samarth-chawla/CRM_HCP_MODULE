import { runAgent, saveInteraction } from '../../api/client'
import {
  addUserMessage,
  addAssistantMessage,
  setChatLoading,
  setChatError,
} from '../chat/chatSlice'
import {
  updateInteractionState,
  mergeInteractionPatch,
  setSuggestedFollowUps,
  resetInteraction,
} from '../interaction/interactionSlice'

/**
 * sendAgentMessage — the single bridge between the chat input and the backend.
 *
 * Flow: user message -> Redux -> FastAPI -> LangGraph -> Groq -> structured JSON
 * -> Redux state update -> read-only form auto-populates.
 */
export function sendAgentMessage(message) {
  return async (dispatch, getState) => {
    const trimmed = message?.trim()
    if (!trimmed) return

    dispatch(setChatError(null))
    dispatch(addUserMessage(trimmed))
    dispatch(setChatLoading(true))

    try {
      const currentInteractionState = getState().interaction
      const res = await runAgent({ message: trimmed, currentInteractionState })

      // The backend decides whether this was a full log or a partial edit.
      if (res.updatedInteractionState) {
        const isEdit = res.intent === 'edit' || res.selectedTool === 'edit_interaction'
        if (isEdit) {
          dispatch(mergeInteractionPatch(res.updatedInteractionState))
        } else {
          dispatch(updateInteractionState(res.updatedInteractionState))
        }
      }

      if (res.suggestedFollowUps) {
        dispatch(setSuggestedFollowUps(res.suggestedFollowUps))
      }

      dispatch(
        addAssistantMessage({
          content: res.assistantMessage || 'Done — I updated the interaction.',
          toolCalls: res.toolCalls || [],
        }),
      )
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Agent request failed.'
      dispatch(setChatError(detail))
      dispatch(
        addAssistantMessage({
          content: `⚠️ I couldn't process that: ${detail}`,
          toolCalls: [],
        }),
      )
    } finally {
      dispatch(setChatLoading(false))
    }
  }
}

/**
 * persistInteraction — save the current read-only form to the backend.
 */
export function persistInteraction() {
  return async (dispatch, getState) => {
    dispatch(setChatError(null))
    dispatch(setChatLoading(true))
    try {
      const interaction = getState().interaction
      const res = await saveInteraction({ interaction })
      dispatch(
        addAssistantMessage({
          content: `Interaction saved (${res.interactionId}). Audit log recorded.`,
          toolCalls: ['interaction.save'],
        }),
      )
      return res
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Save failed.'
      dispatch(setChatError(detail))
      throw err
    } finally {
      dispatch(setChatLoading(false))
    }
  }
}

export function startNewInteraction() {
  return (dispatch) => {
    dispatch(resetInteraction())
  }
}
