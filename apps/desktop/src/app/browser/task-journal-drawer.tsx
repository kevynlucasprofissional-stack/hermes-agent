import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

import type { TaskTimelineEvent } from './types'

export interface TaskJournalDrawerProps {
  taskId: string | null
  onClose: () => void
  className?: string
}

function kindIcon(kind: string): string {
  switch (kind) {
    case 'task_created':
      return 'rocket'

    case 'task_started':
      return 'play'

    case 'navigation':
      return 'globe'

    case 'action':
      return 'record'

    case 'approval_requested':
      return 'shield'

    case 'approval_resolved':
      return 'verified'

    case 'screenshot':
      return 'device-camera'

    case 'error':
      return 'error'

    case 'task_completed':
      return 'check'

    default:
      return 'history'
  }
}

function kindColor(kind: string, risk?: string): string {
  if (kind === 'error') {
    return 'border-red-500/40 text-red-400 bg-red-500/10'
  }

  if (kind === 'task_completed') {
    return 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
  }

  if (risk === 'high' || risk === 'critical') {
    return 'border-amber-500/40 text-amber-400 bg-amber-500/10'
  }

  if (kind === 'navigation') {
    return 'border-sky-500/30 text-sky-400 bg-sky-500/10'
  }

  return 'border-(--ui-stroke-tertiary) text-(--ui-text-tertiary) bg-(--ui-card-background)'
}

export function TaskJournalDrawer({ taskId, onClose, className }: TaskJournalDrawerProps) {
  const [events, setEvents] = useState<TaskTimelineEvent[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!taskId) {
      setEvents([])

      return
    }

    const bridge = window.hermesDesktop?.workstationBrowser

    if (!bridge?.getTaskJournal) {
      return
    }

    setLoading(true)
    bridge
      .getTaskJournal(taskId)
      .then(evs => setEvents(evs || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [taskId])

  if (!taskId) {
    return null
  }

  return (
    <div
      className={cn(
        'flex flex-col border-l border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) w-84 shrink-0 transition-all',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-(--ui-stroke-secondary) p-2.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 font-medium text-xs text-(--ui-text-primary)">
            <Codicon name="history" size="0.85rem" />
            <span>Execution Audit & Replay</span>
          </div>
          <div className="font-mono text-[10px] text-(--ui-text-tertiary) truncate" title={taskId}>
            {taskId}
          </div>
        </div>
        <Button onClick={onClose} size="icon-xs" title="Close Audit Drawer" variant="ghost">
          <Codicon name="close" size="0.75rem" />
        </Button>
      </div>

      {/* Timeline Content */}
      <div className="min-h-0 flex-1 overflow-y-auto p-2.5 space-y-2">
        {loading ? (
          <div className="py-8 text-center text-xs text-(--ui-text-tertiary)">Loading execution events…</div>
        ) : events.length === 0 ? (
          <div className="py-8 text-center text-xs text-(--ui-text-quaternary) italic">
            No journal events recorded for this task yet.
          </div>
        ) : (
          <div className="relative pl-3 border-l border-(--ui-stroke-tertiary) space-y-3">
            {events.map((ev, idx) => {
              const icon = kindIcon(ev.kind)
              const badgeStyle = kindColor(ev.kind, ev.risk)

              return (
                <div className="relative group text-left" key={ev.event_id || idx}>
                  {/* Timeline bullet */}
                  <span className="absolute -left-[17px] top-1 flex size-2.5 items-center justify-center rounded-full bg-(--ui-card-background) border border-(--ui-stroke-secondary) group-hover:border-emerald-500" />

                  <div className="rounded-md border border-(--ui-stroke-secondary) bg-(--ui-card-background) p-2 space-y-1">
                    <div className="flex items-center justify-between gap-1">
                      <span
                        className={cn('rounded px-1 py-0.5 text-[9px] font-mono font-medium uppercase', badgeStyle)}
                      >
                        <Codicon className="mr-0.5 inline" name={icon} size="0.65rem" />
                        {ev.kind.replace('_', ' ')}
                      </span>
                      {ev.elapsed_seconds !== undefined && ev.elapsed_seconds > 0 && (
                        <span className="font-mono text-[9px] text-(--ui-text-quaternary)">+{ev.elapsed_seconds}s</span>
                      )}
                    </div>

                    <p className="text-xs text-(--ui-text-primary) font-medium leading-snug">{ev.message}</p>

                    {ev.url && (
                      <div className="truncate font-mono text-[10px] text-sky-400/90" title={ev.url}>
                        {ev.url}
                      </div>
                    )}

                    {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                      <details className="mt-1 text-[10px] text-(--ui-text-tertiary)">
                        <summary className="cursor-pointer hover:text-(--ui-text-primary)">Details</summary>
                        <pre className="mt-0.5 max-h-24 overflow-auto rounded bg-black/20 p-1 font-mono text-[9px]">
                          {JSON.stringify(ev.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
