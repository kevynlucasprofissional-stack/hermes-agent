import { useEffect, useRef } from 'react'

import type {
  LearningQuestionItem,
  LearningSessionState,
  WorkstationBrowserBridge,
  WorkstationMilestone
} from '@/app/browser/types'
import { textPart } from '@/lib/chat-messages/parts'
import { $sessionStates, publishSessionState } from '@/store/session-states'

import type { ClientSessionState } from '../../types'

interface UseLearningChatBridgeOptions {
  bridge: WorkstationBrowserBridge | undefined
  runtimeSessionId: string | null
  storedSessionId: string | null
}

/**
 * Bridges Electron IPC learning state into the chat transcript.
 *
 * Subscribes to `onLearningState` and `onMilestone` push channels and injects
 * pending questions / milestones as synthetic system messages into the active
 * session's transcript via `publishSessionState`. Deduplicates by question id
 * and milestone eventId so reconnects and re-renders never produce duplicate
 * cards.
 *
 * Questions without a matching `storedSessionId` are intentionally skipped —
 * they remain pending in the recorder but do not leak into an unrelated chat.
 */
export function useLearningChatBridge({
  bridge,
  runtimeSessionId,
  storedSessionId
}: UseLearningChatBridgeOptions): void {
  const injectedQuestionsRef = useRef<Set<string>>(new Set())
  const injectedMilestonesRef = useRef<Set<string>>(new Set())

  // Reset dedup sets when the active session changes so a different chat can
  // receive its own questions/milestones even if ids happen to collide.
  useEffect(() => {
    injectedQuestionsRef.current.clear()
    injectedMilestonesRef.current.clear()
  }, [runtimeSessionId, storedSessionId])

  useEffect(() => {
    if (!bridge?.onLearningState || !runtimeSessionId) {
      return
    }

    const cleanup = bridge.onLearningState((state: LearningSessionState | null) => {
      if (!state || !storedSessionId) {
        return
      }

      // Only inject questions that belong to this chat session.
      if (state.storedSessionId !== storedSessionId) {
        return
      }

      for (const question of state.pendingQuestions) {
        if (question.state !== 'pending') {
          continue
        }

        if (injectedQuestionsRef.current.has(question.id)) {
          continue
        }

        injectedQuestionsRef.current.add(question.id)
        injectLearningQuestion(runtimeSessionId, question)
      }
    })

    return cleanup
  }, [bridge, runtimeSessionId, storedSessionId])

  useEffect(() => {
    if (!bridge?.onMilestone || !runtimeSessionId) {
      return
    }

    const cleanup = bridge.onMilestone((milestone: WorkstationMilestone) => {
      if (!storedSessionId || milestone.sessionId !== storedSessionId) {
        return
      }

      if (injectedMilestonesRef.current.has(milestone.eventId)) {
        return
      }

      injectedMilestonesRef.current.add(milestone.eventId)
      injectLearningMilestone(runtimeSessionId, milestone)
    })

    return cleanup
  }, [bridge, runtimeSessionId, storedSessionId])
}

function injectLearningQuestion(runtimeSessionId: string, question: LearningQuestionItem): void {
  const timestamp = Date.now()
  const current = $sessionStates.get()[runtimeSessionId]

  if (!current) {
    return
  }

  publishSessionState(runtimeSessionId, {
    ...current,
    messages: [
      ...current.messages,
      {
        id: `learning-q-${question.id}`,
        role: 'system',
        parts: [textPart(`learning-question:${JSON.stringify(question)}`, timestamp)],
        timestamp
      }
    ]
  })
}

function injectLearningMilestone(runtimeSessionId: string, milestone: WorkstationMilestone): void {
  const timestamp = new Date(milestone.occurredAt).getTime() || Date.now()
  const current = $sessionStates.get()[runtimeSessionId]

  if (!current) {
    return
  }

  publishSessionState(runtimeSessionId, {
    ...current,
    messages: [
      ...current.messages,
      {
        id: `learning-ms-${milestone.eventId}`,
        role: 'system',
        parts: [textPart(`learning-milestone:${JSON.stringify(milestone)}`, timestamp)],
        timestamp
      }
    ]
  })
}