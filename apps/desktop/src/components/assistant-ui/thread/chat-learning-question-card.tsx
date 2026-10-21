import { MessagePrimitive } from '@assistant-ui/react'
import { useCallback, useEffect, useState } from 'react'

import type { LearningQuestionItem } from '@/app/browser/types'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

export interface ChatLearningQuestionCardProps {
  question: LearningQuestionItem
  onAnswer?: (questionId: string, action: 'confirm' | 'correct' | 'defer' | 'dismiss', correction?: string) => void
}

export function ChatLearningQuestionCard({ question, onAnswer }: ChatLearningQuestionCardProps) {
  const [currentState, setCurrentState] = useState(question.state)
  const [userResponse, setUserResponse] = useState(question.userResponse)
  const [isCorrecting, setIsCorrecting] = useState(false)
  const [correctionText, setCorrectionText] = useState('')
  const [actionBusy, setActionBusy] = useState(false)

  useEffect(() => {
    setCurrentState(question.state)
    setUserResponse(question.userResponse)
  }, [question.state, question.userResponse])

  const handleAction = useCallback(async (action: 'confirm' | 'correct' | 'defer' | 'dismiss', correction?: string) => {
    setActionBusy(true)
    try {
      if (onAnswer) {
        onAnswer(question.id, action, correction)
      } else if (window.hermesDesktop?.workstationBrowser?.learningAnswerQuestion) {
        await window.hermesDesktop.workstationBrowser.learningAnswerQuestion(question.id, action, correction)
      }

      const nextMap: Record<typeof action, LearningQuestionItem['state']> = {
        confirm: 'confirmed',
        correct: 'corrected',
        defer: 'deferred',
        dismiss: 'dismissed'
      }
      setCurrentState(nextMap[action])
      if (action === 'confirm') {
        setUserResponse('Confirmado pelo usuário')
      } else if (action === 'correct') {
        setUserResponse(correction ? `Corrigido: ${correction}` : 'Corrigido pelo usuário')
      } else if (action === 'defer') {
        setUserResponse('Adiado')
      } else if (action === 'dismiss') {
        setUserResponse('Dispensado')
      }
    } finally {
      setActionBusy(false)
      setIsCorrecting(false)
    }
  }, [onAnswer, question.id])

  return (
    <MessagePrimitive.Root
      className="flex w-full min-w-0 max-w-[44rem] flex-col self-center my-1.5 p-3 rounded-lg bg-sky-950/30 border border-sky-500/40 text-xs shadow-sm transition-all"
      data-role="system"
      data-slot="aui_learning-question-card"
    >
      <div className="flex items-center justify-between pb-1.5 border-b border-sky-500/20">
        <div className="flex items-center gap-1.5">
          <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase bg-sky-500/20 text-sky-300 px-1.5 py-0.5 rounded font-semibold">
            <Codicon name="record" size="0.65rem" />
            Modo Aprender
          </span>
          <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase bg-sky-500/10 text-sky-400 px-1.5 py-0.5 rounded">
            {question.kind}
          </span>
        </div>
        <span className="text-[10px] font-mono text-(--ui-text-tertiary)">
          Incerteza: {Math.round(question.uncertainty * 100)}%
        </span>
      </div>

      <div className="text-(--ui-text-secondary) text-[11px] italic mt-1.5">
        Hipótese: {question.hypothesis}
      </div>

      <div className="text-(--ui-text-primary) font-medium text-xs mt-1">
        {question.proposedQuestion}
      </div>

      {currentState === 'pending' ? (
        isCorrecting ? (
          <div className="flex flex-col gap-1.5 mt-2">
            <input
              autoFocus
              className="w-full px-2 py-1 rounded bg-(--ui-background) border border-(--ui-stroke-secondary) text-xs text-(--ui-text-primary) placeholder:text-(--ui-text-tertiary)"
              onChange={e => setCorrectionText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && correctionText.trim()) {
                  void handleAction('correct', correctionText.trim())
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
                onClick={() => void handleAction('correct', correctionText.trim())}
                size="xs"
                variant="default"
              >
                Confirmar Correção
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 mt-2 pt-1.5 border-t border-sky-500/20">
            <Button
              disabled={actionBusy}
              onClick={() => void handleAction('confirm')}
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
              onClick={() => void handleAction('defer')}
              size="xs"
              variant="ghost"
            >
              Adiar
            </Button>
            <Button
              className="text-(--ui-text-tertiary) hover:text-(--ui-text-secondary) ml-auto"
              disabled={actionBusy}
              onClick={() => void handleAction('dismiss')}
              size="xs"
              variant="ghost"
            >
              Dispensar
            </Button>
          </div>
        )
      ) : (
        <div className="flex items-center gap-1.5 mt-2 pt-1.5 border-t border-sky-500/20 text-[11px]">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-0.5 font-medium',
              currentState === 'confirmed'
                ? 'bg-emerald-500/20 text-emerald-400'
                : currentState === 'corrected'
                  ? 'bg-sky-500/20 text-sky-300'
                  : 'bg-muted/40 text-muted-foreground'
            )}
          >
            <Codicon
              name={
                currentState === 'confirmed'
                  ? 'check'
                  : currentState === 'corrected'
                    ? 'edit'
                    : currentState === 'deferred'
                      ? 'history'
                      : 'close'
              }
              size="0.7rem"
            />
            {userResponse || currentState}
          </span>
        </div>
      )}
    </MessagePrimitive.Root>
  )
}
