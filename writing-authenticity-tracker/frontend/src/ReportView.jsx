function scoreColor(score) {
  if (score < 25) return '#2e7d32'
  if (score < 55) return '#e6a700'
  return '#c0392b'
}

const CLASS_LABELS = {
  honest: 'Honest / natural typing',
  paste_heavy: 'Paste-heavy',
  auto_typed: 'Auto-typed / humanized',
}

export default function ReportView({ report, onReset }) {
  const { heuristic, ml, baseline_comparison, text_pattern_analysis, agent_review, layers_active } = report

  return (
    <div className="report-panel">
      {/* ---------- Layer 1: Heuristic ---------- */}
      <div className="score-card" style={{ borderColor: scoreColor(heuristic.suspicion_score) }}>
        <div className="layer-tag">Layer 1 · Heuristic</div>
        <div className="score-number" style={{ color: scoreColor(heuristic.suspicion_score) }}>
          {heuristic.suspicion_score}
          <span className="score-max">/100</span>
        </div>
        <div className="verdict-label">{heuristic.verdict_label}</div>
      </div>

      <p className="disclaimer">{heuristic.disclaimer}</p>

      <h2>Heuristic Signal Breakdown</h2>
      <div className="signals-list">
        {heuristic.signals.map((s) => (
          <div className="signal-row" key={s.name}>
            <div className="signal-header">
              <span className="signal-name">{s.name}</span>
              <span className="signal-contribution">
                +{s.contribution} / {s.max_contribution}
              </span>
            </div>
            <div className="signal-bar-track">
              <div
                className="signal-bar-fill"
                style={{
                  width: `${(s.contribution / s.max_contribution) * 100}%`,
                  background: scoreColor((s.contribution / s.max_contribution) * 100),
                }}
              />
            </div>
            <div className="signal-value">{s.value}</div>
          </div>
        ))}
      </div>

      {/* ---------- Layer 2: ML classifier ---------- */}
      {layers_active.ml && ml && (
        <>
          <h2>Layer 2 · ML Classifier Prediction</h2>
          <div className="ml-card">
            <div className="ml-predicted">
              Predicted: <strong>{CLASS_LABELS[ml.predicted_class] || ml.predicted_class}</strong>
            </div>
            <div className="ml-probs">
              {Object.entries(ml.class_probabilities).map(([cls, prob]) => (
                <div className="ml-prob-row" key={cls}>
                  <span className="ml-prob-label">{CLASS_LABELS[cls] || cls}</span>
                  <div className="ml-prob-track">
                    <div className="ml-prob-fill" style={{ width: `${prob}%` }} />
                  </div>
                  <span className="ml-prob-value">{prob}%</span>
                </div>
              ))}
            </div>
            <div className="ml-factors">
              <span className="ml-factors-label">Top contributing factors:</span>
              {ml.top_factors.map((f) => (
                <span className="factor-pill" key={f.feature}>
                  {f.feature} ({f.influence > 0 ? '+' : ''}{f.influence})
                </span>
              ))}
            </div>
          </div>
        </>
      )}

      {/* ---------- Layer 3: Personalized baseline ---------- */}
      <h2>Layer 3 · Personalized Baseline</h2>
      {layers_active.baseline && baseline_comparison ? (
        <div className="baseline-card">
          <div className="baseline-row">
            <span>Typing rhythm vs. your baseline</span>
            <strong>{formatDelta(baseline_comparison.rhythm_delta_pct)}</strong>
          </div>
          <div className="baseline-row">
            <span>Correction rate vs. your baseline</span>
            <strong>{formatDelta(baseline_comparison.correction_delta_pct)}</strong>
          </div>
          <div className="baseline-row">
            <span>Typing speed vs. your baseline</span>
            <strong>{formatDelta(baseline_comparison.speed_delta_pct)}</strong>
          </div>
          {baseline_comparison.deviation_flags.length > 0 ? (
            <ul className="deviation-flags">
              {baseline_comparison.deviation_flags.map((flag, i) => (
                <li key={i}>{flag}</li>
              ))}
            </ul>
          ) : (
            <div className="no-deviation">No meaningful deviation from your established baseline.</div>
          )}
        </div>
      ) : (
        <div className="empty-layer">
          No baseline calibrated for this session — scored against general
          thresholds only. Calibrate a baseline next time for a fairer,
          personalized comparison.
        </div>
      )}

      {/* ---------- Layer 4: GenAI + agentic review ---------- */}
      <h2>Layer 4 · GenAI Text Analysis &amp; Agent Review</h2>
      {layers_active.genai && text_pattern_analysis ? (
        <>
          <div className="genai-card">
            <div className="genai-score-row">
              <span>AI-writing-pattern likelihood</span>
              <strong style={{ color: scoreColor(text_pattern_analysis.ai_likelihood_score) }}>
                {text_pattern_analysis.ai_likelihood_score}/100
              </strong>
            </div>
            <p className="genai-reasoning">{text_pattern_analysis.reasoning}</p>
          </div>

          {agent_review && (
            <div className={`agent-card ${agent_review.should_flag ? 'flagged' : 'clear'}`}>
              <div className="agent-header">
                <span className="agent-icon">{agent_review.should_flag ? '🚩' : '✓'}</span>
                <span className="agent-verdict">
                  {agent_review.should_flag ? 'Agent recommends a follow-up conversation' : 'Agent found no flag-worthy pattern'}
                </span>
                <span className="agent-confidence">confidence: {agent_review.confidence}</span>
              </div>
              <p className="agent-reasoning">{agent_review.reasoning}</p>
              {agent_review.should_flag && agent_review.drafted_message && (
                <div className="drafted-message">
                  <div className="drafted-message-label">Drafted message to student:</div>
                  <div className="drafted-message-body">{agent_review.drafted_message}</div>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="empty-layer">
          GenAI layer not run for this session (no API key set, or the toggle was off).
        </div>
      )}

      {/* ---------- Raw stats ---------- */}
      <h2>Raw Session Stats</h2>
      <div className="stats-grid">
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.final_text_length}</div>
          <div className="stat-label">Characters written</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.total_keystrokes}</div>
          <div className="stat-label">Total keystrokes</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.total_pastes}</div>
          <div className="stat-label">Paste events</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.total_pasted_chars}</div>
          <div className="stat-label">Characters pasted</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.session_duration_seconds}s</div>
          <div className="stat-label">Session duration</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{heuristic.raw_stats.click_count}</div>
          <div className="stat-label">Clicks in editor</div>
        </div>
      </div>

      <button className="btn-primary" onClick={onReset}>
        Start New Session
      </button>
    </div>
  )
}

function formatDelta(pct) {
  if (pct === null || pct === undefined) return 'n/a'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct}%`
}
