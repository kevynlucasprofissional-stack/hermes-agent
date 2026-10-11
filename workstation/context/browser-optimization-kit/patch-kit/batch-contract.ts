/**
 * Original Hermes batch contract, not a new dispatcher/authority owner.
 * The caller MUST bind check/perform/verify/checkpoint to existing Hermes
 * BrowserTask/TaskRun/Policy/BrowserOwnerReceipt owners.
 */
export type BrowserBatchStep =
  | { kind: 'click'; ref: string; anchor?: { type?: string; value?: string } }
  | { kind: 'type'; ref: string; text: string; clear?: boolean; append?: boolean }
  | { kind: 'press'; key: string }
  | { kind: 'scroll'; direction: 'up' | 'down' }

export interface BrowserBatchContext {
  taskId: string
  runId: string
  tabId: string
  operationId: string
}
export interface StepEvidence {
  receiptRef: string | null
  verified: boolean
  uncertaintyReason?: string
}
export interface BrowserBatchAdapter {
  checkBefore(step: BrowserBatchStep, context: BrowserBatchContext, index: number): Promise<void>
  perform(step: BrowserBatchStep, context: BrowserBatchContext, index: number): Promise<unknown>
  verifyAfter(step: BrowserBatchStep, context: BrowserBatchContext,
    index: number, result: unknown): Promise<StepEvidence>
  checkpoint(context: BrowserBatchContext, index: number,
    evidence: StepEvidence): Promise<void>
}
export interface BrowserBatchResult {
  status: 'verified' | 'uncertain' | 'rejected'
  completedSteps: number
  verifiedSteps: number
  stoppedAt: number | null
  receipts: Array<string | null>
  reason?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function boundedString(value: unknown, maxLength: number): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= maxLength
}

function optionalBoolean(value: unknown): boolean {
  return value === undefined || typeof value === 'boolean'
}

function validAnchor(value: unknown): boolean {
  if (value === undefined) return true
  if (!isRecord(value)) return false

  return (value.type === undefined || boundedString(value.type, 128)) &&
    (value.value === undefined || boundedString(value.value, 512))
}

export function isBrowserBatchStep(value: unknown): value is BrowserBatchStep {
  if (!isRecord(value)) return false

  switch (value.kind) {
    case 'click':
      return boundedString(value.ref, 256) && validAnchor(value.anchor)
    case 'type':
      return boundedString(value.ref, 256) && typeof value.text === 'string' && value.text.length <= 20_000 &&
        optionalBoolean(value.clear) && optionalBoolean(value.append)
    case 'press':
      return boundedString(value.key, 128)
    case 'scroll':
      return value.direction === 'up' || value.direction === 'down'
    default:
      return false
  }
}

function validContext(value: unknown): value is BrowserBatchContext {
  return isRecord(value) && boundedString(value.taskId, 256) && boundedString(value.runId, 256) &&
    boundedString(value.tabId, 256) && boundedString(value.operationId, 256)
}

/** Serial execution, never retries a potentially mutating step automatically. */
export async function executeAuthorizedBatch(
  steps: unknown, context: BrowserBatchContext, owner: BrowserBatchAdapter
): Promise<BrowserBatchResult> {
  if (!validContext(context) || !Array.isArray(steps) || steps.length === 0 || steps.length > 20)
    return { status: 'rejected', completedSteps: 0, verifiedSteps: 0,
      stoppedAt: 0, receipts: [], reason: 'invalid_batch_identity_or_size' }
  let invalidStep = -1
  for (let i = 0; i < steps.length; i++) {
    if (!Object.hasOwn(steps, i) || !isBrowserBatchStep(steps[i])) {
      invalidStep = i
      break
    }
  }
  if (invalidStep >= 0)
    return { status: 'rejected', completedSteps: 0, verifiedSteps: 0,
      stoppedAt: invalidStep, receipts: [], reason: 'invalid_step' }
  const receipts: Array<string | null> = []
  let completedSteps = 0
  let verifiedSteps = 0
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    try {
      // Recheck real lease and policy at every step; never trust an earlier batch approval.
      await owner.checkBefore(step, context, i)
    } catch {
      return { status: 'rejected', completedSteps, verifiedSteps,
        stoppedAt: i, receipts, reason: 'authority_or_precondition_denied' }
    }
    let result: unknown
    try {
      result = await owner.perform(step, context, i)
      completedSteps++
    } catch {
      // The effect may have happened before the exception: never retry blindly.
      return { status: 'uncertain', completedSteps, verifiedSteps,
        stoppedAt: i, receipts, reason: 'effect_state_unknown' }
    }
    try {
      const evidence = await owner.verifyAfter(step, context, i, result)
      receipts.push(evidence.receiptRef)
      await owner.checkpoint(context, i, evidence)
      if (!evidence.verified || !evidence.receiptRef)
        return { status: 'uncertain', completedSteps, verifiedSteps,
          stoppedAt: i, receipts, reason: evidence.uncertaintyReason ?? 'unverified_effect' }
      verifiedSteps++
    } catch {
      return { status: 'uncertain', completedSteps, verifiedSteps,
        stoppedAt: i, receipts, reason: 'verification_or_checkpoint_failed' }
    }
  }
  return { status: 'verified', completedSteps, verifiedSteps, stoppedAt: null, receipts }
}
