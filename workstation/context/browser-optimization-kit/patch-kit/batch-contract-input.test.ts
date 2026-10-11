import assert from 'node:assert/strict'
import { test } from 'vitest'
import {
  executeAuthorizedBatch,
  type BrowserBatchAdapter,
  type BrowserBatchContext
} from './batch-contract'

test('rejects a sparse batch at its actual index before invoking any owner callback', async () => {
  const steps = Array(2)
  steps[0] = { kind: 'click', ref: '@e1' }
  const context: BrowserBatchContext = { taskId: 't', runId: 'r', tabId: 'tab', operationId: 'op' }
  const calls = { checkBefore: 0, perform: 0, verifyAfter: 0, checkpoint: 0 }
  const owner: BrowserBatchAdapter = {
    async checkBefore() { calls.checkBefore += 1 },
    async perform() { calls.perform += 1; return { acknowledged: true } },
    async verifyAfter() { calls.verifyAfter += 1; return { receiptRef: 'owner-receipt', verified: true } },
    async checkpoint() { calls.checkpoint += 1 }
  }

  const result = await executeAuthorizedBatch(steps, context, owner)

  assert.equal(result.status, 'rejected')
  assert.equal(result.stoppedAt, 1)
  assert.equal(result.completedSteps, 0)
  assert.equal(result.verifiedSteps, 0)
  assert.deepEqual(result.receipts, [])
  assert.deepEqual(calls, { checkBefore: 0, perform: 0, verifyAfter: 0, checkpoint: 0 })
})
