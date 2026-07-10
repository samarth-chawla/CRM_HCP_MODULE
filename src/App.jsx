import InteractionForm from './components/InteractionForm'
import AssistantChat from './components/AssistantChat'
import './App.css'

/**
 * App — the Log HCP Interaction screen.
 *
 * Split-screen shell: 65% read-only form (left) / 35% AI assistant (right).
 * The chat on the right is the only input surface; the form on the left is
 * controlled entirely by Redux, which is fed by the AI pipeline.
 */
export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">Rx</span>
          <div>
            <h1>Log HCP Interaction</h1>
            <p className="brand-sub">AI-First CRM · Healthcare Professional Module</p>
          </div>
        </div>
      </header>

      <main className="split">
        <div className="split-left">
          <InteractionForm />
        </div>
        <div className="split-right">
          <AssistantChat />
        </div>
      </main>
    </div>
  )
}
