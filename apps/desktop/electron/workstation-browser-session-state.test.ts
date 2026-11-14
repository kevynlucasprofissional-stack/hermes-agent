import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import {
  BROWSER_SESSION_STATE_VERSION,
  BrowserSessionStateFilePersistence,
  type BrowserSessionStateSnapshot,
  type BrowserSessionTab,
  emptyBrowserSessionState,
  normalizeBrowserSessionState,
  safeRestorableUrlMetadata,
  safeTitleMetadata
} from './workstation-browser-session-state'
import { BROWSER_TASK_STATE_VERSION, type BrowserTaskSnapshot } from './workstation-browser-task'

const tempRoots: string[] = []
afterEach(() => {
  for (const root of tempRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

function tempFiles(): { root: string; stateFile: string; legacyTaskFile: string } {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-browser-session-'))
  tempRoots.push(root)

  return {
    root,
    stateFile: path.join(root, 'browser-session.json'),
    legacyTaskFile: path.join(root, 'browser-tasks.json')
  }
}

function browserTaskSnapshot(taskIds: string[] = []): BrowserTaskSnapshot {
  return {
    version: BROWSER_TASK_STATE_VERSION,
    browserTaskCounter: taskIds.length,
    tasks: taskIds.map((taskId, index) => ({
      taskId,
      createdAt: `2026-08-30T10:00:0${index}.000Z`,
      panelHost: null,
      controlHost: null,
      sessionHost: `hermes-session-${index}`,
      kanbanCardId: null,
      runId: null,
      localConnection: null,
      status: 'parked',
      leaseState: null,
      parked: true,
      recoveryState: 'restored',
      updatedAt: `2026-08-30T10:00:0${index}.000Z`
    }))
  }
}

function tab(id: string, overrides: Partial<BrowserSessionTab> = {}): BrowserSessionTab {
  return {
    id,
    browserTaskId: null,
    safeUrl: 'about:blank',
    safeTitle: 'New Tab',
    recoveryPolicy: 'restore-safe-url',
    recoveryState: 'live',
    recoveryReason: null,
    ...overrides
  }
}

function snapshot(tabs: BrowserSessionTab[], browserTasks = browserTaskSnapshot()): BrowserSessionStateSnapshot {
  return {
    version: BROWSER_SESSION_STATE_VERSION,
    savedAt: '2026-08-30T12:00:00.000Z',
    activeTabId: tabs[0]?.id ?? null,
    tabs,
    browserTasks
  }
}

test('safe URL metadata strips credential data and rejects explicit authentication path classes', () => {
  assert.equal(
    safeRestorableUrlMetadata('https://example.test/account?token=page-secret#session-secret'),
    'https://example.test/account'
  )
  assert.equal(safeRestorableUrlMetadata('https://example.test/docs?q=ordinary-search'), 'https://example.test/docs')
  assert.equal(safeRestorableUrlMetadata('https://user:password@example.test/private'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/reset/client_secret/value'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/aBcdEfghIjklMnopQrstuVwxyz123456'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/abcdefghijklmnopqrstuvwxyzabcdef'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/recovery/code/482913'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/verification/code/482913'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/otp/482913'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/temporary/pin/482913'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/magic/login/code/482913'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/one-time/credential/482913'), null)
  assert.equal(safeRestorableUrlMetadata('file:///C:/Users/example/secret.txt'), null)
  assert.equal(
    safeRestorableUrlMetadata('https://example.test/customers/482913'),
    'https://example.test/customers/482913'
  )
})

test('durable title policy rejects all page-controlled titles without weakening URL identifiers', () => {
  assert.equal(safeTitleMetadata('Example Domain — Dashboard'), null)
  assert.equal(safeTitleMetadata('Access token = page-secret'), null)
  assert.equal(safeTitleMetadata('OAuth code: 123456'), null)
  assert.equal(safeTitleMetadata('user@example.test — Account'), null)
  assert.equal(safeTitleMetadata('eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature123456'), null)
  assert.equal(safeTitleMetadata('Customer 482913'), null)
})

test('adversarial credentials and every raw page title stay absent after serialization and reload', () => {
  const { stateFile } = tempFiles()
  const jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzZXNzaW9uLXNlY3JldCJ9.signatureSecret123456'

  const urlCases = [
    {
      id: 'query-access-token',
      value: 'https://example.test/account?access_token=query-access-token-secret',
      expected: 'https://example.test/account',
      forbidden: ['query-access-token-secret']
    },
    {
      id: 'oauth-code',
      value: 'https://example.test/callback?code=oauth-code-secret',
      expected: 'https://example.test/callback',
      forbidden: ['oauth-code-secret']
    },
    {
      id: 'fragment-token',
      value: 'https://example.test/complete#access_token=fragment-token-secret',
      expected: 'https://example.test/complete',
      forbidden: ['fragment-token-secret']
    },
    {
      id: 'userinfo-password',
      value: 'https://login-user:password-secret@example.test/private',
      expected: null,
      forbidden: ['login-user', 'password-secret']
    },
    {
      id: 'jwt',
      value: `https://example.test/session/${jwt}`,
      expected: null,
      forbidden: [jwt]
    },
    {
      id: 'presigned-url',
      value:
        'https://bucket.example.test/customers/482913?X-Amz-Credential=presigned-credential-secret&X-Amz-Signature=presigned-signature-secret',
      expected: 'https://bucket.example.test/customers/482913',
      forbidden: ['presigned-credential-secret', 'presigned-signature-secret']
    },
    {
      id: 'recovery-path',
      value: 'https://example.test/recovery/code/482913',
      expected: null,
      forbidden: ['/recovery/code/482913']
    },
    {
      id: 'verification-path',
      value: 'https://example.test/verification/code/482913',
      expected: null,
      forbidden: ['/verification/code/482913']
    },
    {
      id: 'otp-path',
      value: 'https://example.test/otp/482913',
      expected: null,
      forbidden: ['/otp/482913']
    },
    {
      id: 'pin-path',
      value: 'https://example.test/temporary/pin/482913',
      expected: null,
      forbidden: ['/temporary/pin/482913']
    },
    {
      id: 'magic-code-path',
      value: 'https://example.test/magic/login/code/482913',
      expected: null,
      forbidden: ['/magic/login/code/482913']
    }
  ] as const

  const forbiddenTitles = [
    'Recovery code 482913',
    'Verification code 482913',
    'OTP 482913',
    'Temporary PIN 482913',
    'Magic login code 482913'
  ]

  const deliberatelyNonSecretTitles = ['Example Domain — Dashboard', 'Customer 482913']

  for (const candidate of urlCases) {
    assert.equal(safeRestorableUrlMetadata(candidate.value), candidate.expected)
  }

  for (const title of [...forbiddenTitles, ...deliberatelyNonSecretTitles]) {
    assert.equal(safeTitleMetadata(title), null)
  }

  const persistence = new BrowserSessionStateFilePersistence(stateFile)
  persistence.load()
  persistence.saveSession(
    [
      ...urlCases.map(candidate => tab(candidate.id, { safeUrl: candidate.value, safeTitle: null })),
      ...[...forbiddenTitles, ...deliberatelyNonSecretTitles].map((title, index) =>
        tab(`title-${index}`, { safeUrl: 'https://example.test/harmless', safeTitle: title })
      )
    ],
    'query-access-token'
  )

  const serialized = fs.readFileSync(stateFile, 'utf-8')

  for (const candidate of urlCases) {
    for (const forbidden of candidate.forbidden) {
      assert.equal(serialized.includes(forbidden), false)
    }
  }

  for (const title of [...forbiddenTitles, ...deliberatelyNonSecretTitles]) {
    assert.equal(serialized.includes(title), false)
  }

  const reloaded = new BrowserSessionStateFilePersistence(stateFile).load()
  assert.ok(reloaded)
  assert.equal(
    reloaded.tabs.every(candidate => candidate.safeTitle === null),
    true
  )
  const reserialized = JSON.stringify(reloaded)

  for (const candidate of urlCases) {
    for (const forbidden of candidate.forbidden) {
      assert.equal(reserialized.includes(forbidden), false)
    }
  }

  for (const title of forbiddenTitles) {
    assert.equal(reserialized.includes(title), false)
  }

  assert.equal(reloaded.tabs.find(candidate => candidate.id === 'presigned-url')?.safeUrl, urlCases[5].expected)
})

test('normalization excludes raw secret markers and process-shaped extra fields', () => {
  const raw = snapshot([
    {
      ...tab('ordinary-a'),
      safeUrl: 'https://example.test/account?access_token=page-secret#fragment-secret',
      safeTitle: 'Password = typed-password-secret',
      view: { webContents: { processId: 99 } }
    } as BrowserSessionTab
  ])

  const normalized = normalizeBrowserSessionState(raw)
  assert.ok(normalized)
  assert.equal(normalized.tabs[0].safeUrl, 'https://example.test/account')
  assert.equal(normalized.tabs[0].safeTitle, null)
  assert.equal(normalized.tabs[0].recoveryReason, 'unsafe-metadata')

  const persisted = JSON.stringify(normalized)
  assert.equal(persisted.includes('page-secret'), false)
  assert.equal(persisted.includes('fragment-secret'), false)
  assert.equal(persisted.includes('typed-password-secret'), false)
  assert.equal(persisted.includes('webContents'), false)
  assert.equal(persisted.includes('processId'), false)
})

test('unknown/corrupt versions fail closed and stale task relationships are reconciled', () => {
  assert.equal(normalizeBrowserSessionState({ version: 999 }), null)
  assert.equal(normalizeBrowserSessionState({ version: BROWSER_SESSION_STATE_VERSION, tabs: 'invalid' }), null)

  const tasks = browserTaskSnapshot(['task-a'])

  const normalized = normalizeBrowserSessionState({
    ...snapshot(
      [
        tab('ordinary-a'),
        tab('task-a-primary', { browserTaskId: 'task-a', recoveryPolicy: 'browser-task-lazy' }),
        tab('task-a-duplicate', { browserTaskId: 'task-a', recoveryPolicy: 'browser-task-lazy' }),
        tab('stale-task', { browserTaskId: 'missing-task', recoveryPolicy: 'browser-task-lazy' })
      ],
      tasks
    ),
    activeTabId: 'stale-task'
  })

  assert.ok(normalized)
  assert.deepEqual(
    normalized.tabs.map(candidate => candidate.id),
    ['ordinary-a', 'task-a-primary']
  )
  assert.equal(normalized.activeTabId, null)
})

test('atomic replacement failure preserves the previous valid snapshot and removes its temp file', () => {
  const { root, stateFile } = tempFiles()

  const persistence = new BrowserSessionStateFilePersistence(
    stateFile,
    null,
    fs,
    () => new Date('2026-08-30T12:00:00.000Z')
  )

  persistence.load()
  persistence.saveSession([tab('ordinary-a')], 'ordinary-a')
  const before = fs.readFileSync(stateFile, 'utf-8')

  const failingIo = {
    ...fs,
    renameSync: () => {
      throw new Error('simulated atomic rename failure')
    }
  }

  const failing = new BrowserSessionStateFilePersistence(
    stateFile,
    null,
    failingIo,
    () => new Date('2026-08-30T12:01:00.000Z')
  )

  assert.ok(failing.load())
  assert.throws(() => failing.saveSession([tab('ordinary-b')], 'ordinary-b'), /simulated atomic rename failure/)

  assert.equal(fs.readFileSync(stateFile, 'utf-8'), before)
  assert.deepEqual(
    fs.readdirSync(root).filter(name => name.endsWith('.tmp')),
    []
  )
})

test('legacy BrowserTask metadata migrates once into the composite state', () => {
  const { stateFile, legacyTaskFile } = tempFiles()
  const legacy = browserTaskSnapshot(['task-migrated'])
  fs.writeFileSync(legacyTaskFile, JSON.stringify(legacy))

  const persistence = new BrowserSessionStateFilePersistence(
    stateFile,
    legacyTaskFile,
    fs,
    () => new Date('2026-08-30T12:00:00.000Z')
  )

  const migrated = persistence.load()

  assert.ok(migrated)
  assert.deepEqual(
    migrated.browserTasks.tasks.map(task => task.taskId),
    ['task-migrated']
  )
  assert.equal(fs.existsSync(stateFile), true)
  assert.equal(fs.existsSync(legacyTaskFile), false)
  assert.equal(JSON.parse(fs.readFileSync(stateFile, 'utf-8')).version, BROWSER_SESSION_STATE_VERSION)
})

test('an existing unknown composite version is preserved and never falls back to stale legacy tasks', () => {
  const { stateFile, legacyTaskFile } = tempFiles()
  fs.writeFileSync(stateFile, JSON.stringify({ version: BROWSER_SESSION_STATE_VERSION + 1 }))
  fs.writeFileSync(legacyTaskFile, JSON.stringify(browserTaskSnapshot(['stale-task'])))

  const persistence = new BrowserSessionStateFilePersistence(stateFile, legacyTaskFile)
  assert.equal(persistence.load(), null)
  persistence.saveSession([tab('ordinary-new')], 'ordinary-new')
  assert.deepEqual(JSON.parse(fs.readFileSync(stateFile, 'utf-8')), {
    version: BROWSER_SESSION_STATE_VERSION + 1
  })
  assert.equal(fs.existsSync(legacyTaskFile), true)
})

test('empty state is versioned and contains BrowserTask identity linkage without page objects', () => {
  const state = emptyBrowserSessionState(() => new Date('2026-08-30T12:00:00.000Z'))
  assert.equal(state.version, BROWSER_SESSION_STATE_VERSION)
  assert.equal(state.browserTasks.version, BROWSER_TASK_STATE_VERSION)
  assert.deepEqual(state.tabs, [])
  assert.deepEqual(state.browserTasks.tasks, [])
})

test('composite state persists and normalizes kanbanCardId and runId identity linkages', () => {
  const { stateFile, legacyTaskFile } = tempFiles()
  const persistence = new BrowserSessionStateFilePersistence(stateFile, legacyTaskFile)

  const tasks: BrowserTaskSnapshot = {
    version: BROWSER_TASK_STATE_VERSION,
    browserTaskCounter: 1,
    tasks: [
      {
        taskId: 'task-kanban-link',
        createdAt: '2026-08-30T10:00:00.000Z',
        panelHost: null,
        controlHost: null,
        sessionHost: 'hermes-session-42',
        kanbanCardId: 'card-abc-123',
        runId: 'run-xyz-789',
        localConnection: null,
        status: 'parked',
        leaseState: null,
        parked: true,
        recoveryState: 'restored',
        updatedAt: '2026-08-30T10:00:00.000Z'
      }
    ]
  }

  persistence.browserTaskPersistence().save(tasks)
  const loaded = persistence.load()
  assert.ok(loaded)
  assert.equal(loaded.browserTasks.tasks[0]?.taskId, 'task-kanban-link')
  assert.equal(loaded.browserTasks.tasks[0]?.sessionHost, 'hermes-session-42')
  assert.equal(loaded.browserTasks.tasks[0]?.kanbanCardId, 'card-abc-123')
  assert.equal(loaded.browserTasks.tasks[0]?.runId, 'run-xyz-789')
})

test('BROW-N2 RED: uncertain batch outcome is durable, sanitized and still fences replay', () => {
  const { stateFile } = tempFiles()
  const persistence = new BrowserSessionStateFilePersistence(stateFile)
  const admission = {
    operationId: 'op-batch-uncertain-n2', taskId: 'task-n2', sessionId: 'session-n2',
    runId: 'run-n2', tabId: 'tab-n2', action: 'browser_batch_actions',
    argumentsDigest: 'a'.repeat(64)
  }
  assert.equal(persistence.admitBrowserMutation(admission), 'admitted')
  persistence.recordBatchUncertainty({
    operationId: admission.operationId, reason: 'selection_postcondition_not_observed',
    stoppedAt: 0, completedSteps: 1, verifiedSteps: 0
  })
  const fresh = new BrowserSessionStateFilePersistence(stateFile)
  const pending = fresh.listPendingAdmissions('task-n2')
  assert.equal(pending.length, 1)
  assert.equal(pending[0].uncertainty?.reason, 'selection_postcondition_not_observed')
  assert.equal(pending[0].uncertainty?.completedSteps, 1)
  assert.equal(fresh.pendingBrowserMutation('task-n2','session-n2','run-n2'), admission.operationId)
  const stale = new BrowserSessionStateFilePersistence(stateFile)
  stale.saveSession([], null)
  assert.equal(new BrowserSessionStateFilePersistence(stateFile).listPendingAdmissions('task-n2')[0].uncertainty?.reason,
    'selection_postcondition_not_observed', 'stale projection must not erase diagnostic metadata')
  assert.throws(() => fresh.recordBatchUncertainty({
    operationId: admission.operationId, reason: 'phone=+55_SECRET',
    stoppedAt: 0, completedSteps: 1, verifiedSteps: 0
  }), /invalid_batch_uncertainty/)
})

test('BROW-N2 RED: stale writer cannot erase an operator reconciliation terminal', () => {
  const { stateFile } = tempFiles()
  const owner = new BrowserSessionStateFilePersistence(stateFile)
  const admission = {
    operationId: 'op-immutable-terminal-n2', taskId:'task-terminal-n2',
    sessionId:'session-terminal-n2', runId:'run-terminal-n2',
    tabId:'tab-terminal-n2', action:'browser_batch_actions',
    argumentsDigest:'b'.repeat(64)
  }
  assert.equal(owner.admitBrowserMutation(admission),'admitted')
  owner.recordBatchUncertainty({operationId:admission.operationId,reason:'readback_unavailable',
    stoppedAt:0,completedSteps:1,verifiedSteps:0})
  const stale = new BrowserSessionStateFilePersistence(stateFile)
  stale.load()
  owner.reconcilePendingAdmission({operationId:admission.operationId,
    reason:'OPERATOR_RECONCILED',evidence:'OPERATOR_REVIEW',
    evidenceDetails:'SYNTHETIC_REVIEW_ONLY',resolvedBy:'synthetic-operator'})
  stale.saveSession([],null)
  const loaded = new BrowserSessionStateFilePersistence(stateFile).load()
  assert.equal(loaded?.operationAdmissions?.[admission.operationId]?.terminal?.kind,'RECONCILED')
  assert.equal(loaded?.operationAdmissions?.[admission.operationId]?.uncertainty?.reason,'readback_unavailable')
  assert.equal(new BrowserSessionStateFilePersistence(stateFile).listPendingAdmissions('task-terminal-n2').length,0)
})

test('P0 automatic safe recovery of legacy invalid browser batch is durable, scoped and idempotent', () => {
  const {stateFile} = tempFiles()
  const store = new BrowserSessionStateFilePersistence(stateFile)
  const taskId = 'task-legacy-invalid'
  const sessionId = 'session-legacy-invalid'
  const runId = 'run-legacy-invalid'
  const tabId = 'tab-legacy-invalid'
  const initial = snapshot([tab(tabId,{browserTaskId:taskId})],browserTaskSnapshot([taskId]))
  initial.browserTasks.tasks[0].sessionHost=sessionId
  initial.browserTasks.tasks[0].runId=runId
  ;(store as unknown as {save:(state:BrowserSessionStateSnapshot)=>unknown}).save(initial)
  const operationId='op-invalid-legacy-batch'
  assert.equal(store.admitBrowserMutation({operationId,taskId,sessionId,runId,tabId,
    action:'browser_batch_actions',argumentsDigest:'1'.repeat(64)}),'admitted')
  store.recordBatchUncertainty({operationId,reason:'invalid_step',
    stoppedAt:0,completedSteps:0,verifiedSteps:0})
  const restarted = new BrowserSessionStateFilePersistence(stateFile)
  assert.equal(restarted.pendingBrowserMutation('other-task',sessionId,runId),null)
  assert.equal(restarted.listPendingAdmissions(taskId).length,1)
  assert.equal(restarted.pendingBrowserMutation(taskId,sessionId,runId),null)
  const terminal = new BrowserSessionStateFilePersistence(stateFile).load()?.operationAdmissions?.[operationId]?.terminal
  assert.equal(terminal?.kind,'NOT_DISPATCHED')
  assert.equal(terminal?.reason,'EVIDENCE_RECONCILED')
  assert.equal(terminal?.resolvedBy,'browser-preflight-auto-recovery')
  assert.equal(restarted.pendingBrowserMutation(taskId,sessionId,runId),null)
  assert.equal(restarted.listPendingAdmissions(taskId).length,0)
  // Immutable terminal is preserved even if an older projection is re-saved.
  store.saveSession([],null)
  assert.equal(new BrowserSessionStateFilePersistence(stateFile).load()?.operationAdmissions?.[operationId]?.terminal?.kind,
    'NOT_DISPATCHED')
})

test('P0 automatic recovery refuses any possibility of a dispatched browser effect', () => {
  for(const [reason,completed,verified,withReceipt] of [
    ['click_postcondition_not_observed',1,0,false],
    ['effect_state_unknown',0,0,false],
    ['invalid_step',1,0,false],
    ['invalid_step',0,0,true]
  ] as const) {
    const {stateFile}=tempFiles()
    const store=new BrowserSessionStateFilePersistence(stateFile)
    const taskId='task-safety'
    const sessionId='session-safety'
    const runId='run-safety'
    const tabId='tab-safety'
    const initial=snapshot([tab(tabId,{browserTaskId:taskId})],browserTaskSnapshot([taskId]))
    initial.browserTasks.tasks[0].sessionHost=sessionId
    initial.browserTasks.tasks[0].runId=runId
    const operationId='op-safety-batch'
    if(withReceipt) {
      initial.browserTasks.tasks[0].lastReceipt={
        operationId:operationId+':0',taskId,runId,browserTaskId:taskId,tabId,revision:1,
        action:'browser_click',safeUrl:null,executedAt:new Date().toISOString()
      }
    }
    ;(store as unknown as {save:(state:BrowserSessionStateSnapshot)=>unknown}).save(initial)
    assert.equal(store.admitBrowserMutation({operationId,taskId,sessionId,runId,tabId,
      action:'browser_batch_actions',argumentsDigest:'2'.repeat(64)}),'admitted')
    store.recordBatchUncertainty({operationId,reason,stoppedAt:0,completedSteps:completed,verifiedSteps:verified})
    assert.equal(new BrowserSessionStateFilePersistence(stateFile).pendingBrowserMutation(taskId,sessionId,runId),
      operationId,reason+' has effect risk and must not auto-recover')
    assert.equal(store.load()?.operationAdmissions?.[operationId]?.terminal,undefined)
  }
})