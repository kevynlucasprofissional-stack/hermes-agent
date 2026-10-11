import assert from 'node:assert/strict'
import { test } from 'vitest'
import { executeAuthorizedBatch, type BrowserBatchAdapter,
  type BrowserBatchContext, type BrowserBatchStep } from './batch-contract'

const ctx: BrowserBatchContext = { taskId: 't', tabId: 'tab', runId: 'r', operationId: 'op' }
const steps: BrowserBatchStep[] = [{ kind: 'click', ref: '@e1' },
  { kind: 'type', ref: '@e2', text: 'ok' }, { kind: 'press', key: 'Enter' }]

test('stops before next effect when human takes over', async () => {
  const called: number[] = []
  const owner: BrowserBatchAdapter = {
    checkBefore: async (_step, _ctx, index) => { if (index === 1) throw Error('409 USER_CONTROL_ACTIVE') },
    perform: async (_step, _ctx, index) => { called.push(index); return 'ok' },
    verifyAfter: async (_step, _ctx, index) => ({ verified: true, receiptRef: 'r:' + index }),
    checkpoint: async () => {}
  }
  const r = await executeAuthorizedBatch(steps, ctx, owner)
  assert.equal(r.status, 'rejected')
  assert.equal(r.stoppedAt, 1)
  assert.deepEqual(called, [0])
})

test('does not mark ACK-only evidence as verified', async () => {
  let effects = 0
  const owner: BrowserBatchAdapter = {
    checkBefore: async () => {},
    perform: async () => { effects++; return 'ack' },
    verifyAfter: async () => ({ verified: false, receiptRef: null }),
    checkpoint: async () => {}
  }
  const r = await executeAuthorizedBatch(steps, ctx, owner)
  assert.equal(r.status, 'uncertain')
  assert.equal(effects, 1)
  assert.equal(r.verifiedSteps, 0)
})

test('reports verified only when each step produces proof', async () => {
  const owner: BrowserBatchAdapter = {
    checkBefore: async () => {},
    perform: async () => 'ok',
    verifyAfter: async (_step, _ctx, index) => ({ verified: true, receiptRef: 'r:' + index }),
    checkpoint: async () => {}
  }
  const r = await executeAuthorizedBatch(steps, ctx, owner)
  assert.equal(r.status, 'verified')
  assert.equal(r.verifiedSteps, 3)
  assert.equal(r.receipts.length, 3)
})
