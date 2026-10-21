import { useCallback, useEffect, useRef } from 'react'

import type { ClientSessionState } from '@/app/types'
import { chatMessageText, type ChatMessage } from '@/lib/chat-messages'
import { $sessions, conversationAliases } from '@/store/session'

import type {
  LearningQuestionItem,
  LearningSessionState,
  WorkstationBrowserBridge,
  WorkstationMilestone
} from './types'

export interface UseWorkstationChatSyncOptions {
  activeSessionId: string | null
  selectedStoredSessionId: string | null
  updateSessionState: (
    sessionId: string,
    updater: (state: ClientSessionState) => ClientSessionState,
    storedSessionId?: string | null
  ) => ClientSessionState
  getRuntimeIdForStoredSession?: (storedSessionId: string) => string | null
}

function questionMatchesSession(
  question: LearningQuestionItem,
  storedSessionId: string | null,
  runtimeSessionId: string | null,
  learningState?: LearningSessionState | null
): boolean {
  if (question.storedSessionId && storedSessionId) {
    if (question.storedSessionId === storedSessionId) {
      return true
    }
    const aliases = conversationAliases(storedSessionId, $sessions.get())
    if (aliases.includes(question.storedSessionId)) {
      return true
    }
  }

  if (question.runtimeSessionId && runtimeSessionId && question.runtimeSessionId === runtimeSessionId) {
    return true
  }

  if (learningState && learningState.sessionId === question.sessionId) {
    if (learningState.storedSessionId && storedSessionId) {
      if (learningState.storedSessionId === storedSessionId) {
        return true
      }
      const aliases = conversationAliases(storedSessionId, $sessions.get())
      if (aliases.includes(learningState.storedSessionId)) {
        return true
      }
    }
    if (learningState.runtimeSessionId && runtimeSessionId && learningState.runtimeSessionId === runtimeSessionId) {
      return true
    }
  }

  return false
}

export function useWorkstationChatSync({
  activeSessionId,
  selectedStoredSessionId,
  updateSessionState,
  getRuntimeIdForStoredSession
}: UseWorkstationChatSyncOptions) {
  const bridge: WorkstationBrowserBridge | undefined = window.hermesDesktop?.workstationBrowser
  const activeSessionIdRef = useRef(activeSessionId)
  const selectedStoredSessionIdRef = useRef(selectedStoredSessionId)
  const latestLearningStateRef = useRef<LearningSessionState | null>(null)

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
    selectedStoredSessionIdRef.current = selectedStoredSessionId
  }, [activeSessionId, selectedStoredSessionId])

  const syncQuestionToSession = useCallback(
    (question: LearningQuestionItem, targetRuntimeId: string, targetStoredId?: string | null) => {
      const messageId = `learning-question-${question.id}`
      const json = JSON.stringify(question)
      const text = `learning-question:${json}`

      updateSessionState(
        targetRuntimeId,
        state => {
          const existingIndex = state.messages.findIndex(m => m.id === messageId)

          if (existingIndex >= 0) {
            const currentMessage = state.messages[existingIndex]
            if (chatMessageText(currentMessage).trim() === text) {
              return state
            }

            const updatedMessages = [...state.messages]
            updatedMessages[existingIndex] = {
              ...currentMessage,
              parts: [{ type: 'text', text }]
            }

            return {
              ...state,
              messages: updatedMessages
            }
          }

          const newMessage: ChatMessage = {
            id: messageId,
            role: 'system',
            parts: [{ type: 'text', text }],
            timestamp: new Date(question.createdAt).getTime() || Date.now()
          }

          return {
            ...state,
            messages: [...state.messages, newMessage]
          }
        },
        targetStoredId
      )
    },
    [updateSessionState]
  )

  const syncMilestoneToSession = useCallback(
    (milestone: WorkstationMilestone) => {
      const targetSessionId = milestone.sessionId
      if (!targetSessionId) {
        return
      }

      const activeStored = selectedStoredSessionIdRef.current
      const activeRuntime = activeSessionIdRef.current

      // Verify that this milestone matches a known session or active conversation
      const resolvedRuntimeId =
        (getRuntimeIdForStoredSession ? getRuntimeIdForStoredSession(targetSessionId) : null) ||
        (activeStored && targetSessionId === activeStored && activeRuntime ? activeRuntime : null) ||
        (activeRuntime && targetSessionId === activeRuntime ? activeRuntime : null) ||
        targetSessionId

      const messageId = `milestone-${milestone.eventId}`
      const json = JSON.stringify(milestone)
      const text = `workstation:${json}`

      updateSessionState(
        resolvedRuntimeId,
        state => {
          if (state.messages.some(m => m.id === messageId)) {
            return state
          }

          const newMessage: ChatMessage = {
            id: messageId,
            role: 'system',
            parts: [{ type: 'text', text }],
            timestamp: new Date(milestone.occurredAt).getTime() || Date.now()
          }

          return {
            ...state,
            messages: [...state.messages, newMessage]
          }
        },
        targetSessionId
      )
    },
    [getRuntimeIdForStoredSession, updateSessionState]
  )

  // 1. Subscribe to IPC milestone broadcasts
  useEffect(() => {
    if (!bridge?.onMilestone) {
      return
    }

    const cleanup = bridge.onMilestone(milestone => {
      syncMilestoneToSession(milestone)
    })

    return cleanup
  }, [bridge, syncMilestoneToSession])

  // 2. Subscribe to IPC learning state broadcasts (proactive questions)
  useEffect(() => {
    if (!bridge?.onLearningState) {
      return
    }

    const cleanup = bridge.onLearningState(state => {
      latestLearningStateRef.current = state
      if (!state) {
        return
      }

      const questions = state.pendingQuestions || []
      if (!questions.length) {
        return
      }

      const targetStored = state.storedSessionId
      const targetRuntime =
        state.runtimeSessionId ||
        (targetStored && getRuntimeIdForStoredSession ? getRuntimeIdForStoredSession(targetStored) : null) ||
        (targetStored && targetStored === selectedStoredSessionIdRef.current && activeSessionIdRef.current
          ? activeSessionIdRef.current
          : null)

      if (!targetRuntime) {
        return
      }

      for (const question of questions) {
        if (
          questionMatchesSession(
            question,
            targetStored,
            targetRuntime,
            state
          )
        ) {
          syncQuestionToSession(question, targetRuntime, targetStored)
        }
      }
    })

    return cleanup
  }, [bridge, getRuntimeIdForStoredSession, syncQuestionToSession])

  // 3. Hydrate questions when active session changes or mounts
  useEffect(() => {
    if (!bridge?.learningGetQuestions) {
      return
    }

    const curActive = activeSessionId
    const curStored = selectedStoredSessionId

    if (!curActive && !curStored) {
      return
    }

    let isMounted = true

    bridge
      .learningGetQuestions()
      .then(questions => {
        if (!isMounted || !Array.isArray(questions) || !questions.length) {
          return
        }

        const targetRuntime =
          curActive || (curStored && getRuntimeIdForStoredSession ? getRuntimeIdForStoredSession(curStored) : null)
        if (!targetRuntime) {
          return
        }

        for (const question of questions) {
          if (
            questionMatchesSession(
              question,
              curStored,
              curActive,
              latestLearningStateRef.current
            )
          ) {
            syncQuestionToSession(question, targetRuntime, curStored)
          }
        }
      })
      .catch(() => undefined)

    return () => {
      isMounted = false
    }
  }, [activeSessionId, selectedStoredSessionId, bridge, getRuntimeIdForStoredSession, syncQuestionToSession])
}
