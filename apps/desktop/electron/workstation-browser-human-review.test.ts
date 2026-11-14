import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { test } from 'vitest'

import { sameNavigationReview, verifiedNavigationCandidate, uncertainBatchReviewCandidate } from './workstation-browser-human-review'
import { BrowserSessionStateFilePersistence, type BrowserSessionStateSnapshot } from './workstation-browser-session-state'

const op = 'op-local-nav'
const url = 'https://example.test/safe'
function fixture(): BrowserSessionStateSnapshot {
  const receipt = {operationId:op,taskId:'task-a',runId:'run-a',browserTaskId:'task-a',
    tabId:'tab-a',revision:1,action:'browser_navigate',safeUrl:url,executedAt:'2026-10-29T12:00:00Z'}
  return {version:1,savedAt:'2026-10-29T12:00:00Z',activeTabId:'tab-a',
    tabs:[{id:'tab-a',browserTaskId:'task-a',safeUrl:url,safeTitle:'Test',
      recoveryPolicy:'browser-task-lazy',recoveryState:'live',recoveryReason:null}],
    browserTasks:{version:1,browserTaskCounter:1,tasks:[{
      taskId:'task-a',createdAt:'2026-10-29T12:00:00Z',panelHost:null,controlHost:null,
      sessionHost:'session-a',kanbanCardId:null,runId:'run-a',localConnection:null,
      status:'visible',leaseState:null,parked:false,recoveryState:'fresh',
      updatedAt:'2026-10-29T12:00:00Z',lastReceipt:receipt}]},
    operationAdmissions:{[op]:{
      operationId:op,taskId:'task-a',sessionId:'session-a',runId:'run-a',tabId:'tab-a',
      action:'browser_navigate',argumentsDigest:'a'.repeat(64)}}}
}
test('review requires exact receipt, owner and live local readback; never approves WhatsApp or batch', () => {
  const snap=fixture()
  const readback={url,webContentsId:100}
  const accepted=verifiedNavigationCandidate(snap,op,readback)
  assert.ok(accepted)
  assert.equal(verifiedNavigationCandidate(snap,op,{url:'about:blank',webContentsId:100}),null)
  assert.equal(verifiedNavigationCandidate(snap,'other',readback),null)
  const wrongRun=structuredClone(snap)
  wrongRun.browserTasks.tasks[0].runId='other'
  assert.equal(verifiedNavigationCandidate(wrongRun,op,readback),null)
  const batch=structuredClone(snap)
  batch.operationAdmissions![op].action='browser_batch_actions'
  assert.equal(verifiedNavigationCandidate(batch,op,readback),null)
  const external=structuredClone(snap)
  external.tabs[0].safeUrl='https://web.whatsapp.com'
  external.browserTasks.tasks[0].lastReceipt!.safeUrl='https://web.whatsapp.com'
  assert.equal(verifiedNavigationCandidate(external,op,{url:'https://web.whatsapp.com',webContentsId:100}),null)
  assert.equal(sameNavigationReview(accepted.review,{...accepted.review,webContentsId:200}),false)
})
test('reconciliation is CAS single use under exclusive durable store lock',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-human-review-'))
  try {
    const store=new BrowserSessionStateFilePersistence(path.join(root,'browser-session.json'))
    const s=fixture()
    // Simulate a legacy/crash snapshot: durable receipt exists but ACK was not committed.
    fs.writeFileSync(path.join(root, 'browser-session.json'), JSON.stringify(s), 'utf8')
    const prior=s.operationAdmissions![op]
    const receipt=s.browserTasks.tasks[0].lastReceipt!
    const req={operationId:op,reason:'EVIDENCE_RECONCILED' as const,evidence:'RECEIPT_PROVEN' as const,
      resolvedBy:'desktop-human-native-dialog',requirePending:true,expectedAdmission:prior,
      expectedNavigationReceipt:{operationId:receipt.operationId,taskId:receipt.taskId,
        runId:receipt.runId,tabId:receipt.tabId,safeUrl:receipt.safeUrl,action:receipt.action}}
    assert.throws(()=>store.reconcilePendingAdmission({...req,expectedAdmission:{...prior,runId:'wrong'}}),
      /browser_reconciliation_identity_changed/)
    assert.equal(store.load()?.operationAdmissions?.[op]?.terminal,undefined)
    assert.equal(store.reconcilePendingAdmission(req).reconciled,true)
    assert.equal(store.load()?.operationAdmissions?.[op]?.terminal?.evidence,'RECEIPT_PROVEN')
    assert.throws(()=>store.reconcilePendingAdmission(req),/browser_reconciliation_already_finalized/)
  } finally {fs.rmSync(root,{recursive:true,force:true})}
})

