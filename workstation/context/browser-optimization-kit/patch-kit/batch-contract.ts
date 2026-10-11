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
/** Serial execution, never retries a potentially mutating step automatically. */
export async function executeAuthorizedBatch(
  steps: BrowserBatchStep[], context: BrowserBatchContext, owner: BrowserBatchAdapter
): Promise<BrowserBatchResult> {
  if (!context.taskId || !context.runId || !context.tabId || !context.operationId ||
      !Array.isArray(steps) || steps.length === 0 || steps.length > 20)
    return { status: 'rejected', completedSteps: 0, verifiedSteps: 0,
      stoppedAt: 0, receipts: [], reason: 'invalid_batch_identity_or_size' }
  const receipts: Array<string | null> = []
  let completedSteps = 0
  let verifiedSteps = 0
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    if (!step || !['click', 'type', 'press', 'scroll'].includes(step.kind) ||
        (('ref' in step) && (!step.ref || step.ref.length > 256)) ||
        (step.kind === 'type' && step.text.length > 20_000)) {
      return { status: 'rejected', completedSteps, verifiedSteps,
        stoppedAt: i, receipts, reason: 'invalid_step' }
    }
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
