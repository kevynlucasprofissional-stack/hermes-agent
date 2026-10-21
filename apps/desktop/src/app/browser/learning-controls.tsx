import { useCallback, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

import type {
  LearningIntensity,
  LearningQuestionItem,
  LearningSessionState,
  WorkstationBrowserBridge
} from './types'

export interface LearningControlsProps {
  bridge?: WorkstationBrowserBridge
  learningState: LearningSessionState | null
  activeTabId?: string | null
  sessionId?: string | null
  onStartLearning?: () => void
  busy?: boolean
}

const INTENSITY_OPTIONS: Array<{ key: LearningIntensity; label: string; desc: string }> = [
  { key: 'discreto', label: 'Discreto', desc: 'Max 1 pergunta/5min (cooldown 4m)' },
  { key: 'equilibrado', label: 'Equilibrado', desc: 'Max 2 perguntas/5min (cooldown 1m45s)' },
  { key: 'intensivo', label: 'Intensivo', desc: 'Max 4 perguntas/5min (cooldown 40s)' }
]

interface IntensityBarProps {
  currentIntensity?: LearningIntensity
  disabled?: boolean
  onSelect: (intensity: LearningIntensity) => void
}

function LearningIntensityBar({ currentIntensity, disabled, onSelect }: IntensityBarProps) {
  return (
    <div className="flex items-center gap-0.5 ml-1 border border-(--ui-stroke-tertiary) rounded bg-(--ui-background) p-0.5">
      <span className="text-[10px] text-(--ui-text-tertiary) px-1 font-mono">Intensidade:</span>
      {INTENSITY_OPTIONS.map(opt => {
        const selected = currentIntensity === opt.key

        return (
          <button
            className={cn(
              'px-1.5 py-0.5 text-[10px] rounded transition-colors font-medium',
              selected
                ? 'bg-(--ui-stroke-tertiary) text-(--ui-text-primary) font-semibold shadow-xs'
                : 'text-(--ui-text-tertiary) hover:text-(--ui-text-secondary)'
            )}
            disabled={disabled}
            key={opt.key}
            onClick={() => onSelect(opt.key)}
            title={opt.desc}
            type="button"
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

interface NoChatNoticeProps {
  question: LearningQuestionItem
  actionBusy: boolean
  onAnswer: (questionId: string, action: 'confirm' | 'defer') => void
}

function LearningNoChatNotice({ question, actionBusy, onAnswer }: NoChatNoticeProps) {
  return (
    <div
      className="mx-2 px-2 py-1.5 rounded bg-sky-950/30 border border-sky-500/30 text-xs flex items-center justify-between gap-2 text-sky-200"
      data-testid="learning-no-chat-notice"
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <Codicon className="text-sky-400 shrink-0" name="question" size="0.75rem" />
        <span className="truncate">
          Dúvida: <strong className="text-sky-100">{question.proposedQuestion}</strong>
        </span>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          disabled={actionBusy}
          onClick={() => onAnswer(question.id, 'confirm')}
          size="xs"
          variant="default"
        >
          Confirmar
        </Button>
        <Button
          disabled={actionBusy}
          onClick={() => onAnswer(question.id, 'defer')}
          size="xs"
          variant="ghost"
        >
          Adiar
        </Button>
      </div>
    </div>
  )
}

interface ActiveBarProps {
  isLearning: boolean
  intensity?: LearningIntensity
  disabled: boolean
  eventsCount?: number
  questionsCount?: number
  onSetIntensity: (intensity: LearningIntensity) => void
  onDiscard: () => void
}

function LearningActiveBar({
  isLearning,
  intensity,
  disabled,
  eventsCount,
  questionsCount,
  onSetIntensity,
  onDiscard
}: ActiveBarProps) {
  return (
    <>
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider',
          isLearning
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
        )}
      >
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            isLearning ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
          )}
        />
        {isLearning ? 'Aprendendo' : 'Pausado'}
      </span>

      <LearningIntensityBar
        currentIntensity={intensity}
        disabled={disabled}
        onSelect={onSetIntensity}
      />

      <span className="text-[10px] font-mono text-(--ui-text-tertiary) ml-auto">
        Eventos: {eventsCount ?? 0} · Perguntas: {questionsCount ?? 0}
      </span>

      <Button
        aria-label="Descartar Sessão de Aprendizagem"
        className="text-(--ui-text-tertiary) hover:text-rose-400 ml-1"
        disabled={disabled}
        onClick={onDiscard}
        size="xs"
        variant="ghost"
      >
        <Codicon name="trash" size="0.75rem" />
        Descartar
      </Button>
    </>
  )
}

export function LearningControls({
  bridge,
  learningState,
  activeTabId,
  sessionId,
  onStartLearning,
  busy = false
}: LearningControlsProps) {
  const [actionBusy, setActionBusy] = useState(false)

  const isLearning = learningState?.status === 'learning'
  const isPaused = learningState?.status === 'paused'
  const isActive = isLearning || isPaused

  const handleToggle = useCallback(async () => {
    if (!bridge || actionBusy) {return}
    setActionBusy(true)

    try {
      if (isActive) {
        await bridge.learningStop()
      } else if (onStartLearning) {
        onStartLearning()
      } else {
        await bridge.learningStart(activeTabId ?? undefined, sessionId ?? undefined)
      }
    } finally {
      setActionBusy(false)
    }
  }, [bridge, actionBusy, isActive, onStartLearning, activeTabId, sessionId])

  const handleDiscard = useCallback(async () => {
    if (!bridge || actionBusy) {return}
    setActionBusy(true)

    try {
      await bridge.learningDiscard()
    } finally {
      setActionBusy(false)
    }
  }, [bridge, actionBusy])

  const handleSetIntensity = useCallback(async (newIntensity: LearningIntensity) => {
    if (!bridge || actionBusy) {return}
    setActionBusy(true)

    try {
      await bridge.learningSetIntensity(newIntensity)
    } finally {
      setActionBusy(false)
    }
  }, [bridge, actionBusy])

  const handleAnswer = useCallback(async (
    questionId: string,
    action: 'confirm' | 'correct' | 'defer' | 'dismiss',
    correction?: string
  ) => {
    if (!bridge || actionBusy) {return}
    setActionBusy(true)

    try {
      await bridge.learningAnswerQuestion(questionId, action, correction)
    } finally {
      setActionBusy(false)
    }
  }, [bridge, actionBusy])

  const activeQuestion = learningState?.pendingQuestions?.[0]
  const isToggleDisabled = busy || actionBusy || (!isActive && !activeTabId)

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {/* Learning Control Bar */}
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-1 bg-(--ui-sidebar-surface-background) border-b border-(--ui-stroke-tertiary) text-xs">
        <Button
          aria-label={isActive ? 'Parar Aprender' : 'Aprender'}
          disabled={isToggleDisabled}
          onClick={handleToggle}
          size="xs"
          variant={isActive ? 'destructive' : 'default'}
        >
          <Codicon name={isActive ? 'debug-stop' : 'record'} size="0.75rem" />
          <span>{isActive ? 'Parar Aprender' : 'Aprender'}</span>
        </Button>

        {isActive && (
          <LearningActiveBar
            disabled={actionBusy}
            eventsCount={learningState?.eventsCount}
            intensity={learningState?.intensity}
            isLearning={isLearning}
            onDiscard={handleDiscard}
            onSetIntensity={optKey => void handleSetIntensity(optKey)}
            questionsCount={learningState?.questionsCount}
          />
        )}
      </div>

      {/* Notice on pause (auth page or off-origin) */}
      {isPaused && learningState?.lastError && (
        <div className="mx-2 p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <Codicon className="text-amber-400 shrink-0" name="warning" />
            <span>{learningState.lastError}</span>
          </div>
        </div>
      )}

      {/* When no chat session is connected, maintain pending questions non-intrusively without covering canvas */}
      {!sessionId && activeQuestion && (
        <LearningNoChatNotice
          actionBusy={actionBusy}
          onAnswer={(id, action) => void handleAnswer(id, action)}
          question={activeQuestion}
        />
      )}
    </div>
  )
}
