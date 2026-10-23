import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { LearningControls } from '@/app/browser/learning-controls'
import { isNativeViewOccluded, useNativeViewOcclusion } from '@/app/browser/native-view-occlusion'
import { TaskJournalDrawer } from '@/app/browser/task-journal-drawer'
import type {
  LearningSessionState,
  WorkstationBrowserBounds,
  WorkstationBrowserState,
  WorkstationBrowserTabState
} from '@/app/browser/types'
import { useLearningChatBridge } from '@/app/chat/hooks/use-learning-chat-bridge'
import { isElementInHiddenPane, usePaneVisible } from '@/components/pane-shell/pane-visibility'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import { $activeSessionId, $selectedStoredSessionId, $sessions, conversationAliases } from '@/store/session'

interface NativeHumanReview {
  handoff_id: string
  task_id: string
  session_id: string
  run_id: string
  status: string
  reason: string
  requested_at: string
}

export interface WorkstationBrowserPaneProps {
  sessionId?: string
  onPopOut?: () => void
  className?: string
}

const EMPTY_STATE: WorkstationBrowserState = {
  runtime: 'electron-chromium',
  ready: false,
  attached: false,
  viewportHost: null,
  backgroundCapable: true,
  paused: false,
  controlOwner: 'agent',
  controlReady: false,
  profilePath: '',
  cacheBytes: null,
  activeTabId: null,
  tabs: [],
  tasks: [],
  downloads: [],
  lastError: null
}

function rectToBounds(rect: DOMRect): WorkstationBrowserBounds {
  return {
    x: Math.max(0, Math.round(rect.left)),
    y: Math.max(0, Math.round(rect.top)),
    width: Math.max(1, Math.round(rect.width)),
    height: Math.max(1, Math.round(rect.height))
  }
}

function shortTitle(tab: WorkstationBrowserTabState | null): string {
  if (!tab) {
    return 'Workstation Browser'
  }

  if (tab.title && tab.title !== 'New Tab') {
    return tab.title
  }

  if (!tab.url || tab.url === 'about:blank') {
    return 'Blank Page'
  }

  try {
    return new URL(tab.url).hostname || tab.url
  } catch {
    return tab.url
  }
}

function formatBrowserError(error: string): string {
  if (error === 'stale_or_unknown_ref') {
    return 'Element reference expired or was detached by page (stale_or_unknown_ref)'
  }

  if (error === 'element_not_visible') {
    return 'Element is not visible in current viewport (element_not_visible)'
  }

  if (error === 'element_unavailable') {
    return 'Element is unavailable for interaction (element_unavailable)'
  }

  return error
}

