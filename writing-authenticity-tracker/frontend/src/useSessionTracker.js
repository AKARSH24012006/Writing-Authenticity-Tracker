import { useState, useRef, useCallback } from 'react'

/**
 * Encapsulates all the raw event-capture logic (keystrokes, pastes,
 * blurs, clicks) so both the calibration flow and the real writing
 * session can reuse the exact same tracking behavior.
 */
export function useSessionTracker() {
  const [text, setText] = useState('')
  const [sessionStarted, setSessionStarted] = useState(false)

  const sessionStartRef = useRef(null)
  const keystrokesRef = useRef([])
  const pastesRef = useRef([])
  const blursRef = useRef([])
  const clickCountRef = useRef(0)
  const lastBlurRef = useRef(null)

  const now = useCallback(() => {
    if (!sessionStartRef.current) return 0
    return performance.now() - sessionStartRef.current
  }, [])

  const ensureSessionStarted = useCallback(() => {
    if (!sessionStartRef.current) {
      sessionStartRef.current = performance.now()
      setSessionStarted(true)
    }
  }, [])

  const handleChange = (e) => setText(e.target.value)

  const handleKeyDown = (e) => {
    ensureSessionStarted()
    let keyType = 'char'
    if (e.key === 'Backspace') keyType = 'backspace'
    else if (e.key === 'Delete') keyType = 'delete'
    else if (e.key.length > 1) keyType = 'other'
    keystrokesRef.current.push({ t: now(), key_type: keyType })
  }

  const handlePaste = (e) => {
    ensureSessionStarted()
    const pastedText = e.clipboardData.getData('text')
    pastesRef.current.push({ t: now(), length: pastedText.length })
  }

  const handleClick = () => {
    clickCountRef.current += 1
  }

  const handleBlur = () => {
    if (!sessionStartRef.current) return
    lastBlurRef.current = now()
  }

  const handleFocus = () => {
    if (!sessionStartRef.current) return
    if (lastBlurRef.current !== null) {
      blursRef.current.push({ blur_t: lastBlurRef.current, focus_t: now() })
      lastBlurRef.current = null
    }
  }

  const getPayload = () => ({
    final_text: text,
    session_duration_ms: now(),
    keystrokes: keystrokesRef.current,
    pastes: pastesRef.current,
    blurs: blursRef.current,
    click_count: clickCountRef.current,
  })

  const reset = () => {
    setText('')
    setSessionStarted(false)
    sessionStartRef.current = null
    keystrokesRef.current = []
    pastesRef.current = []
    blursRef.current = []
    clickCountRef.current = 0
    lastBlurRef.current = null
  }

  return {
    text,
    sessionStarted,
    handlers: {
      onChange: handleChange,
      onKeyDown: handleKeyDown,
      onPaste: handlePaste,
      onClick: handleClick,
      onBlur: handleBlur,
      onFocus: handleFocus,
    },
    getPayload,
    reset,
  }
}
