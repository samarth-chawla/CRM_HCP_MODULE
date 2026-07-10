import { configureStore } from '@reduxjs/toolkit'
import interactionReducer from '../features/interaction/interactionSlice'
import chatReducer from '../features/chat/chatSlice'

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
  },
})
