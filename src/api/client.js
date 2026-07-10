import axios from 'axios'

/**
 * API client for the FastAPI backend.
 *
 * VITE_API_BASE defaults to the FastAPI dev server. Override with a .env file:
 *   VITE_API_BASE=http://localhost:8000
 */
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const http = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * POST /api/interaction/agent
 * Send the latest prompt + current interaction state to LangGraph.
 */
export async function runAgent({ message, currentInteractionState }) {
  const { data } = await http.post('/api/interaction/agent', {
    message,
    currentInteractionState,
  })
  return data
}

/**
 * POST /api/interaction/save
 * Persist the finalized interaction record.
 */
export async function saveInteraction({ interaction }) {
  const { data } = await http.post('/api/interaction/save', { interaction })
  return data
}

/**
 * GET /api/hcps/search?q=...  — used by the HCP Profile Lookup tool display.
 */
export async function searchHcps(query) {
  const { data } = await http.get('/api/hcps/search', { params: { q: query } })
  return data
}

export default http
