import type {
  BrowserMutationAdmission, BrowserSessionStateSnapshot
} from './workstation-browser-session-state'

export interface VerifiedNavigationReview {
  operationId: string
  taskId: string
  sessionId: string
  runId: string
  tabId: string
  safeUrl: string
  webContentsId: number
  taskRevision: number
}

export interface NavigationReadback {
  url: string
  webContentsId: number
}

const SAFE_SYNTHETIC_HOST = /(?:^|\.)example\.test$|(?:^|\.)localhost$/

// No external message, click, batch or credential-bearing navigation can be
// reconciled with a URL match. This workflow is intentionally SYNTHETIC only.
function permittedReviewUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return !parsed.username && !parsed.password && !parsed.search && !parsed.hash &&
      ((parsed.protocol === 'https:' && SAFE_SYNTHETIC_HOST.test(parsed.hostname)) ||
        (parsed.protocol === 'http:' && ['127.0.0.1', '::1', 'localhost'].includes(parsed.hostname)))
  } catch {
    return false
  }
}

export function verifiedNavigationCandidate(
  snapshot: BrowserSessionStateSnapshot | null,
  operationId: string,
  readback: NavigationReadback | null
): { admission: BrowserMutationAdmission; review: VerifiedNavigationReview } | null {
  if (!snapshot || !readback || !Number.isInteger(readback.webContentsId) ||
    readback.webContentsId < 0) {return null}

  const admission = snapshot.operationAdmissions?.[operationId]
  if (!admission || admission.action !== 'browser_navigate' ||
      admission.acknowledged === true || admission.terminal) {return null}

  const task = snapshot.browserTasks.tasks.find(candidate =>
    candidate.taskId === admission.taskId &&
    candidate.runId === admission.runId &&
    candidate.sessionHost === admission.sessionId
  )
  const tab = snapshot.tabs.find(candidate =>
    candidate.id === admission.tabId && candidate.browserTaskId === admission.taskId
  )
  const receipt = task?.lastReceipt
  if (!task || !tab || !receipt || receipt.operationId !== operationId ||
      receipt.action !== 'browser_navigate' ||
      receipt.taskId !== admission.taskId ||
      receipt.runId !== admission.runId ||
      receipt.tabId !== admission.tabId ||
      receipt.browserTaskId !== admission.taskId ||
      task.humanControlLease || tab.recoveryState !== 'live' ||
      !receipt.safeUrl || !permittedReviewUrl(receipt.safeUrl) ||
      readback.url !== receipt.safeUrl ||
      tab.safeUrl !== receipt.safeUrl) {return null}

  return {admission, review: {
    operationId, taskId: admission.taskId, sessionId: admission.sessionId,
    runId: admission.runId, tabId: admission.tabId, safeUrl: receipt.safeUrl,
    webContentsId: readback.webContentsId,
    taskRevision: task.revision ?? 0
  }}
}

export function sameNavigationReview(
  left: VerifiedNavigationReview,
  right: VerifiedNavigationReview
): boolean {
  return left.operationId === right.operationId &&
    left.taskId === right.taskId &&
    left.sessionId === right.sessionId &&
    left.runId === right.runId &&
    left.tabId === right.tabId &&
    left.safeUrl === right.safeUrl && left.webContentsId === right.webContentsId &&
    left.taskRevision === right.taskRevision
}

/** An unresolved browser batch can only be closed by a native human review.
 * DOM or local ACK alone must never be treated as proof of external delivery. */
export interface UncertainBatchReview {
  operationId: string
  taskId: string
  sessionId: string
  runId: string
  tabId: string
  reason: string
  completedSteps: number
  verifiedSteps: number
  webContentsId: number
  taskRevision: number
}

export function uncertainBatchReviewCandidate(
  snapshot: BrowserSessionStateSnapshot | null,
  operationId: string,
  readback: NavigationReadback | null
): { admission: BrowserMutationAdmission; review: UncertainBatchReview } | null {
  if (!snapshot) {return null}
  const admission = snapshot.operationAdmissions?.[operationId]
  const uncertainty = admission?.uncertainty
  if (!admission || admission.action !== 'browser_batch_actions' || admission.acknowledged === true ||
      admission.terminal || !uncertainty || uncertainty.completedSteps < 1 ||
      uncertainty.verifiedSteps >= uncertainty.completedSteps) {return null}
  const task = snapshot.browserTasks.tasks.find(candidate =>
    candidate.taskId === admission.taskId && candidate.runId === admission.runId &&
    candidate.sessionHost === admission.sessionId)
  const tab = snapshot.tabs.find(candidate =>
    candidate.id === admission.tabId && candidate.browserTaskId === admission.taskId)
  const hasLiveReadback = Boolean(readback && Number.isInteger(readback.webContentsId) &&
    readback.webContentsId >= 0 && readback.url)
  // On restart, pending external pages remain intentionally unrestored. A native
  // human review can release the fence without loading or trusting that page.
  const recoverable = tab?.recoveryState === 'restored' && readback === null
  if (!task || !tab || task.humanControlLease ||
      !(tab.recoveryState === 'live' && hasLiveReadback) && !recoverable) {return null}
  return {admission, review: {
    operationId, taskId: admission.taskId, sessionId: admission.sessionId,
    runId: admission.runId, tabId: admission.tabId, reason: uncertainty.reason,
    completedSteps: uncertainty.completedSteps, verifiedSteps: uncertainty.verifiedSteps,
    webContentsId: recoverable ? -1 : readback!.webContentsId, taskRevision: task.revision ?? 0
  }}
}

export function sameUncertainBatchReview(left: UncertainBatchReview, right: UncertainBatchReview): boolean {
  return Object.keys(left).every(key =>
    left[key as keyof UncertainBatchReview] === right[key as keyof UncertainBatchReview])
}
