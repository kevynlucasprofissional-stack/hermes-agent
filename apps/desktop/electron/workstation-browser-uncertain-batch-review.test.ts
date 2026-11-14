import assert from 'node:assert/strict'
import {test} from 'vitest'

import {sameUncertainBatchReview, uncertainBatchReviewCandidate} from './workstation-browser-human-review'

const operationId = 'op-batch-pending'
const admission = {
  operationId, action: 'browser_batch_actions', taskId: 'task-chat',
  sessionId: 'session-chat', runId: 'run-chat', tabId: 'tab-chat',
  argumentsDigest: 'digest', uncertainty: {
    reason: 'click_postcondition_not_observed', completedSteps: 1,
    verifiedSteps: 0, stoppedAt: 0, recordedAt: new Date().toISOString()
  }
}
const snapshot = () => ({
  operationAdmissions: {[operationId]: {...admission, uncertainty: {...admission.uncertainty}}},
  browserTasks: {tasks: [{
    taskId: 'task-chat', sessionHost: 'session-chat', runId: 'run-chat', revision: 3
  }]},
  tabs: [{id: 'tab-chat', browserTaskId: 'task-chat', recoveryState: 'live'}]
})
const live = {url: 'https://chatgpt.com/c/known', webContentsId: 3}

test('pending batch with effect uncertainty qualifies for a human review only', () => {
  const proof = uncertainBatchReviewCandidate(snapshot() as any, operationId, live)
  assert.ok(proof)
  assert.equal(proof.review.reason, 'click_postcondition_not_observed')
  assert.equal(proof.review.completedSteps, 1)
  assert.equal(proof.review.taskRevision, 3)
})

test('no-effect invalid batches and acknowledged or terminal operations do not qualify', () => {
  const noSteps = snapshot()
  noSteps.operationAdmissions[operationId].uncertainty.completedSteps = 0
  assert.equal(uncertainBatchReviewCandidate(noSteps as any, operationId, live), null)
  const ack = snapshot()
  ;(ack.operationAdmissions[operationId] as any).acknowledged = true
  assert.equal(uncertainBatchReviewCandidate(ack as any, operationId, live), null)
  const terminal = snapshot()
  ;(terminal.operationAdmissions[operationId] as any).terminal = {kind: 'RECONCILED'}
  assert.equal(uncertainBatchReviewCandidate(terminal as any, operationId, live), null)
})

test('task owner, live tab and human lease remain hard gates', () => {
  const badOwner = snapshot()
  badOwner.browserTasks.tasks[0].runId = 'different'
  assert.equal(uncertainBatchReviewCandidate(badOwner as any, operationId, live), null)
  const parked = snapshot()
  parked.tabs[0].recoveryState = 'restored'
  assert.equal(uncertainBatchReviewCandidate(parked as any, operationId, live), null)
  const leased = snapshot()
  ;(leased.browserTasks.tasks[0] as any).humanControlLease = {token: 'human'}
  assert.equal(uncertainBatchReviewCandidate(leased as any, operationId, live), null)
  assert.equal(uncertainBatchReviewCandidate(snapshot() as any, operationId, null), null)
})

test('compare exact batch review identities and revisions before releasing fence', () => {
  const review = uncertainBatchReviewCandidate(snapshot() as any, operationId, live)!.review
  assert.equal(sameUncertainBatchReview(review, {...review}), true)
  assert.equal(sameUncertainBatchReview(review, {...review, taskRevision: 4}), false)
  assert.equal(sameUncertainBatchReview(review, {...review, webContentsId: 4}), false)
  assert.equal(sameUncertainBatchReview(review, {...review, reason: 'other'}), false)
})
