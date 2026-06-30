import { useSessionTracker } from './useSessionTracker.js'

const API_URL = 'http://localhost:8000'
const MIN_CHARS = 200

export default function CalibrationView({ studentId, onDone, onSkip }) {
  const { text, sessionStarted, handlers, getPayload, reset } = useSessionTracker()

  const submit = async () => {
    const payload = { ...getPayload(), student_id: studentId, is_calibration: true }
    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`Server returned ${res.status}`)
      await res.json()
      onDone()
    } catch (err) {
      alert(`Could not save calibration: ${err.message}`)
    }
  }

  const ready = text.trim().length >= MIN_CHARS

  return (
    <div className="writing-panel calibration-panel">
      <div className="calibration-badge">Step 1 of 2 — Calibration</div>
      <h2 className="calibration-title">Establish your own baseline</h2>
      <p className="subtitle">
        Type at least {MIN_CHARS} characters naturally — anything is fine,
        just write the way you normally would. This becomes{' '}
        <strong>your personal norm</strong>, so future sessions are judged
        against how <em>you</em> actually type, not a generic average.
      </p>

      <div className="status-bar">
        <span className={`dot ${sessionStarted ? 'active' : ''}`} />
        {sessionStarted ? 'Recording your baseline...' : 'Start typing to begin'}
      </div>

      <textarea
        className="editor"
        placeholder="Write a few sentences about anything — your day, a topic you know well, whatever feels natural..."
        value={text}
        rows={10}
        {...handlers}
      />

      <div className="action-row">
        <span className={`char-count ${ready ? 'ready' : ''}`}>
          {text.length} / {MIN_CHARS} characters
        </span>
        <div className="buttons">
          <button className="btn-secondary" onClick={onSkip}>
            Skip calibration
          </button>
          <button className="btn-primary" onClick={submit} disabled={!ready}>
            Save Baseline
          </button>
        </div>
      </div>
    </div>
  )
}
