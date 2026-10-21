import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import type { LearningQuestionItem, WorkstationBrowserBridge } from '@/app/browser/types'

export interface LearningQuestionChatCardProps {
  question: LearningQuestionItem
  bridge?: WorkstationBrowserBridge
}

/**
 * Renders a learning question inside the chat transcript as an interactive
 * system message. Answers are persisted through the existing
 * `learningAnswerQuestion` IPC channel so the recorder's JSONL stays
 * authoritative.
 */
export function LearningQuestionChatCard({ question, bridge }: LearningQuestionChatCardProps) {
  const [isCorrecting, setIsCorrecting] = useState(false)
  const [correctionText, setCorrectionText] = useState('')
  const [busy, setBusy] = useState(false)
  const [answered, setAnswered] = useState(question.state !== 'pending')

  if (answered) {
    return null
  }

  const handleAnswer = async (action: 'confirm' | 'correct' | 'defer' | 'dismiss', correction?: string) => {
    if (!bridge?.learningAnswerQuestion || busy) {
      return
    }

    setBusy(true)
    try {
      await bridge.learningAnswerQuestion(question.id, action, correction)
      setAnswered(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-2 my-1 p-2.5 rounded-lg bg-sky-950/40 border border-sky-500/40 text-xs flex flex-col gap-2 shadow-sm">
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
                void handleAnswer('correct', correctionText.trim())
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
              disabled={!correctionText.trim() || busy}
              onClick={() => {
                void handleAnswer('correct', correctionText.trim())
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
        <div className="flex items-center gap-1.5 mt-1">
          <Button
            disabled={busy}
            onClick={() => void handleAnswer('confirm')}
            size="xs"
            variant="default"
          >
            Confirmar
          </Button>
          <Button
            disabled={busy}
            onClick={() => setIsCorrecting(true)}
            size="xs"
            variant="secondary"
          >
            Corrigir
          </Button>
          <Button
            disabled={busy}
            onClick={() => void handleAnswer('defer')}
            size="xs"
            variant="ghost"
          >
            Adiar
          </Button>
          <Button
            disabled={busy}
            onClick={() => void handleAnswer('dismiss')}
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