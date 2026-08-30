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

test('safe URL metadata strips query/fragment and rejects credential-bearing or opaque paths', () => {
  assert.equal(
    safeRestorableUrlMetadata('https://example.test/account?token=page-secret#session-secret'),
    'https://example.test/account'
  )
  assert.equal(safeRestorableUrlMetadata('https://example.test/docs?q=ordinary-search'), 'https://example.test/docs')
  assert.equal(safeRestorableUrlMetadata('https://user:password@example.test/private'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/reset/client_secret/value'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/aBcdEfghIjklMnopQrstuVwxyz123456'), null)
  assert.equal(safeRestorableUrlMetadata('https://example.test/abcdefghijklmnopqrstuvwxyzabcdef'), null)
  assert.equal(safeRestorableUrlMetadata('file:///C:/Users/example/secret.txt'), null)
})

test('safe title metadata accepts bounded display text and rejects secret/page-content shapes', () => {
  assert.equal(safeTitleMetadata('Example Domain — Dashboard'), 'Example Domain — Dashboard')
  assert.equal(safeTitleMetadata('Access token = page-secret'), null)
  assert.equal(safeTitleMetadata('OAuth code: 123456'), null)
  assert.equal(safeTitleMetadata('user@example.test — Account'), null)
  assert.equal(safeTitleMetadata('eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature123456'), null)
  assert.equal(safeTitleMetadata(`Title ${'a'.repeat(200)}`), null)
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
