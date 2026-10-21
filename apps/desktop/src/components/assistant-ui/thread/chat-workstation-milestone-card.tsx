import { MessagePrimitive } from '@assistant-ui/react'
import { useState } from 'react'

import type { WorkstationMilestone, WorkstationMilestoneStage } from '@/app/browser/types'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

export interface ChatWorkstationMilestoneCardProps {
  milestone: WorkstationMilestone
}

interface StageConfig {
  title: string
  icon: string
  badgeClass: string
  borderClass: string
}

const STAGE_CONFIGS: Record<WorkstationMilestoneStage, StageConfig> = {
  observed: {
    title: 'Demonstração observada',
    icon: 'eye',
    badgeClass: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    borderClass: 'border-purple-500/30'
  },
  candidate: {
    title: 'Candidata identificada',
    icon: 'lightbulb',
    badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    borderClass: 'border-amber-500/30'
  },
  compilation_started: {
    title: 'Compilação iniciada',
    icon: 'gear',
    badgeClass: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
    borderClass: 'border-sky-500/30'
  },
  validation_passed: {
    title: 'Validação aprovada',
    icon: 'pass',
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    borderClass: 'border-emerald-500/30'
  },
  validation_failed: {
    title: 'Validação recusada',
    icon: 'error',
    badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    borderClass: 'border-rose-500/30'
  },
  capability_selected: {
    title: 'Capacidade selecionada',
    icon: 'symbol-method',
    badgeClass: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    borderClass: 'border-cyan-500/30'
  },
  executed: {
    title: 'Capacidade executada',
    icon: 'play',
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    borderClass: 'border-emerald-500/30'
  },
  rejected: {
    title: 'Execução recusada',
    icon: 'stop',
    badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    borderClass: 'border-rose-500/30'
  }
}

export function ChatWorkstationMilestoneCard({ milestone }: ChatWorkstationMilestoneCardProps) {
  const [showEvidence, setShowEvidence] = useState(false)
  const config = STAGE_CONFIGS[milestone.stage] || {
    title: milestone.stage,
    icon: 'info',
    badgeClass: 'bg-muted text-muted-foreground border-border',
    borderClass: 'border-border'
  }

  const hasEvidence = Array.isArray(milestone.evidenceRefs) && milestone.evidenceRefs.length > 0

  return (
    <MessagePrimitive.Root
      className={cn(
        'flex w-full min-w-0 max-w-[44rem] flex-col self-center my-1.5 p-2.5 rounded-lg bg-(--ui-card-background) border text-xs shadow-xs transition-all',
        config.borderClass
      )}
      data-role="system"
      data-slot="aui_workstation-milestone-card"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span
            className={cn(
              'inline-flex items-center gap-1 text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border font-semibold',
              config.badgeClass
            )}
          >
            <Codicon name={config.icon} size="0.7rem" />
            {config.title}
          </span>
          {milestone.capabilityId && (
            <span className="font-mono text-[11px] text-(--ui-text-primary) truncate font-medium">
              {milestone.capabilityId}
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono text-(--ui-text-tertiary) shrink-0">
          {new Date(milestone.occurredAt).toLocaleTimeString()}
        </span>
      </div>

      {(milestone.reasonCode || milestone.taskRunId || milestone.learningSessionId) && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[11px] text-(--ui-text-secondary)">
          {milestone.reasonCode && (
            <span>
              Motivo: <span className="font-mono text-[10px] text-(--ui-text-primary)">{milestone.reasonCode}</span>
            </span>
          )}
          {milestone.taskRunId && (
            <span>
              TaskRun: <span className="font-mono text-[10px] text-(--ui-text-tertiary)">{milestone.taskRunId}</span>
            </span>
          )}
          {milestone.learningSessionId && (
            <span>
              Sessão: <span className="font-mono text-[10px] text-(--ui-text-tertiary)">{milestone.learningSessionId}</span>
            </span>
          )}
        </div>
      )}

      {hasEvidence && (
        <div className="mt-1.5 pt-1 border-t border-(--ui-stroke-tertiary)">
          <button
            className="flex items-center gap-1 text-[10px] text-(--ui-text-tertiary) hover:text-(--ui-text-secondary) font-mono"
            onClick={() => setShowEvidence(prev => !prev)}
            type="button"
          >
            <Codicon name={showEvidence ? 'chevron-down' : 'chevron-right'} size="0.65rem" />
            <span>Evidências ({milestone.evidenceRefs.length})</span>
          </button>
          {showEvidence && (
            <div className="mt-1 space-y-0.5 pl-3 border-l border-(--ui-stroke-tertiary)">
              {milestone.evidenceRefs.map((ref, i) => (
                <div className="font-mono text-[10px] text-(--ui-text-tertiary) truncate" key={i}>
                  {ref}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </MessagePrimitive.Root>
  )
}
