import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import { BrowserSessionStateFilePersistence } from './workstation-browser-session-state'
import { BROWSER_TASK_STATE_VERSION, type BrowserOwnerReceipt, type BrowserTaskSnapshot } from './workstation-browser-task'

const roots: string[] = []
afterEach(() => {
  for (const root of roots.splice(0)) {fs.rmSync(root, { recursive: true, force: true })}
})

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-p01-'))
  roots.push(root)
  const file = path.join(root, 'browser-session.json')
  const store = new BrowserSessionStateFilePersistence(file)
  store.load()
  const task = {
    taskId: 'task-p01',
    createdAt: new Date().toISOString(),
    panelHost: null,
    controlHost: null,
    sessionHost: 'session-p01',
    kanbanCardId: null,
    runId: 'run-p01',
    localConnection: null,
    status: 'parked' as const,
    leaseState: null,
    parked: true,
    recoveryState: 'restored' as const,
    updatedAt: new Date().toISOString()
  }
  const tasks: BrowserTaskSnapshot = { version: BROWSER_TASK_STATE_VERSION, browserTaskCounter: 1, tasks: [task] }
  store.browserTaskPersistence().save(tasks)
  const admission = {
    operationId: 'op-p01', taskId: 'task-p01', sessionId: 'session-p01', runId: 'run-p01',
    tabId: 'tab-p01', action: 'browser_batch_actions', argumentsDigest: 'a'.repeat(64)
  }
  assert.equal(store.admitBrowserMutation(admission), 'admitted')
  const child: BrowserOwnerReceipt = {
    operationId: 'op-p01:1', taskId: 'task-p01', browserTaskId: 'task-p01',
    runId: 'run-p01', tabId: 'tab-p01', action: 'browser_type',
    revision: 2, safeUrl: 'https://example.test/', executedAt: new Date().toISOString()
  }
  store.browserTaskPersistence().save({
    ...tasks, tasks: [{ ...task, revision: 2, lastReceipt: child }]
  })
  store.saveSession([{
    id: 'tab-p01', browserTaskId: 'task-p01', safeUrl: 'https://example.test/',
    safeTitle: null, recoveryPolicy: 'browser-task-lazy',
    recoveryState: 'restored', recoveryReason: 'process-restart'
  }], 'tab-p01', { 'task-p01': child })
  const parent: BrowserOwnerReceipt = {
    ...child, operationId: 'op-p01', action: 'browser_batch_actions', revision: 0
  }
  const refs = ['op-p01:0:tab-p01:1', 'op-p01:1:tab-p01:2']
  return { store, file, parent, refs }
}

test('P01: complete parent persists child audit refs and releases only the matching run after restart', () => {
  const { store, file, parent, refs } = fixture()
  const saved = store.completeVerifiedBatch({ receipt: parent, sessionId: 'session-p01', stepReceiptRefs: refs })
  assert.equal(saved.operationId, 'op-p01')
  const reopened = new BrowserSessionStateFilePersistence(file)
  const state = reopened.load()
  assert.equal(state?.operationAdmissions?.['op-p01']?.acknowledged, true)
  assert.deepEqual(state?.operationAdmissions?.['op-p01']?.batchStepReceiptRefs, refs)
  assert.equal(state?.receipts?.['task-p01']?.operationId, 'op-p01')
  assert.equal(reopened.pendingBrowserMutation('task-p01', 'session-p01', 'run-p01'), null)
  assert.equal(reopened.admitBrowserMutation({ operationId: 'op-next', taskId: 'task-p01',
    sessionId: 'session-p01', runId: 'run-p01', tabId: 'tab-p01',
    action: 'browser_navigate', argumentsDigest: 'b'.repeat(64) }), 'admitted')
})

test('P01: partial child receipt, wrong run and wrong tab never acknowledge the parent', () => {
  const { store, file, parent, refs } = fixture()
  assert.throws(() => store.completeVerifiedBatch({
    receipt: parent, sessionId: 'session-p01', stepReceiptRefs: [refs[0]]
  }), /owner_or_evidence_mismatch/)
  assert.throws(() => store.completeVerifiedBatch({
    receipt: { ...parent, runId: 'run-other' }, sessionId: 'session-p01', stepReceiptRefs: refs
  }), /owner_or_evidence_mismatch/)
  assert.throws(() => store.completeVerifiedBatch({
    receipt: { ...parent, tabId: 'tab-other' }, sessionId: 'session-p01', stepReceiptRefs: refs
  }), /invalid_batch_completion_evidence|owner_or_evidence_mismatch/)
  const reopened = new BrowserSessionStateFilePersistence(file)
  assert.equal(reopened.pendingBrowserMutation('task-p01', 'session-p01', 'run-p01'), 'op-p01')
  assert.equal(reopened.load()?.operationAdmissions?.['op-p01']?.acknowledged, undefined)
})

test('P01: fsync failure refuses verified completion and keeps this process fail-closed', () => {
  const { file, parent, refs } = fixture()
  const failing = new BrowserSessionStateFilePersistence(file, null, {
    ...fs, fsyncSync: () => {throw new Error('simulated fsync failure')}
  } as typeof fs)
  assert.throws(() => failing.completeVerifiedBatch({
    receipt: parent, sessionId: 'session-p01', stepReceiptRefs: refs
  }), /browser_batch_parent_not_durable/)
  assert.equal(new BrowserSessionStateFilePersistence(file).load()?.operationAdmissions?.['op-p01']?.acknowledged,
    undefined, 'a failed fsync must not publish the parent ACK even after restart')
  assert.throws(() => failing.admitBrowserMutation({
    operationId: 'op-after-fsync', taskId: 'task-p01', sessionId: 'session-p01',
    runId: 'run-p01', tabId: 'tab-p01', action: 'browser_navigate',
    argumentsDigest: 'b'.repeat(64)
  }), /browser_admission_persistence_unavailable/)
})

test('P01: concurrent admission lock and corrupt snapshot fail closed', () => {
  const { store, file, parent, refs } = fixture()
  fs.writeFileSync(file + '.admission.lock', 'synthetic lock')
  assert.throws(() => store.completeVerifiedBatch({
    receipt: parent, sessionId: 'session-p01', stepReceiptRefs: refs
  }), /browser_admission_concurrent_reconciliation_required/)
  assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).operationAdmissions['op-p01'].acknowledged, undefined)
  fs.rmSync(file + '.admission.lock')
  fs.writeFileSync(file, '{invalid-json')
  const reopened = new BrowserSessionStateFilePersistence(file)
  assert.throws(() => reopened.completeVerifiedBatch({
    receipt: parent, sessionId: 'session-p01', stepReceiptRefs: refs
  }), /browser_batch_state_unavailable/)
})


test('P01: stale Browser writer cannot erase verified batch child audit history', () => {
  const { store, file, parent, refs } = fixture()
  const stale = new BrowserSessionStateFilePersistence(file)
  const before = stale.load()
  assert.ok(before)

  store.completeVerifiedBatch({ receipt: parent, sessionId: 'session-p01', stepReceiptRefs: refs })
  stale.saveSession(before.tabs, before.activeTabId, before.receipts)

  const after = new BrowserSessionStateFilePersistence(file).load()
  assert.equal(after?.operationAdmissions?.['op-p01']?.acknowledged, true)
  assert.deepEqual(after?.operationAdmissions?.['op-p01']?.batchStepReceiptRefs, refs)
})
