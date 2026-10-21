import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ClientSessionState } from '@/app/types'
import type { LearningQuestionItem, LearningSessionState, WorkstationMilestone } from './types'
import { useWorkstationChatSync } from './use-workstation-chat-sync'

describe('useWorkstationChatSync', () => {
  let onLearningStateCb: ((state: LearningSessionState | null) => void) | null = null
  let onMilestoneCb: ((milestone: WorkstationMilestone) => void) | null = null

  const mockBridge = {
    onLearningState: vi.fn((cb: (state: LearningSessionState | null) => void) => {
      onLearningStateCb = cb
      return vi.fn()
    }),
    onMilestone: vi.fn((cb: (milestone: WorkstationMilestone) => void) => {
      onMilestoneCb = cb
      return vi.fn()
    }),
    learningGetQuestions: vi.fn().mockResolvedValue([])
  }

  beforeEach(() => {
    vi.stubGlobal('hermesDesktop', {
      workstationBrowser: mockBridge
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    onLearningStateCb = null
    onMilestoneCb = null
  })

  it('subscribes to onMilestone and appends milestone to the target session messages', () => {
    let sessionMessages: any[] = []
    const updateSessionState = vi.fn((sessionId, updater) => {
      const state: ClientSessionState = {
        storedSessionId: 'sess-stored-1',
        messages: sessionMessages,
        branch: 'main',
        cwd: '/test',
        model: 'hermes',
        provider: 'nous',
        reasoningEffort: 'low',
        serviceTier: 'standard',
        fast: false,
        yolo: false,
        personality: 'helpful',
        busy: false,
        awaitingResponse: false,
        streamId: null,
        sawAssistantPayload: false,
        adoptedRunningTurn: false,
        pendingBranchGroup: null,
        interrupted: false,
        interimBoundaryPending: false,
        needsInput: false,
        runtimeStartedAt: 0,
        turnStartedAt: null,
        turnLive: false,
        usage: null
      }
      const next = updater(state)
      sessionMessages = next.messages
      return next
    })

    renderHook(() =>
      useWorkstationChatSync({
        activeSessionId: 'rt-1',
        selectedStoredSessionId: 'sess-stored-1',
        updateSessionState
      })
    )

    expect(mockBridge.onMilestone).toHaveBeenCalled()

    const milestone: WorkstationMilestone = {
      eventId: 'ms-999',
      sessionId: 'sess-stored-1',
      stage: 'candidate',
      occurredAt: '2026-10-18T10:00:00Z',
      capabilityId: 'layer_crop',
      evidenceRefs: ['lesson:1']
    }

    onMilestoneCb!(milestone)

    expect(updateSessionState).toHaveBeenCalled()
    expect(sessionMessages).toHaveLength(1)
    expect(sessionMessages[0].id).toBe('milestone-ms-999')
    expect(sessionMessages[0].parts[0].text).toContain('workstation:')
    expect(sessionMessages[0].parts[0].text).toContain('candidate')

    // Second arrival with same eventId must NOT duplicate (idempotence)
    onMilestoneCb!(milestone)
    expect(sessionMessages).toHaveLength(1)
  })

  it('subscribes to onLearningState and syncs questions to matching session only', () => {
    let sessionMessages: any[] = []
    const updateSessionState = vi.fn((sessionId, updater) => {
      const state: ClientSessionState = {
        storedSessionId: 'st-1',
        messages: sessionMessages,
        branch: 'main',
        cwd: '/test',
        model: 'hermes',
        provider: 'nous',
        reasoningEffort: 'low',
        serviceTier: 'standard',
        fast: false,
        yolo: false,
        personality: 'helpful',
        busy: false,
        awaitingResponse: false,
        streamId: null,
        sawAssistantPayload: false,
        adoptedRunningTurn: false,
        pendingBranchGroup: null,
        interrupted: false,
        interimBoundaryPending: false,
        needsInput: false,
        runtimeStartedAt: 0,
        turnStartedAt: null,
        turnLive: false,
        usage: null
      }
      const next = updater(state)
      sessionMessages = next.messages
      return next
    })

    renderHook(() =>
      useWorkstationChatSync({
        activeSessionId: 'rt-1',
        selectedStoredSessionId: 'st-1',
        updateSessionState
      })
    )

    const questionItem: LearningQuestionItem = {
      id: 'q-777',
      sessionId: 'learn-sess-1',
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      eventRefs: [],
      fromMs: 0,
      toMs: 0,
      kind: 'intent',
      category: 'intent',
      hypothesis: 'Intent hypothesis',
      uncertainty: 0.5,
      score: 0.8,
      dedupeKey: 'key-777',
      proposedQuestion: 'Dúvida?',
      state: 'pending',
      needsReinterpretation: false,
      createdAt: '2026-10-18T10:00:00Z'
    }

    const learningState: LearningSessionState = {
      schema: 'hermes.learning_session.v1',
      sessionId: 'learn-sess-1',
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      status: 'learning',
      intensity: 'intensivo',
      startedAt: '2026-10-18T10:00:00Z',
      endedAt: null,
      allowlistedOrigin: 'https://test.com',
      eventsCount: 5,
      questionsCount: 1,
      pendingQuestions: [questionItem],
      videoStatus: 'recording',
      lastError: null,
      sessionDir: '/tmp',
      userBusy: false
    }

    onLearningStateCb!(learningState)

    expect(updateSessionState).toHaveBeenCalled()
    expect(sessionMessages).toHaveLength(1)
    expect(sessionMessages[0].id).toBe('learning-question-q-777')
    expect(sessionMessages[0].parts[0].text).toContain('learning-question:')

    // Question update in place (e.g. answered)
    const answeredQuestion: LearningQuestionItem = {
      ...questionItem,
      state: 'confirmed',
      userResponse: 'Confirmado pelo usuário'
    }
    onLearningStateCb!({
      ...learningState,
      pendingQuestions: [answeredQuestion]
    })

    expect(sessionMessages).toHaveLength(1)
    expect(sessionMessages[0].parts[0].text).toContain('Confirmado pelo usuário')
  })

  it('prevents question leakage to an unrelated session (strict session isolation)', () => {
    let sessionMessages: any[] = []
    const updateSessionState = vi.fn((sessionId, updater) => {
      const state: any = { messages: sessionMessages }
      const next = updater(state)
      sessionMessages = next.messages
      return next
    })

    renderHook(() =>
      useWorkstationChatSync({
        activeSessionId: 'rt-current-user',
        selectedStoredSessionId: 'st-current-user',
        updateSessionState
      })
    )

    // Event belonging to a different session
    const otherSessionQuestion: LearningQuestionItem = {
      id: 'q-other',
      sessionId: 'learn-sess-other',
      runtimeSessionId: 'rt-other',
      storedSessionId: 'st-other',
      tabId: 'tab-1',
      eventRefs: [],
      fromMs: 0,
      toMs: 0,
      kind: 'intent',
      category: 'intent',
      hypothesis: 'Other hypothesis',
      uncertainty: 0.5,
      score: 0.8,
      dedupeKey: 'key-other',
      proposedQuestion: 'Other question?',
      state: 'pending',
      needsReinterpretation: false,
      createdAt: '2026-10-18T10:00:00Z'
    }

    const otherLearningState: LearningSessionState = {
      schema: 'hermes.learning_session.v1',
      sessionId: 'learn-sess-other',
      runtimeSessionId: 'rt-other',
      storedSessionId: 'st-other',
      tabId: 'tab-1',
      webContentsId: 2,
      documentEpoch: 'ep-2',
      status: 'learning',
      intensity: 'intensivo',
      startedAt: '2026-10-18T10:00:00Z',
      endedAt: null,
      allowlistedOrigin: 'https://other.com',
      eventsCount: 1,
      questionsCount: 1,
      pendingQuestions: [otherSessionQuestion],
      videoStatus: 'recording',
      lastError: null,
      sessionDir: '/tmp',
      userBusy: false
    }

    onLearningStateCb!(otherLearningState)

    // Notice: updateSessionState was NOT called targeting rt-current-user!
    expect(updateSessionState).not.toHaveBeenCalledWith('rt-current-user', expect.anything(), expect.anything())
  })
})
