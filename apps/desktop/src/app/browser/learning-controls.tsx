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

interface QuestionCardProps {
  question: LearningQuestionItem
  actionBusy: boolean
  onAnswer: (action: 'confirm' | 'correct' | 'defer' | 'dismiss', correction?: string) => void
}

function LearningQuestionCard({ question, actionBusy, onAnswer }: QuestionCardProps) {
  const [isCorrecting, setIsCorrecting] = useState(false)
  const [correctionText, setCorrectionText] = useState('')

  return (
    <div className="mx-2 p-2.5 rounded-lg bg-sky-950/40 border border-sky-500/40 text-xs flex flex-col gap-2 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase bg-sky-500/20 text-sky-300 px-1.5 py-0.5 rounded">
          <Codicon name="question" size="0.7rem" />
          {question.kind}
        </span>
        <span className="text-[10px] font-mono text-(--ui-text-tertiary)">
          Incerteza: {Math.round(question.uncertainty * 100)}%
        </span>
      </div>

      <div className="text-(--ui-text-secondary) text-[11px] italic">
        Hipótese: {question.hypothesis}
      </div>

      <div className="text-(--ui-text-primary) font-medium text-xs">
        {question.proposedQuestion}
      </div>

      {isCorrecting ? (
        <div className="flex flex-col gap-1.5 mt-1">
          <input
            autoFocus
            className="w-full px-2 py-1 rounded bg-(--ui-background) border border-(--ui-stroke-secondary) text-xs text-(--ui-text-primary) placeholder:text-(--ui-text-tertiary)"
            onChange={e => setCorrectionText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && correctionText.trim()) {
                onAnswer('correct', correctionText.trim())
                setIsCorrecting(false)
                setCorrectionText('')
              }
            }}
            placeholder="Explique o motivo real ou ajuste correto..."
            type="text"
            value={correctionText}
          />
          <div className="flex items-center justify-end gap-1.5">
            <Button
              onClick={() => {
                setIsCorrecting(false)
                setCorrectionText('')
              }}
              size="xs"
              variant="ghost"
            >
              Cancelar
            </Button>
            <Button
              disabled={!correctionText.trim() || actionBusy}
              onClick={() => {
                onAnswer('correct', correctionText.trim())
                setIsCorrecting(false)
                setCorrectionText('')
              }}
              size="xs"
              variant="default"
            >
              Confirmar Correção
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 mt-1 pt-1 border-t border-sky-500/20">
          <Button
            disabled={actionBusy}
            onClick={() => onAnswer('confirm')}
            size="xs"
            variant="default"
          >
            <Codicon name="check" size="0.7rem" />
            Confirmar
          </Button>
          <Button
            disabled={actionBusy}
            onClick={() => {
              setIsCorrecting(true)
              setCorrectionText('')
            }}
            size="xs"
            variant="secondary"
          >
            <Codicon name="edit" size="0.7rem" />
            Corrigir
          </Button>
          <Button
            disabled={actionBusy}
            onClick={() => onAnswer('defer')}
            size="xs"
            variant="ghost"
          >
            Adiar
          </Button>
          <Button
            className="text-(--ui-text-tertiary) hover:text-(--ui-text-secondary) ml-auto"
            disabled={actionBusy}
            onClick={() => onAnswer('dismiss')}
            size="xs"
            variant="ghost"
          >
            Dispensar
          </Button>
        </div>
      )}
    </div>
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

  const activeQuestion: LearningQuestionItem | undefined =
    learningState?.pendingQuestions && learningState.pendingQuestions.length > 0
      ? learningState.pendingQuestions[0]
      : undefined

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {/* Learning Control Bar */}
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-1 bg-(--ui-sidebar-surface-background) border-b border-(--ui-stroke-tertiary) text-xs">
        <Button
          aria-label={isActive ? 'Parar Aprender' : 'Aprender'}
          disabled={busy || actionBusy || (!isActive && !activeTabId)}
          onClick={handleToggle}
          size="xs"
          variant={isActive ? 'destructive' : 'default'}
        >
          <Codicon name={isActive ? 'debug-stop' : 'record'} size="0.75rem" />
          <span>{isActive ? 'Parar Aprender' : 'Aprender'}</span>
        </Button>

        {isActive && (
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

            {/* Live Intensity Control */}
            <LearningIntensityBar
              currentIntensity={learningState?.intensity}
              disabled={actionBusy}
              onSelect={optKey => void handleSetIntensity(optKey)}
            />

            <span className="text-[10px] font-mono text-(--ui-text-tertiary) ml-auto">
              Eventos: {learningState?.eventsCount ?? 0} · Perguntas: {learningState?.questionsCount ?? 0}
            </span>

            <Button
              aria-label="Descartar Sessão de Aprendizagem"
              className="text-(--ui-text-tertiary) hover:text-rose-400 ml-1"
              disabled={actionBusy}
              onClick={handleDiscard}
              size="xs"
              variant="ghost"
            >
              <Codicon name="trash" size="0.75rem" />
              Descartar
            </Button>
          </>
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

      {/* Proactive Learning Question Card */}
      {activeQuestion && (
        <LearningQuestionCard
          actionBusy={actionBusy}
          onAnswer={(action, correction) => void handleAnswer(activeQuestion.id, action, correction)}
          question={activeQuestion}
        />
      )}
    </div>
  )
}
