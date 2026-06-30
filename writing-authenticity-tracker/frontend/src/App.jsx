import { useState, useEffect } from 'react'
import { useSessionTracker } from './useSessionTracker.js'
import CalibrationView from './CalibrationView.jsx'
import ReportView from './ReportView.jsx'

const API_URL = 'http://localhost:8000'
const STUDENT_ID = 'demo_student'

export default function App() {
  const [stage, setStage] = useState('loading') // loading | calibration | writing | report
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [genaiAvailable, setGenaiAvailable] = useState(false)
  const [useGenai, setUseGenai] = useState(false)

  const { text, sessionStarted, handlers, getPayload, reset } = useSessionTracker()

  // Check server status + whether this student already has a baseline
  useEffect(() => {
    const init = async () => {
      try {
        const statusRes = await fetch(`${API_URL}/`)
        const status = await statusRes.json()
        setGenaiAvailable(!!status.genai_available)

        const baselineRes = await fetch(`${API_URL}/baseline_status/${STUDENT_ID}`)
        const baselineData = await baselineRes.json()
        setStage(baselineData.has_baseline ? 'writing' : 'calibration')
      } catch (err) {
        setError(
          `Could not reach the backend at ${API_URL}. Make sure the FastAPI server is running (uvicorn main:app --reload --port 8000).`
        )
        setStage('writing') // allow them to still try
      }
    }
    init()
  }, [])

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError('Write or paste something first.')
      return
    }
    setLoading(true)
    setError(null)

    const payload = {
      ...getPayload(),
      student_id: STUDENT_ID,
      use_genai: useGenai && genaiAvailable,
    }

    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`Server returned ${res.status}`)
      const data = await res.json()
      setReport(data)
      setStage('report')
    } catch (err) {
      setError(
        `Could not reach the backend (${err.message}). Make sure the FastAPI server is running on port 8000.`
      )
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    reset()
    setReport(null)
    setError(null)
    setStage('writing')
  }

  return (
    <div className="app">
      <header className="header">
        <h1>✍️ Writing Authenticity Tracker</h1>
        <p className="subtitle">
          Logs typing behavior, scores it with a hand-tuned heuristic AND a
          trained ML classifier, compares it to your own personal baseline,
          and — optionally — runs a GenAI text + agentic review on top.
        </p>
      </header>

      {stage === 'loading' && <div className="loading-state">Connecting to backend...</div>}

      {stage === 'calibration' && (
        <CalibrationView
          studentId={STUDENT_ID}
          onDone={() => setStage('writing')}
          onSkip={() => setStage('writing')}
        />
      )}

      {stage === 'writing' && (
        <div className="writing-panel">
          <div className="status-bar">
            <span className={`dot ${sessionStarted ? 'active' : ''}`} />
            {sessionStarted ? 'Session recording...' : 'Start typing to begin tracking'}
          </div>

          <textarea
            className="editor"
            placeholder="Start writing your assignment here... (try typing normally, or paste some text, and see how the report differs)"
            value={text}
            rows={14}
            {...handlers}
          />

          <div className="action-row">
            <span className="char-count">{text.length} characters</span>
            <div className="buttons">
              <button className="btn-secondary" onClick={handleReset}>
                Reset
              </button>
              <button className="btn-primary" onClick={handleAnalyze} disabled={loading}>
                {loading ? 'Analyzing...' : 'Submit for Analysis'}
              </button>
            </div>
          </div>

          <div className="genai-toggle-row">
            <label className={`genai-toggle ${!genaiAvailable ? 'disabled' : ''}`}>
              <input
                type="checkbox"
                checked={useGenai}
                disabled={!genaiAvailable}
                onChange={(e) => setUseGenai(e.target.checked)}
              />
              Run GenAI text analysis + agentic review
            </label>
            {!genaiAvailable && (
              <span className="genai-hint">
                Requires OPENAI_API_KEY set on the backend
              </span>
            )}
          </div>

          {error && <div className="error-banner">{error}</div>}
        </div>
      )}

      {stage === 'report' && report && (
        <ReportView report={report} onReset={handleReset} />
      )}
    </div>
  )
}
