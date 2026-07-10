import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendAgentMessage, persistInteraction, startNewInteraction } from '../features/interaction/interactionThunks'
import { setChatError } from '../features/chat/chatSlice'
import styles from './AssistantChat.module.css'

/**
 * AssistantChat — the RIGHT panel.
 * This is the ONLY editable surface for logging an interaction. Typing a prompt dispatches sendAgentMessage, which drives the full client -> backend -> LangGraph -> Groq -> Redux pipeline. The chat also surfaces loading and error states and exposes the Save action for the finalized record.
 */
export default function AssistantChat() {
  const dispatch = useDispatch()
  const { messages, isLoading, error } = useSelector((s) => s.chat)
  const interaction = useSelector((s) => s.interaction)
  const [text, setText] = useState('')

  const canSave =
    interaction.hcpName && interaction.interactionType && interaction.date && interaction.topicsDiscussed

  const submit = (e) => {
    e.preventDefault()
    const value = text.trim()
    if (!value || isLoading) return
    dispatch(sendAgentMessage(value))
    setText('')
  }

  const onSave = async () => {
    dispatch(setChatError(null))
    try {
      await dispatch(persistInteraction()).unwrap()
    } catch {
      /* error already in chat.error */
    }
  }

  return (
    <section className={styles.panel} aria-label="AI assistant">
      <header className={styles.head}>
        <div>
          <h2>AI Assistant</h2>
          <p className={styles.subtitle}>Log & edit HCP interactions by chatting</p>
        </div>
        <button
          type="button"
          className={styles.newBtn}
          onClick={() => dispatch(startNewInteraction())}
          disabled={isLoading}
        >
          New
        </button>
      </header>

      <div className={styles.messages}>
        {messages.map((m) => (
          <Message key={m.id} message={m} />
        ))}
        {isLoading && (
          <div className={`${styles.msg} ${styles.assistant}`}>
            <div className={styles.bubble}>
              <span className={styles.typing}>
                <i /> <i /> <i />
              </span>
            </div>
          </div>
        )}
        {error && (
          <div className={`${styles.msg} ${styles.assistant}`}>
            <div className={`${styles.bubble} ${styles.errorBubble}`}>{error}</div>
          </div>
        )}
      </div>

      <div className={styles.composer}>
        {!canSave && (
          <p className={styles.saveHint}>
            Fill HCP name, type, date &amp; topics via chat before saving.
          </p>
        )}
        <form className={styles.form} onSubmit={submit}>
          <textarea
            className={styles.input}
            placeholder="Describe interaction..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) submit(e)
            }}
            rows={2}
            disabled={isLoading}
          />
          <div className={styles.actions}>
            <button type="submit" className={styles.sendBtn} disabled={isLoading || !text.trim()}>
              Send
            </button>
            <button type="button" className={styles.saveBtn} onClick={onSave} disabled={isLoading || !canSave}>
              Save interaction
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`${styles.msg} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.bubble}>
        {message.content}
        {message.toolCalls?.length > 0 && (
          <div className={styles.toolCalls}>
            {message.toolCalls.map((t, idx) => (
              <span key={idx} className={styles.toolChip}>
                ⚙ {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
