import type { LearningSessionState } from './workstation-learning-session'

export const LEARNING_CAPTURE_CONTROL = 'hermes:learning-capture:control'
export const LEARNING_CAPTURE_GESTURE = 'hermes:learning-capture:gesture'

export interface LearningCaptureBinding {
  activationId: string
  sessionId: string
  ownerTaskId: string
  tabId: string
  webContentsId: number
  documentEpoch: string
  origin: string
  leaseAcquiredAt: string
  leaseSessionId: string | null
}

export interface LearningCaptureAuthority {
  session: LearningSessionState | null
  tabId: string
  webContentsId: number
  documentEpoch: string
  ownerTaskId: string | null
  url: string
  frameUrl: string
  isMainFrame: boolean
  profileScope: string
  lease: {
    owner: string
    taskId: string
    sessionId: string | null
    tabId: string | null
    pageId: number | null
    profileScope: string | null
    acquiredAt: string
    expiresAt: string
  } | null
  nowMs: number
}

export function captureBindingMatches(value: unknown, expected: LearningCaptureBinding): boolean {
  if (!value || typeof value !== 'object') {
    return false
  }

  const binding = value as Record<string, unknown>

  return binding.activationId === expected.activationId
    && binding.sessionId === expected.sessionId
    && binding.ownerTaskId === expected.ownerTaskId
    && binding.tabId === expected.tabId
    && binding.webContentsId === expected.webContentsId
    && binding.documentEpoch === expected.documentEpoch
    && binding.origin === expected.origin
    && binding.leaseAcquiredAt === expected.leaseAcquiredAt
    && binding.leaseSessionId === expected.leaseSessionId
}

export function isLearningCaptureAuthorized(binding: LearningCaptureBinding, authority: LearningCaptureAuthority): boolean {
  const { session, lease } = authority

  if (!session || session.status !== 'learning' || !lease || !authority.isMainFrame
    || lease.owner !== 'human' || !authority.ownerTaskId
    || lease.taskId !== authority.ownerTaskId || authority.ownerTaskId !== binding.ownerTaskId
    || session.sessionId !== binding.sessionId
    || session.tabId !== binding.tabId || authority.tabId !== binding.tabId
    || session.webContentsId !== binding.webContentsId || authority.webContentsId !== binding.webContentsId
    || session.documentEpoch !== binding.documentEpoch || authority.documentEpoch !== binding.documentEpoch
    || lease.tabId !== binding.tabId || lease.pageId !== binding.webContentsId
    || lease.profileScope !== authority.profileScope
    || lease.acquiredAt !== binding.leaseAcquiredAt || lease.sessionId !== binding.leaseSessionId
    || !(Date.parse(lease.expiresAt) > authority.nowMs)) {
    return false
  }

  try {
    return binding.origin !== 'null'
      && new URL(session.allowlistedOrigin).origin === binding.origin
      && new URL(authority.url).origin === binding.origin
      && new URL(authority.frameUrl).origin === binding.origin
  } catch {
    return false
  }
}
