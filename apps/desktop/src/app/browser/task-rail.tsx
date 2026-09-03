import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

import type { BrowserTask } from './types'

export interface TaskRailProps {
  tasks: BrowserTask[]
  activeTaskId?: string | null
  onSelectTask?: (task: BrowserTask) => void
  onParkTask?: (taskId: string) => void
  onHideTask?: (taskId: string) => void
  onDestroyTask?: (taskId: string) => void
  onClearParked?: () => void
  className?: string
}

interface TaskGroup {
  id: 'active' | 'waiting-for-human' | 'background' | 'recent'
  title: string
  icon: string
  tasks: BrowserTask[]
}

function statusBadge(task: BrowserTask) {
  switch (task.status) {
    case 'visible':
      return {
        label: 'Visible',
        color: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
      }
    case 'parked':
      return {
        label: 'Parked',
        color: 'border-amber-500/30 text-amber-400 bg-amber-500/10'
      }
    case 'hidden':
      return {
        label: 'Background',
        color: 'border-sky-500/30 text-sky-400 bg-sky-500/10'
      }
    default:
      return {
        label: task.status,
        color: 'border-(--ui-stroke-tertiary) text-(--ui-text-tertiary)'
      }
  }
}

export function TaskRail({
  tasks,
  activeTaskId,
  onSelectTask,
  onParkTask,
  onHideTask,
  onDestroyTask,
  onClearParked,
  className
}: TaskRailProps) {
  const [collapsed, setCollapsed] = useState(false)

  const groups: TaskGroup[] = useMemo(() => {
    const active: BrowserTask[] = []
    const waiting: BrowserTask[] = []
    const background: BrowserTask[] = []
    const recent: BrowserTask[] = []

    for (const task of tasks) {
      if (task.status === 'visible') {
        active.push(task)
      } else if (task.status === 'parked') {
        background.push(task)
      } else if (task.sessionHost?.includes('waiting') || task.leaseState === 'waiting') {
        waiting.push(task)
      } else {
        recent.push(task)
      }
    }

    return [
      { id: 'active', title: 'Active', icon: 'eye', tasks: active },
      { id: 'waiting-for-human', title: 'Waiting for Human', icon: 'person', tasks: waiting },
      { id: 'background', title: 'Background', icon: 'history', tasks: background },
      { id: 'recent', title: 'Recent', icon: 'check-all', tasks: recent }
    ]
  }, [tasks])

  if (collapsed) {
    return (
      <div className={cn('flex flex-col items-center border-r border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) p-1.5', className)}>
        <Button
          aria-label="Expand Task Rail"
          onClick={() => setCollapsed(false)}
          size="icon-xs"
          title="Expand Task Rail"
          variant="ghost"
        >
          <Codicon name="layout-sidebar-left-off" size="0.75rem" />
        </Button>
        <span className="mt-2 text-[10px] text-(--ui-text-tertiary) [writing-mode:vertical-lr]">Tasks ({tasks.length})</span>
      </div>
    )
  }

  return (
    <aside
      aria-label="Browser Task Rail"
      className={cn(
        'flex w-64 shrink-0 flex-col border-r border-(--ui-stroke-secondary) bg-(--ui-sidebar-surface-background) text-xs',
        className
      )}
    >
      <div className="flex h-9 items-center justify-between border-b border-(--ui-stroke-tertiary) px-2.5">
        <span className="font-semibold text-(--ui-text-secondary)">Task Rail ({tasks.length})</span>
        <div className="flex items-center gap-1">
          {tasks.some(t => t.status === 'parked' || t.status === 'hidden') && onClearParked && (
            <Button
              aria-label="Clear Parked Tasks"
              className="h-6 px-1.5 text-[10px] text-(--ui-text-tertiary) hover:bg-red-500/10 hover:text-red-300"
              onClick={onClearParked}
              size="xs"
              title="Clear all parked/inactive tasks"
              variant="ghost"
            >
              <Codicon name="clear-all" size="0.7rem" />
              Clear
            </Button>
          )}
          <Button
            aria-label="Collapse Task Rail"
            onClick={() => setCollapsed(true)}
            size="icon-xs"
            title="Collapse Task Rail"
            variant="ghost"
          >
            <Codicon name="layout-sidebar-left" size="0.75rem" />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2 space-y-3">
        {groups.map(group => (
          <div key={group.id} className="space-y-1">
            <div className="flex items-center gap-1 px-1 text-[11px] font-medium text-(--ui-text-tertiary)">
              <Codicon name={group.icon} size="0.7rem" />
              <span>{group.title}</span>
              <span className="ml-auto font-mono text-[10px] text-(--ui-text-quaternary)">
                {group.tasks.length}
              </span>
            </div>

            {group.tasks.length === 0 ? (
              <p className="px-2 py-1 text-[10px] italic text-(--ui-text-quaternary)">No {group.title.toLowerCase()} tasks</p>
            ) : (
              <div className="space-y-1">
                {group.tasks.map(task => {
                  const badge = statusBadge(task)
                  const isCurrent = task.taskId === activeTaskId

                  return (
                    <div
                      key={task.taskId}
                      className={cn(
                        'group rounded-md border p-2 text-left transition-colors',
                        isCurrent
                          ? 'border-(--ui-stroke-primary) bg-(--ui-main-surface-background)'
                          : 'border-(--ui-stroke-secondary) bg-(--ui-card-background) hover:border-(--ui-stroke-tertiary)'
                      )}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-mono font-medium text-(--ui-text-primary) truncate" title={task.taskId}>
                          {task.taskId}
                        </span>
                        <span className={cn('rounded px-1 py-0.5 text-[9px] font-medium uppercase', badge.color)}>
                          {badge.label}
                        </span>
                      </div>

                      <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-(--ui-text-quaternary)">
                        {task.kanbanCardId && (
                          <span className="rounded bg-black/10 px-1 py-0.2" title={`Kanban Card: ${task.kanbanCardId}`}>
                            Card #{task.kanbanCardId.slice(0, 8)}
                          </span>
                        )}
                        {task.runId && (
                          <span className="rounded bg-black/10 px-1 py-0.2" title={`Run ID: ${task.runId}`}>
                            Run #{task.runId.slice(0, 6)}
                          </span>
                        )}
                      </div>

                      <div className="mt-2 flex items-center gap-1 border-t border-(--ui-stroke-tertiary) pt-1.5 opacity-80 group-hover:opacity-100">
                        <Button
                          onClick={() => onSelectTask?.(task)}
                          size="xs"
                          variant={isCurrent ? 'secondary' : 'ghost'}
                        >
                          <Codicon name="eye" size="0.7rem" />
                          Show
                        </Button>
                        {task.status !== 'parked' && (
                          <Button
                            onClick={() => onParkTask?.(task.taskId)}
                            size="xs"
                            variant="ghost"
                          >
                            <Codicon name="archive" size="0.7rem" />
                            Park
                          </Button>
                        )}
                        {task.status === 'visible' && (
                          <Button
                            onClick={() => onHideTask?.(task.taskId)}
                            size="xs"
                            variant="ghost"
                          >
                            <Codicon name="eye-closed" size="0.7rem" />
                            Hide
                          </Button>
                        )}
                        {onDestroyTask && (
                          <Button
                            className="ml-auto text-red-400 hover:bg-red-500/10 hover:text-red-300"
                            onClick={() => onDestroyTask(task.taskId)}
                            size="xs"
                            title="Close and delete task"
                            variant="ghost"
                          >
                            <Codicon name="trash" size="0.7rem" />
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}
