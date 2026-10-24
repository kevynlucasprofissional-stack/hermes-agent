import { describe, expect, it } from 'vitest'

import {
  captureBindingMatches,
  isLearningCaptureAuthorized,
  type LearningCaptureAuthority,
  type LearningCaptureBinding
} from './workstation-learning-capture'

const binding: LearningCaptureBinding = {
  activationId: 'activation-1', sessionId: 'learning-1', ownerTaskId: 'task-1', tabId: 'tab-1',
  webContentsId: 41, documentEpoch: 'document-1', origin: 'https://app.example.com',
  leaseAcquiredAt: '2026-10-24T10:00:00Z', leaseSessionId: 'chat-1'
}

function authority(): LearningCaptureAuthority {
  return {
    session: {
      schema: 'hermes.learning_session.v1', sessionId: 'learning-1', runtimeSessionId: 'task-1',
      storedSessionId: 'chat-1', tabId: 'tab-1', webContentsId: 41, documentEpoch: 'document-1',
      status: 'learning', intensity: 'intensivo', startedAt: '2026-10-24T10:00:00Z', endedAt: null,
      allowlistedOrigin: 'https://app.example.com', eventsCount: 0, questionsCount: 0,
      pendingQuestions: [], videoStatus: 'disabled', lastError: null, sessionDir: 'unused', userBusy: false
    },
    tabId: 'tab-1', webContentsId: 41, documentEpoch: 'document-1', ownerTaskId: 'task-1',
    url: 'https://app.example.com/editor', frameUrl: 'https://app.example.com/editor',
    isMainFrame: true, profileScope: 'profile-1', nowMs: Date.parse('2026-10-24T10:01:00Z'),
    lease: {
      owner: 'human', taskId: 'task-1', sessionId: 'chat-1', tabId: 'tab-1', pageId: 41,
      profileScope: 'profile-1', acquiredAt: binding.leaseAcquiredAt, expiresAt: '2026-10-24T10:05:00Z'
    }
  }
}

describe('learning capture authority', () => {
  it('accepts the current owner document with a valid human lease', () => {
    expect(isLearningCaptureAuthorized(binding, authority())).toBe(true)
    expect(captureBindingMatches({ ...binding }, binding)).toBe(true)
  })

  it.each([
    ['another tab', { tabId: 'tab-2' }],
    ['another webContents', { webContentsId: 42 }],
    ['an unauthorized frame', { isMainFrame: false }],
    ['an old document', { documentEpoch: 'document-2' }],
    ['another origin', { url: 'https://other.example.com' }],
    ['another frame origin', { frameUrl: 'https://other.example.com' }],
    ['a missing owner', { ownerTaskId: null }],
    ['a revoked lease', { lease: null }],
    ['an expired lease', { nowMs: Date.parse('2026-10-24T10:05:00Z') }]
  ] as Array<[string, Partial<LearningCaptureAuthority>]>)('rejects %s', (_name, patch) => {
    expect(isLearningCaptureAuthorized(binding, { ...authority(), ...patch })).toBe(false)
  })

  it.each(['paused', 'idle', 'failed'] as const)('rejects session state %s', (status) => {
    const current = authority()
    current.session = { ...current.session!, status }
    expect(isLearningCaptureAuthorized(binding, current)).toBe(false)
  })

  it('rejects another learning session and a replaced lease', () => {
    const current = authority()
    current.session = { ...current.session!, sessionId: 'learning-2' }
    expect(isLearningCaptureAuthorized(binding, current)).toBe(false)
    const replaced = authority()
    replaced.lease = { ...replaced.lease!, acquiredAt: '2026-10-24T10:01:00Z' }
    expect(isLearningCaptureAuthorized(binding, replaced)).toBe(false)
    expect(captureBindingMatches({ ...binding, activationId: 'previous-activation' }, binding)).toBe(false)
    const transferred = authority()
    transferred.ownerTaskId = 'new-task'
    transferred.lease = { ...transferred.lease!, taskId: 'new-task' }
    expect(isLearningCaptureAuthorized(binding, transferred)).toBe(false)
  })

  it.each([
    ['task', { taskId: 'other-task' }],
    ['tab', { tabId: 'other-tab' }],
    ['webContents', { pageId: 99 }],
    ['session', { sessionId: 'other-chat' }],
    ['profile', { profileScope: 'other-profile' }]
  ] as Array<[string, Partial<NonNullable<LearningCaptureAuthority['lease']>>]>)('rejects a lease with the wrong %s scope', (_name, patch) => {
    const current = authority()
    current.lease = { ...current.lease!, ...patch }
    expect(isLearningCaptureAuthorized(binding, current)).toBe(false)
  })
})
