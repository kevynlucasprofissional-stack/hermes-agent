import { useEffect, useState } from 'react'

declare global {
  interface Window {
    __hermesAiControlActive?: boolean
  }
}

/**
 * Visual indicator for AI control mode.
 *
 * Reads `window.__hermesAiControlActive` (set by Claude Code via CDP eval or
 * toggled locally via Ctrl+Shift+A). Polls every 500ms — simplicity over
 * perfect reactivity; the flag is a cooperative signal, not a security gate.
 *
 * Mounted in the main shell (contrib/controller.tsx). HUD and browser popout
 * windows intentionally omit it: AI control targets the primary workspace.
 */
export function AiControlBadge() {
  const [active, setActive] = useState(() => Boolean(window.__hermesAiControlActive))

  useEffect(() => {
    const id = setInterval(() => {
      setActive(Boolean(window.__hermesAiControlActive))
    }, 500)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'a') {
        event.preventDefault()
        window.__hermesAiControlActive = !window.__hermesAiControlActive
        setActive(window.__hermesAiControlActive)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  if (!active) return null

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed right-4 top-4 z-50 rounded bg-amber-500 px-2 py-1 font-mono text-xs text-white shadow-sm"
    >
      🤖 AI Control
    </div>
  )
}