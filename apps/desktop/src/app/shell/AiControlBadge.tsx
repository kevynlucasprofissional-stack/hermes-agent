import { useEffect, useState } from 'react'

declare global {
  interface Window {
    __hermesAiControlActive?: boolean
  }
}

/**
 * AI Control is owned by Electron's native shortcut (Ctrl+Shift+A).
 * This indicator mirrors the main-process authorization; setting the legacy
 * JS flag does not grant a token or enable the local control bridge.
 */
export function AiControlBadge() {
  const [active, setActive] = useState(false)

  useEffect(() => {
    const bridge = window.hermesDesktop?.aiControl
    if (!bridge) return
    let mounted = true
    let receivedPush = false
    const unsubscribe = bridge.onStatus(enabled => {
      receivedPush = true
      if (mounted) setActive(enabled)
    })
    void bridge.getStatus().then(enabled => {
      if (mounted && !receivedPush) setActive(enabled)
    }).catch(() => {
      if (mounted && !receivedPush) setActive(false)
    })
    return () => {
      mounted = false
      unsubscribe()
    }
  }, [])

  useEffect(() => {
    // Compatibility for existing navigation scripts. Not an authority source.
    window.__hermesAiControlActive = active
    return () => { window.__hermesAiControlActive = false }
  }, [active])

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
