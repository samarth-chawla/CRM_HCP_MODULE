import { useDispatch, useSelector } from 'react-redux'
import { setInteractionMode, setInteractionField } from '../features/interaction/interactionSlice'
import styles from './InteractionForm.module.css'

const SENTIMENTS = ['Unknown', 'Positive', 'Neutral', 'Negative']

/**
 * InteractionForm — the LEFT panel.
 *
 * Two modes (toggle in the header):
 *  - AI-controlled (default): every field is `disabled` (read-only). The form is populated ONLY by the LangGraph -> Groq pipeline via Redux actions
 *    (updateInteractionState / mergeInteractionPatch). This is the "conversational chat" logging path from the spec.
 *  - Manual entry: the rep may type directly into the structured form. Changes are written to Redux via setInteractionField. This is the "structured form" logging path.
 */
export default function InteractionForm() {
  const dispatch = useDispatch()
  const i = useSelector((s) => s.interaction)
  const manual = i.mode === 'manual'

  const isEmpty =
    !i.hcpName && !i.interactionType && !i.topicsDiscussed && !i.date

  // Edit helper used only in manual mode.
  const set = (field) => (e) => {
    const value = e.target.value
    dispatch(setInteractionField({ field, value }))
  }
  const setArray = (field) => (e) => {
    const arr = e.target.value
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean)
    dispatch(setInteractionField({ field, value: arr }))
  }

  return (
    <section className={styles.panel} aria-label="Interaction details">
      <header className={styles.panelHead}>
        <h2>Interaction Details</h2>
        <div className={styles.modeToggle}>
          <button
            type="button"
            className={`${styles.modeBtn} ${!manual ? styles.modeActive : ''}`}
            onClick={() => dispatch(setInteractionMode('ai'))}
          >
            AI-controlled
          </button>
          <button
            type="button"
            className={`${styles.modeBtn} ${manual ? styles.modeActive : ''}`}
            onClick={() => dispatch(setInteractionMode('manual'))}
          >
            Manual entry
          </button>
        </div>
      </header>

      <div className={styles.modeNote}>
        {manual
          ? 'Manual entry: you can type directly into the form. Switch to AI-controlled to log via chat.'
          : 'AI-controlled · read-only: describe the interaction in the assistant on the right and it populates automatically.'}
      </div>

      {isEmpty && !manual && (
        <div className={styles.emptyHint}>
          The form is empty. Describe the interaction in the assistant on the
          right and it will populate automatically (or switch to Manual entry).
        </div>
      )}

      <div className={styles.grid}>
        <Field label="HCP Name">
          <input
            className={styles.input}
            value={i.hcpName}
            disabled={!manual}
            readOnly={!manual}
            onChange={set('hcpName')}
          />
        </Field>

        <Field label="Interaction Type">
          <input
            className={styles.input}
            value={i.interactionType}
            disabled={!manual}
            readOnly={!manual}
            onChange={set('interactionType')}
          />
        </Field>

        <Field label="Date">
          <input
            className={styles.input}
            value={i.date}
            disabled={!manual}
            readOnly={!manual}
            onChange={set('date')}
          />
        </Field>

        <Field label="Time">
          <input
            className={styles.input}
            value={i.time}
            disabled={!manual}
            readOnly={!manual}
            onChange={set('time')}
          />
        </Field>

        <Field label="Attendees" wide>
          {manual ? (
            <input
              className={styles.input}
              placeholder="Comma-separated names"
              value={(i.attendees || []).join(', ')}
              disabled={!manual}
              onChange={setArray('attendees')}
            />
          ) : (
            <Tags value={i.attendees} empty="No attendees recorded" />
          )}
        </Field>

        <Field label="Topics Discussed" wide>
          {manual ? (
            <textarea
              className={styles.textarea}
              rows={2}
              value={i.topicsDiscussed}
              disabled={!manual}
              onChange={set('topicsDiscussed')}
            />
          ) : (
            <textarea className={styles.textarea} value={i.topicsDiscussed} disabled readOnly rows={2} />
          )}
        </Field>

        <Field label="Materials Shared" wide>
          {manual ? (
            <input
              className={styles.input}
              placeholder="Comma-separated materials"
              value={(i.materialsShared || []).join(', ')}
              disabled={!manual}
              onChange={setArray('materialsShared')}
            />
          ) : (
            <Tags value={i.materialsShared} empty="No materials shared" />
          )}
        </Field>

        <Field label="Samples Distributed" wide>
          {manual ? (
            <input
              className={styles.input}
              placeholder="e.g. Product Z x5 (B-123)"
              value={(i.samplesDistributed || []).map(formatSample).join(', ')}
              disabled={!manual}
              onChange={(e) =>
                dispatch(
                  setInteractionField({
                    field: 'samplesDistributed',
                    value: e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean)
                      .map((s) => ({ productName: s, quantity: 1, batchNumber: '' })),
                  }),
                )
              }
            />
          ) : (
            <Tags value={(i.samplesDistributed || []).map(formatSample)} empty="No samples distributed" />
          )}
        </Field>

        <Field label="Observed / Inferred HCP Sentiment">
          {manual ? (
            <div className={styles.radioGroup}>
              {SENTIMENTS.map((s) => (
                <label key={s} className={styles.radioPill}>
                  <input
                    type="radio"
                    name="sentiment"
                    value={s}
                    checked={i.sentiment === s}
                    disabled={!manual}
                    onChange={set('sentiment')}
                  />
                  {s}
                </label>
              ))}
            </div>
          ) : (
            <Sentiment value={i.sentiment} />
          )}
        </Field>

        <Field label="Outcomes" wide>
          {manual ? (
            <textarea
              className={styles.textarea}
              rows={2}
              value={i.outcomes}
              disabled={!manual}
              onChange={set('outcomes')}
            />
          ) : (
            <textarea className={styles.textarea} value={i.outcomes} disabled readOnly rows={2} />
          )}
        </Field>

        <Field label="Follow-up Actions" wide>
          {manual ? (
            <input
              className={styles.input}
              placeholder="Comma-separated actions"
              value={(i.followUpActions || []).join(', ')}
              disabled={!manual}
              onChange={setArray('followUpActions')}
            />
          ) : (
            <Tags value={i.followUpActions} empty="No follow-up actions" />
          )}
        </Field>

        <Field label="AI Suggested Follow-ups" wide>
          <Tags value={i.suggestedFollowUps} tone="suggested" empty="No suggestions yet" />
        </Field>
      </div>
    </section>
  )
}

function Field({ label, wide, children }) {
  return (
    <div className={`${styles.field} ${wide ? styles.wide : ''}`}>
      <label className={styles.label}>{label}</label>
      {children}
    </div>
  )
}

function Tags({ value, empty = '—', tone }) {
  const arr = Array.isArray(value) ? value : []
  if (arr.length === 0) {
    return <div className={styles.tagEmpty}>{empty}</div>
  }
  return (
    <div className={styles.tags}>
      {arr.map((t, idx) => (
        <span key={idx} className={`${styles.tag} ${tone === 'suggested' ? styles.tagSuggested : ''}`}>
          {t}
        </span>
      ))}
    </div>
  )
}

function Sentiment({ value }) {
  const v = (value || 'Unknown').toLowerCase()
  const cls = v === 'positive' ? styles.pos : v === 'negative' ? styles.neg : styles.neu
  return <span className={`${styles.sentiment} ${cls}`}>{value || 'Unknown'}</span>
}

function formatSample(s) {
  if (typeof s === 'string') return s
  return `${s.productName} ×${s.quantity} (${s.batchNumber})`
}