// health: allow CC -- HWH-OVERLAY-01 session-bound occlusion coordination and native human review handling
export function WorkstationBrowserPane({ sessionId, onPopOut, className }: WorkstationBrowserPaneProps) {
  const bridge = window.hermesDesktop?.workstationBrowser
  const [state, setState] = useState<WorkstationBrowserState>(EMPTY_STATE)
  const [runtimeDiscovered, setRuntimeDiscovered] = useState(false)
  const [busy, setBusy] = useState(false)
  const [showJournal, setShowJournal] = useState(false)
  const [nativeReviews, setNativeReviews] = useState<NativeHumanReview[]>([])
  const [reviewBusy, setReviewBusy] = useState(false)
  const [reviewNotice, setReviewNotice] = useState('')
  const [learningState, setLearningState] = useState<LearningSessionState | null>(null)

  useEffect(() => {
    if (!bridge?.onLearningState) {return}
    bridge.learningStatus?.().then(status => setLearningState(status)).catch(() => undefined)
    const cleanup = bridge.onLearningState(state => setLearningState(state))

    return cleanup
  }, [bridge])

  const hostRef = useRef<HTMLDivElement | null>(null)
  const paneVisible = usePaneVisible()

  const selectedStoredSessionId = useStore($selectedStoredSessionId)
  const activeSessionId = useStore($activeSessionId)
  const sessions = useStore($sessions)

  const activeSessionKey = sessionId ?? selectedStoredSessionId ?? activeSessionId ?? null

  // Bridge learning questions and milestones into the chat transcript.
  // Only active when this pane is bound to a stored session so questions
  // never leak across unrelated conversations.
  useLearningChatBridge({
    bridge,
    runtimeSessionId: activeSessionKey,
    storedSessionId: selectedStoredSessionId
  })

  const activeSessionAliases = useMemo(() => {
    if (!activeSessionKey) {
      return []
    }

    return conversationAliases(activeSessionKey, sessions)
  }, [activeSessionKey, sessions])

  // Only the authenticated LOCAL backend may expose the canonical reviews of
  // the selected session. Never mix gateway/connection reviews with this native Browser.
  useEffect(() => {
    const api = window.hermesDesktop?.api

    if (!bridge || !api || activeSessionAliases.length === 0) {
      setNativeReviews([])

      return
    }

    let disposed = false
    setNativeReviews([])
    setReviewNotice('')

    const refresh = async () => {
      try {
        // Stored chat IDs and canonical conversation/root IDs can differ.
        // Query only aliases of the actively selected conversation, never all sessions.
        const results = await Promise.allSettled(activeSessionAliases.map(sessionId =>
          api<{ handoffs: NativeHumanReview[] }>({
            path: `/api/workstation/handoffs?session_id=${encodeURIComponent(sessionId)}`,
            connectionId: 'local'
          })
        ))

        if (!disposed) {
          const seen = new Set<string>()
          const reviews = results.flatMap(result => result.status === 'fulfilled' ? (result.value?.handoffs ?? []) : [])
          setNativeReviews(reviews.filter(review => {
            if (!activeSessionAliases.includes(review.session_id) || review.status !== 'waiting-for-human' || seen.has(review.handoff_id)) {return false}
            seen.add(review.handoff_id)

            return true
          }))
        }
      } catch {
        if (!disposed) {setNativeReviews([])}
      }
    }

    void refresh()
    const poll = window.setInterval(() => void refresh(), 5000)

    return () => {
      disposed = true
      window.clearInterval(poll)
    }
  }, [bridge, activeSessionAliases])

  const acknowledgeNativeReview = useCallback(async (review: NativeHumanReview) => {
    if (reviewBusy || !activeSessionAliases.includes(review.session_id)) {return}
    setReviewBusy(true)
    setReviewNotice('')

    try {
      const result = await window.hermesDesktop.api<{ status: string; readback_required: boolean }>({
        path: `/api/workstation/handoffs/${encodeURIComponent(review.handoff_id)}/review`,
        method: 'POST',
        body: { session_id: review.session_id, run_id: review.run_id },
        connectionId: 'local'
      })

      if (result.status !== 'ready' || result.readback_required !== true) {
        throw new Error('Review was not accepted')
      }

      setNativeReviews(current => current.filter(item => item.handoff_id !== review.handoff_id))
      setReviewNotice('Review acknowledged. Independent readback is required before work can continue.')
    } catch {
      setReviewNotice('Review could not be accepted. Recheck session and TaskRun authority.')
    } finally {
      setReviewBusy(false)
    }
  }, [activeSessionAliases, reviewBusy])

  const preferredTaskId = useMemo(() => {
    if (activeSessionAliases.length === 0 || !state.tasks || state.tasks.length === 0) {
      return null
    }

    const matched = state.tasks.find(task => {
      if (!task.sessionHost) {
        return false
      }

      return activeSessionAliases.includes(task.sessionHost)
    })

    return matched?.taskId ?? null
  }, [activeSessionAliases, state.tasks])

  const activeTab = useMemo(
    () => state.tabs.find(tab => tab.id === state.activeTabId) ?? state.tabs[0] ?? null,
    [state.activeTabId, state.tabs]
  )

  const backgroundTaskCount = useMemo(() => {
    if (!state.tasks) {return 0}

    return state.tasks.filter(
      task => task.taskId !== preferredTaskId && (task.status === 'parked' || task.status === 'hidden')
    ).length
  }, [state.tasks, preferredTaskId])

  const run = useCallback(
    async (fn: () => Promise<WorkstationBrowserState>) => {
      if (!bridge) {
        return
      }

      try {
        setBusy(true)
        setState(await fn())
      } finally {
        setBusy(false)
      }
    },
    [bridge]
  )

  const boundOwnerIdRef = useRef<string | null>(activeSessionKey ?? preferredTaskId ?? null)

  const lastAttachedRef = useRef<{
    host: 'chat'
    sessionKey: string | null
    preferredTaskId: string | null
  } | null>(null)

  const wasPaneVisibleRef = useRef(false)

  const publishBounds = useCallback(
    async (attach = false) => {
      if (!bridge || !hostRef.current || !paneVisible || isElementInHiddenPane(hostRef.current)) {
        return
      }

      const rect = hostRef.current.getBoundingClientRect()

      if (rect.width < 1 || rect.height < 1) {
        return
      }

      const bounds = rectToBounds(rect)
      const ownerId = activeSessionKey ?? preferredTaskId ?? undefined

      if (ownerId) {
        boundOwnerIdRef.current = ownerId
      }

      const currentKey = {
        host: 'chat' as const,
        sessionKey: activeSessionKey,
        preferredTaskId: preferredTaskId ?? null
      }

      const last = lastAttachedRef.current

      const keyMismatch =
        !last ||
        last.host !== currentKey.host ||
        last.sessionKey !== currentKey.sessionKey ||
        last.preferredTaskId !== currentKey.preferredTaskId

      if (attach || keyMismatch) {
        lastAttachedRef.current = currentKey
        const visible = paneVisible && !isNativeViewOccluded(document)
        setState(await bridge.attach(bounds, 'chat', preferredTaskId ?? undefined, ownerId, visible))
      } else {
        setState(await bridge.setBounds(bounds, 'chat', ownerId))
      }
    },
    [activeSessionKey, bridge, paneVisible, preferredTaskId]
  )

  // eslint-disable-next-line no-restricted-syntax -- cleanup last attached key on unmount
  useEffect(() => {
    if (!bridge) {
      return
    }

    let disposed = false
    setRuntimeDiscovered(false)

    const off = bridge.onState(next => {
      if (!disposed) {
        setState(next)
      }
    })

    void bridge
      .ensure()
      .then(next => {
        if (!disposed) {
          setState(next)
          setRuntimeDiscovered(true)
        }
      })
      .catch(error => {
        if (!disposed) {
          setState(current => ({ ...current, lastError: String(error) }))
        }
      })

    return () => {
      disposed = true
      off()
      lastAttachedRef.current = null
      void bridge.detach('chat', boundOwnerIdRef.current ?? undefined)
    }
  }, [bridge])

  // eslint-disable-next-line no-restricted-syntax -- cache last attached key to prevent viewport stealing
  useEffect(() => {
    if (!bridge || !hostRef.current || !runtimeDiscovered) {
      return
    }

    // Keep-alive panes retain layout bounds while hidden. Never let an
    // inactive session annex the OS-level Chromium child view.
    if (!paneVisible || isElementInHiddenPane(hostRef.current)) {
      wasPaneVisibleRef.current = false

      return
    }

    const becameVisible = !wasPaneVisibleRef.current
    wasPaneVisibleRef.current = true

    const currentKey = {
      host: 'chat' as const,
      sessionKey: activeSessionKey,
      preferredTaskId: preferredTaskId ?? null
    }

    const last = lastAttachedRef.current

    const keyChanged =
      !last ||
      last.host !== currentKey.host ||
      last.sessionKey !== currentKey.sessionKey ||
      last.preferredTaskId !== currentKey.preferredTaskId

    // A deliberate Hub transfer changes viewportHost while this pane may stay
    // mounted for a render. Do not steal the viewport back. Reattach only for
    // new conversation ownership, or when Chat itself lost its attachment.
    const chatNeedsReattach = !state.attached && (state.viewportHost === null || state.viewportHost === 'chat')

    if (becameVisible || keyChanged || chatNeedsReattach) {
      lastAttachedRef.current = currentKey
      void publishBounds(true)
    }
  }, [activeSessionKey, preferredTaskId, bridge, paneVisible, publishBounds, runtimeDiscovered, state.attached, state.viewportHost])

  useEffect(() => {
    if (!bridge || !hostRef.current) {
      return
    }

    let frame = 0

    const schedule = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => void publishBounds(false))
    }

    const observer = new ResizeObserver(schedule)
    observer.observe(hostRef.current)
    window.addEventListener('resize', schedule)
    window.addEventListener('transitionend', schedule)

    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('resize', schedule)
      window.removeEventListener('transitionend', schedule)
    }
  }, [bridge, publishBounds])

  if (paneVisible) {
    const currentOwner = activeSessionKey ?? preferredTaskId ?? null

    if (currentOwner) {
      boundOwnerIdRef.current = currentOwner
    }
  }

  const effectiveOwnerId =
    (paneVisible
      ? activeSessionKey || preferredTaskId
      : boundOwnerIdRef.current || activeSessionKey || preferredTaskId) || undefined

  useNativeViewOcclusion(bridge, 'chat', { enabled: paneVisible, ownerId: effectiveOwnerId })

  const transferToChat = useCallback(async () => {
    if (!bridge || !hostRef.current) {
      return
    }

    const rect = hostRef.current.getBoundingClientRect()

    if (rect.width < 1 || rect.height < 1) {
      return
    }

    const bounds = rectToBounds(rect)
    setState(await bridge.transferViewport('chat', bounds))
  }, [bridge])

  if (!bridge) {
    return (
      <div
        className={cn('grid h-full place-items-center p-4 text-center text-xs text-(--ui-text-secondary)', className)}
      >
        Workstation Browser bridge is not available.
      </div>
    )
  }

  const isAttachedHere = state.attached && state.viewportHost === 'chat'
  const isAttachedElsewhere = state.attached && state.viewportHost !== 'chat'

  return (
    <div className={cn('flex h-full flex-col overflow-hidden bg-(--ui-main-surface-background)', className)}>
      <div className="flex h-9 shrink-0 items-center justify-between gap-1.5 border-b border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) px-2">
        <div className="flex items-center gap-1">
          <Button
            aria-label="Back"
            disabled={!activeTab?.canGoBack || busy}
            onClick={() => void run(() => bridge.back())}
            size="icon-xs"
            variant="ghost"
          >
            <Codicon name="arrow-left" size="0.75rem" />
          </Button>
          <Button
            aria-label="Forward"
            disabled={!activeTab?.canGoForward || busy}
            onClick={() => void run(() => bridge.forward())}
            size="icon-xs"
            variant="ghost"
          >
            <Codicon name="arrow-right" size="0.75rem" />
          </Button>
          <Button
            aria-label={activeTab?.loading ? 'Stop' : 'Reload'}
            onClick={() => void run(() => (activeTab?.loading ? bridge.stop() : bridge.reload()))}
            size="icon-xs"
            variant="ghost"
          >
            <Codicon name={activeTab?.loading ? 'debug-stop' : 'refresh'} size="0.75rem" />
          </Button>
        </div>

        <div className="min-w-0 flex-1 truncate px-1 text-center font-mono text-[11px] text-(--ui-text-secondary) flex items-center justify-center gap-1.5">
          {busy && <span className="size-1.5 shrink-0 rounded-full bg-amber-400 animate-pulse" title="Action in progress" />}
          <span className="truncate">{shortTitle(activeTab)}</span>
        </div>

        <div className="flex items-center gap-1">
          {backgroundTaskCount > 0 && (
            <span
              className="rounded-full bg-(--ui-sidebar-surface-background) border border-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] font-mono text-(--ui-text-tertiary)"
              title={`${backgroundTaskCount} background browser task(s) running`}
            >
              ⚡{backgroundTaskCount}
            </span>
          )}

          <span
            className={cn(
              'rounded-full px-1.5 py-0.5 text-[9px] font-medium uppercase',
              state.paused
                ? 'bg-amber-500/20 text-amber-400'
                : state.controlOwner === 'human'
                  ? 'bg-sky-500/20 text-sky-400'
                  : 'bg-emerald-500/20 text-emerald-400'
            )}
            title={`Control: ${state.controlOwner}`}
          >
            {state.paused ? 'Paused' : state.controlOwner}
          </span>

          {state.controlOwner === 'human' ? (
            <Button
              aria-label="Release Human Control"
              className="text-sky-400 hover:text-sky-300"
              onClick={() => void run(() => bridge.releaseControl(preferredTaskId ?? undefined))}
              size="icon-xs"
              variant="ghost"
            >
              <Codicon name="robot" size="0.75rem" />
            </Button>
          ) : (
            <Button
              aria-label="Take Human Control"
              className="text-(--ui-text-tertiary) hover:text-(--ui-text-primary)"
              onClick={() => void run(() => bridge.takeControl(preferredTaskId ?? undefined, activeSessionKey ?? undefined))}
              size="icon-xs"
              variant="ghost"
            >
              <Codicon name="person" size="0.75rem" />
            </Button>
          )}

          {preferredTaskId && (
            <Button
              aria-label="Toggle Execution History"
              onClick={() => setShowJournal(prev => !prev)}
              size="icon-xs"
              variant={showJournal ? 'secondary' : 'ghost'}
            >
              <Codicon name="history" size="0.75rem" />
            </Button>
          )}

          {onPopOut && (
            <Button
              aria-label="Pop out to Browser Hub"
              onClick={onPopOut}
              size="icon-xs"
              variant="ghost"
            >
              <Codicon name="link-external" size="0.75rem" />
            </Button>
          )}
        </div>
      </div>

      {(activeTab?.loading || busy) && (
        <div className="h-0.5 w-full bg-emerald-500/20 overflow-hidden">
          <div className="h-full bg-emerald-500 animate-pulse w-full" />
        </div>
      )}

      {state.controlOwner === 'human' && (
        <div className="flex items-center justify-between gap-2 border-b border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs text-sky-300">
          <span>Human control active. Agent actions safely paused.</span>
          <Button
            onClick={() => void run(() => bridge.releaseControl(preferredTaskId ?? undefined))}
            size="xs"
            variant="secondary"
          >
            Release to Agent
          </Button>
        </div>
      )}

      {nativeReviews.map(review => (
        <div className="flex items-center justify-between gap-2 border-b border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200" key={review.handoff_id}>
          <span>Uncertain Browser operation for this session. Review the effect; approval never retries the mutation.</span>
          <Button
            aria-label="Acknowledge uncertain Browser operation"
            disabled={reviewBusy}
            onClick={() => void acknowledgeNativeReview(review)}
            size="xs"
            variant="secondary"
          >
            I reviewed ? require readback
          </Button>
        </div>
      ))}
      {reviewNotice && (
        <div className="border-b border-amber-500/20 px-3 py-1 text-xs text-amber-200" role="status">
          {reviewNotice}
        </div>
      )}

      {isAttachedElsewhere && (
        <div className="flex items-center justify-between gap-2 border-b border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">
          <span>Viewport active in Browser Hub ({state.viewportHost})</span>
          <Button onClick={() => void transferToChat()} size="xs" variant="secondary">
            Bring to Chat
          </Button>
        </div>
      )}

      {state.lastError && (
        <div className="flex items-center justify-between gap-2 border-b border-red-500/30 bg-red-500/10 px-3 py-1 text-xs text-red-300">
          <span className="truncate" title={state.lastError}>
            {formatBrowserError(state.lastError)}
          </span>
          <button
            aria-label="Dismiss error"
            className="ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] text-red-300/80 hover:bg-red-500/20 hover:text-white"
            onClick={() => void bridge?.clearError?.()}
            type="button"
          >
            ✕
          </button>
        </div>
      )}

      <LearningControls
        activeTabId={state.activeTabId}
        bridge={bridge}
        busy={busy}
        learningState={learningState}
        sessionId={activeSessionKey}
      />

      <div className="relative min-h-0 flex-1 bg-black">
        <div className="absolute inset-0" ref={hostRef} />
        {!state.ready && (
          <div className="absolute inset-0 grid place-items-center text-xs text-(--ui-text-tertiary)">
            Starting Workstation Browser…
          </div>
        )}
        {showJournal && preferredTaskId && (
          <TaskJournalDrawer
            className="absolute inset-y-0 right-0 z-20 w-80 shadow-2xl border-l border-(--ui-stroke-secondary)"
            onClose={() => setShowJournal(false)}
            taskId={preferredTaskId}
          />
        )}
      </div>
    </div>
  )
}