test('review denies an active human lease, stale page and a changed BrowserTask revision', () => {
  const snap=fixture()
  const readback={url,webContentsId:100}
  const leaseSnap=structuredClone(snap)
  leaseSnap.browserTasks.tasks[0].humanControlLease={
    owner:'human',taskId:'task-a',sessionId:'session-a',tabId:'tab-a',pageId:100,
    profileScope:'test',acquiredAt:'2026-10-29T12:00:00Z',
    expiresAt:'2026-10-29T18:00:00Z',renewedAt:null
  }
  assert.equal(verifiedNavigationCandidate(leaseSnap,op,readback),null)
  const staleSnap=structuredClone(snap)
  staleSnap.tabs[0].recoveryState='stale'
  assert.equal(verifiedNavigationCandidate(staleSnap,op,readback),null)
  const initial=verifiedNavigationCandidate(snap,op,readback)
  assert.ok(initial)
  const revisionSnap=structuredClone(snap)
  revisionSnap.browserTasks.tasks[0].revision=2
  const revised=verifiedNavigationCandidate(revisionSnap,op,readback)
  assert.ok(revised)
  assert.equal(sameNavigationReview(initial.review,revised.review),false)
})

test('durable reconciliation refuses changed task revision and new human lease under lock',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-human-lease-cas-'))
  try {
    const base=fixture()
    const prior=base.operationAdmissions![op]
    const receipt=base.browserTasks.tasks[0].lastReceipt!
    const request={operationId:op,reason:'EVIDENCE_RECONCILED' as const,
      evidence:'RECEIPT_PROVEN' as const,requirePending:true,
      expectedAdmission:prior,expectedTaskRevision:0,requireNoHumanLease:true,
      expectedNavigationReceipt:{operationId:receipt.operationId,taskId:receipt.taskId,
        runId:receipt.runId,tabId:receipt.tabId,safeUrl:receipt.safeUrl,action:receipt.action}}
    const changed=structuredClone(base)
    changed.browserTasks.tasks[0].revision=5
    fs.writeFileSync(path.join(root,'browser-session.json'),JSON.stringify(changed),'utf8')
    const fresh=new BrowserSessionStateFilePersistence(path.join(root,'browser-session.json'))
    assert.throws(()=>fresh.reconcilePendingAdmission(request),/browser_navigation_task_state_changed/)
    assert.equal(fresh.load()?.operationAdmissions?.[op]?.terminal,undefined)
    const leased=structuredClone(base)
    leased.browserTasks.tasks[0].humanControlLease={
      owner:'human',taskId:'task-a',sessionId:'session-a',tabId:'tab-a',pageId:100,
      profileScope:'test',acquiredAt:'2026-10-29T12:00:00Z',
      expiresAt:'2026-10-29T18:00:00Z',renewedAt:null
    }
    fs.writeFileSync(path.join(root,'browser-session.json'),JSON.stringify(leased),'utf8')
    assert.throws(()=>new BrowserSessionStateFilePersistence(path.join(root,'browser-session.json'))
      .reconcilePendingAdmission(request),/browser_navigation_task_state_changed/)
  }finally{fs.rmSync(root,{recursive:true,force:true})}
})

test('fsync failure cannot publish a reconciled terminal before durable commit',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-human-fsync-'))
  try{
    const target=path.join(root,'browser-session.json')
    const base=fixture()
    fs.writeFileSync(target,JSON.stringify(base),'utf8')
    const io={...fs,fsyncSync:(_fd:number)=>{throw new Error('simulated-flush-failure')}}
    const store=new BrowserSessionStateFilePersistence(target,null,io)
    const prior=base.operationAdmissions![op]
    const rec=base.browserTasks.tasks[0].lastReceipt!
    const request={operationId:op,reason:'EVIDENCE_RECONCILED' as const,
      evidence:'RECEIPT_PROVEN' as const,requirePending:true,
      expectedAdmission:prior,expectedTaskRevision:0,requireNoHumanLease:true,
      expectedNavigationReceipt:{operationId:rec.operationId,taskId:rec.taskId,runId:rec.runId,
        tabId:rec.tabId,safeUrl:rec.safeUrl,action:rec.action}}
    assert.throws(()=>store.reconcilePendingAdmission(request),/browser_admission_persistence_unavailable/)
    const persisted=JSON.parse(fs.readFileSync(target,'utf8')) as BrowserSessionStateSnapshot
    assert.equal(persisted.operationAdmissions?.[op]?.terminal,undefined)
  }finally{fs.rmSync(root,{recursive:true,force:true})}
})

test('a second writer cannot reconcile while another writer owns the admission lock',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-human-concurrent-'))
  const file=path.join(root,'browser-session.json')
  const lock=file+'.admission.lock'
  let handle:number|null=null
  try {
    const state=fixture()
    fs.writeFileSync(file,JSON.stringify(state),'utf8')
    const prior=state.operationAdmissions![op]
    const receipt=state.browserTasks.tasks[0].lastReceipt!
    const request={operationId:op,reason:'EVIDENCE_RECONCILED' as const,
      evidence:'RECEIPT_PROVEN' as const,requirePending:true,
      expectedAdmission:prior,expectedTaskRevision:0,requireNoHumanLease:true,
      expectedNavigationReceipt:{operationId:receipt.operationId,taskId:receipt.taskId,
        runId:receipt.runId,tabId:receipt.tabId,safeUrl:receipt.safeUrl,action:receipt.action}}
    handle=fs.openSync(lock,'wx')
    assert.throws(()=>new BrowserSessionStateFilePersistence(file).reconcilePendingAdmission(request),
      /browser_admission_concurrent_reconciliation_required/)
    assert.equal(JSON.parse(fs.readFileSync(file,'utf8')).operationAdmissions[op].terminal,undefined)
    fs.closeSync(handle);handle=null;fs.rmSync(lock)
    assert.equal(new BrowserSessionStateFilePersistence(file).reconcilePendingAdmission(request).reconciled,true)
  } finally {
    if(handle!==null){fs.closeSync(handle)}
    fs.rmSync(root,{recursive:true,force:true})
  }
})

test('after prepublication fsync a second sync failure cannot report uncertain reconciliation',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-human-double-fsync-'))
  try{
    const file=path.join(root,'browser-session.json')
    const state=fixture()
    fs.writeFileSync(file,JSON.stringify(state),'utf8')
    let syncCount=0
    const io={...fs,fsyncSync:(fd:number)=>{syncCount++;if(syncCount===2){throw new Error('second-fsync-failed')}fs.fsyncSync(fd)}}
    const store=new BrowserSessionStateFilePersistence(file,null,io)
    const prior=state.operationAdmissions![op]
    const receipt=state.browserTasks.tasks[0].lastReceipt!
    const req={operationId:op,reason:'EVIDENCE_RECONCILED' as const,
      evidence:'RECEIPT_PROVEN' as const,requirePending:true,
      expectedTaskRevision:0,requireNoHumanLease:true,expectedAdmission:prior,
      expectedNavigationReceipt:{operationId:receipt.operationId,taskId:receipt.taskId,
        runId:receipt.runId,tabId:receipt.tabId,safeUrl:receipt.safeUrl,action:receipt.action}}
    assert.equal(store.reconcilePendingAdmission(req).reconciled,true)
    assert.equal(syncCount,1)
    assert.equal(JSON.parse(fs.readFileSync(file,'utf8')).operationAdmissions[op].terminal.kind,'RECONCILED')
  }finally{fs.rmSync(root,{recursive:true,force:true})}
})

test('a restored uncertain batch is reconciled only by a pinned operator review, never by a replay', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-batch-restored-review-'))
  try {
    const s = fixture()
    s.tabs[0].recoveryState = 'restored'
    const prior = s.operationAdmissions![op]
    prior.action = 'browser_batch_actions'
    prior.uncertainty = {
      reason: 'click_postcondition_not_observed', stoppedAt: 0, completedSteps: 1,
      verifiedSteps: 0, recordedAt: '2026-11-01T18:36:09Z'
    }
    const review = uncertainBatchReviewCandidate(s, op, null)
    assert.ok(review)
    assert.equal(review.review.webContentsId, -1)
    const file = path.join(root, 'browser-session.json')
    fs.writeFileSync(file, JSON.stringify(s), 'utf8')
    const req = {operationId:op, reason:'OPERATOR_RECONCILED' as const,
      evidence:'OPERATOR_REVIEW' as const, requirePending:true,
      expectedAdmission:prior, expectedTaskRevision:0, requireNoHumanLease:true,
      resolvedBy:'desktop-human-native-dialog'}
    const store = new BrowserSessionStateFilePersistence(file)
    assert.throws(() => store.reconcilePendingAdmission({...req, expectedAdmission:{...prior, runId:'wrong'}}),
      /browser_reconciliation_identity_changed/)
    assert.equal(store.load()?.operationAdmissions?.[op]?.terminal, undefined)
    assert.equal(store.reconcilePendingAdmission(req).reconciled, true)
    assert.equal(store.load()?.operationAdmissions?.[op]?.terminal?.evidence, 'OPERATOR_REVIEW')
    assert.throws(() => store.reconcilePendingAdmission(req), /browser_reconciliation_already_finalized/)
  } finally {
    fs.rmSync(root, {recursive:true, force:true})
  }
})
