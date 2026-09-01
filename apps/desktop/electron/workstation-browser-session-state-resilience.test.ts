import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import {
  BrowserSessionStateFilePersistence,
  type BrowserSessionTab,
  safeRestorableUrlMetadata
} from './workstation-browser-session-state'
import { BROWSER_TASK_STATE_VERSION, type BrowserTaskSnapshot } from './workstation-browser-task'

const tempRoots: string[] = []

afterEach(() => {
  for (const root of tempRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

function stateFile(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-browser-session-resilience-'))

  tempRoots.push(root)
  return path.join(root, 'browser-session.json')
}

function tab(id: string, safeUrl = 'about:blank'): BrowserSessionTab {
  return {
    id,
    browserTaskId: null,
    safeUrl,
    safeTitle: null,
    recoveryPolicy: 'restore-safe-url',
    recoveryState: 'live',
    recoveryReason: null
  }
}

function taskSnapshot(status: 'parked' | 'visible' = 'parked', taskIds = ['task-a']): BrowserTaskSnapshot {
  return {
    version: BROWSER_TASK_STATE_VERSION,
    browserTaskCounter: taskIds.length,
    tasks: taskIds.map((taskId, index) => ({
      taskId,
      createdAt: `2026-09-01T10:00:0${index}.000Z`,
      panelHost: null,
      controlHost: null,
      sessionHost: `hermes-session-${index}`,
      localConnection: null,
      status,
      leaseState: null,
      parked: status !== 'visible',
      recoveryState: status === 'visible' ? 'recreated' : 'restored',
      updatedAt: `2026-09-01T10:01:0${index}.000Z`
    }))
  }
}

function persistenceWithOneShotRenameFailure(filePath: string): {
  persistence: BrowserSessionStateFilePersistence
  failNextRename(): void
} {
  let shouldFailNextRename = false

  const io = {
    ...fs,
    renameSync: (...args: Parameters<typeof fs.renameSync>) => {
      if (shouldFailNextRename) {
        shouldFailNextRename = false
        throw new Error('simulated atomic rename failure')
      }

      fs.renameSync(...args)
    }
  }

  return {
    persistence: new BrowserSessionStateFilePersistence(
      filePath,
      null,
      io,
      () => new Date('2026-09-01T12:00:00.000Z')
    ),
    failNextRename(): void {
      shouldFailNextRename = true
    }
  }
}

function persistenceWithOneShotWriteFailure(filePath: string): {
  persistence: BrowserSessionStateFilePersistence
  failNextWrite(): void
} {
  let shouldFailNextWrite = false

  const io = {
    ...fs,
    writeFileSync: (...args: Parameters<typeof fs.writeFileSync>) => {
      if (shouldFailNextWrite) {
        shouldFailNextWrite = false
        throw new Error('simulated BrowserSessionState write failure')
      }

      return fs.writeFileSync(...args)
    }
  }

  return {
    persistence: new BrowserSessionStateFilePersistence(
      filePath,
      null,
      io,
      () => new Date('2026-09-01T12:00:00.000Z')
    ),
    failNextWrite(): void {
      shouldFailNextWrite = true
    }
  }
}

function readComposite(filePath: string): {
  activeTabId: string | null
  tabs: BrowserSessionTab[]
  browserTasks: BrowserTaskSnapshot
} {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
}

test('R1 failed BrowserTask write keeps latest intended task state for the next successful session save', () => {
  const filePath = stateFile()
  const fault = persistenceWithOneShotRenameFailure(filePath)
  const tasks = fault.persistence.browserTaskPersistence()

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a', 'https://example.test/a')], 'ordinary-a')
  tasks.save(taskSnapshot('parked'))

  const beforeFailure = fs.readFileSync(filePath, 'utf-8')
  fault.failNextRename()
  assert.throws(() => tasks.save(taskSnapshot('visible')), /simulated atomic rename failure/)

  // Atomic durability: a new process before any later successful write still
  // sees the last fully durable snapshot.
  assert.equal(fs.readFileSync(filePath, 'utf-8'), beforeFailure)
  const beforeRetry = new BrowserSessionStateFilePersistence(filePath).load()
  assert.equal(beforeRetry?.browserTasks.tasks[0]?.status, 'parked')

  // The original process must retain its newer intended BrowserTask snapshot so
  // an unrelated tab save cannot regress it back to the durable-old state.
  fault.persistence.saveSession([tab('ordinary-b', 'https://example.test/b')], 'ordinary-b')

  const converged = readComposite(filePath)
  assert.equal(converged.browserTasks.tasks[0]?.status, 'visible')
  assert.deepEqual(converged.tabs.map(candidate => candidate.id), ['ordinary-b'])
  assert.equal(converged.activeTabId, 'ordinary-b')

  const reloaded = new BrowserSessionStateFilePersistence(filePath).load()
  assert.equal(reloaded?.browserTasks.tasks[0]?.status, 'visible')
  assert.deepEqual(reloaded?.tabs.map(candidate => candidate.id), ['ordinary-b'])
})

test('R2 failed BrowserTask destroy cannot be resurrected by a later successful session save', () => {
  const filePath = stateFile()
  const fault = persistenceWithOneShotRenameFailure(filePath)
  const tasks = fault.persistence.browserTaskPersistence()

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a')], 'ordinary-a')
  tasks.save(taskSnapshot('parked'))

  fault.failNextRename()
  assert.throws(() => tasks.save(taskSnapshot('parked', [])), /simulated atomic rename failure/)
  assert.deepEqual(readComposite(filePath).browserTasks.tasks.map(task => task.taskId), ['task-a'])

  fault.persistence.saveSession([tab('ordinary-b')], 'ordinary-b')

  const converged = readComposite(filePath)
  assert.deepEqual(converged.browserTasks.tasks, [])
  assert.deepEqual(new BrowserSessionStateFilePersistence(filePath).load()?.browserTasks.tasks, [])
})

test('R3 failed session write keeps latest intended tabs for the next successful BrowserTask save', () => {
  const filePath = stateFile()
  const fault = persistenceWithOneShotRenameFailure(filePath)
  const tasks = fault.persistence.browserTaskPersistence()

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a', 'https://example.test/a')], 'ordinary-a')
  tasks.save(taskSnapshot('parked'))

  fault.failNextRename()
  assert.throws(
    () => fault.persistence.saveSession([tab('ordinary-b', 'https://example.test/b')], 'ordinary-b'),
    /simulated atomic rename failure/
  )
  assert.deepEqual(readComposite(filePath).tabs.map(candidate => candidate.id), ['ordinary-a'])

  tasks.save(taskSnapshot('visible'))

  const converged = readComposite(filePath)
  assert.deepEqual(converged.tabs.map(candidate => candidate.id), ['ordinary-b'])
  assert.equal(converged.activeTabId, 'ordinary-b')
  assert.equal(converged.browserTasks.tasks[0]?.status, 'visible')
})

test('R4 failed replacement leaves the previous complete file and cleans the temporary file', () => {
  const filePath = stateFile()
  const root = path.dirname(filePath)
  const fault = persistenceWithOneShotRenameFailure(filePath)

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a')], 'ordinary-a')
  const before = fs.readFileSync(filePath, 'utf-8')

  fault.failNextRename()
  assert.throws(() => fault.persistence.saveSession([tab('ordinary-b')], 'ordinary-b'), /simulated atomic rename failure/)

  assert.equal(fs.readFileSync(filePath, 'utf-8'), before)
  assert.deepEqual(
    fs.readdirSync(root).filter(name => name.endsWith('.tmp')),
    []
  )
  assert.deepEqual(new BrowserSessionStateFilePersistence(filePath).load()?.tabs.map(candidate => candidate.id), [
    'ordinary-a'
  ])
})

test('R5 next successful composite write converges disk to the complete latest intended projection', () => {
  const filePath = stateFile()
  const fault = persistenceWithOneShotRenameFailure(filePath)
  const tasks = fault.persistence.browserTaskPersistence()

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a')], 'ordinary-a')
  tasks.save(taskSnapshot('parked'))

  fault.failNextRename()
  assert.throws(() => tasks.save(taskSnapshot('visible')), /simulated atomic rename failure/)

  fault.failNextRename()
  assert.throws(
    () => fault.persistence.saveSession([tab('ordinary-b', 'https://example.test/b')], 'ordinary-b'),
    /simulated atomic rename failure/
  )

  // Both failed operations still advanced the process-local intended projection.
  // The next success must commit the union rather than whichever half was last durable.
  tasks.save(taskSnapshot('visible'))

  const fresh = new BrowserSessionStateFilePersistence(filePath).load()
  assert.equal(fresh?.browserTasks.tasks[0]?.status, 'visible')
  assert.deepEqual(fresh?.tabs.map(candidate => candidate.id), ['ordinary-b'])
  assert.equal(fresh?.activeTabId, 'ordinary-b')
})

test('a pre-rename write failure also retains latest intent without changing the durable file', () => {
  const filePath = stateFile()
  const fault = persistenceWithOneShotWriteFailure(filePath)
  const tasks = fault.persistence.browserTaskPersistence()

  fault.persistence.load()
  fault.persistence.saveSession([tab('ordinary-a')], 'ordinary-a')
  tasks.save(taskSnapshot('parked'))
  const before = fs.readFileSync(filePath, 'utf-8')

  fault.failNextWrite()
  assert.throws(() => tasks.save(taskSnapshot('visible')), /simulated BrowserSessionState write failure/)
  assert.equal(fs.readFileSync(filePath, 'utf-8'), before)
  assert.equal(new BrowserSessionStateFilePersistence(filePath).load()?.browserTasks.tasks[0]?.status, 'parked')

  fault.persistence.saveSession([tab('ordinary-b')], 'ordinary-b')
  const fresh = new BrowserSessionStateFilePersistence(filePath).load()
  assert.equal(fresh?.browserTasks.tasks[0]?.status, 'visible')
  assert.deepEqual(fresh?.tabs.map(candidate => candidate.id), ['ordinary-b'])
})

test('credential-like pathname parameters and parser-confusion URLs fail closed through serialization and reload', () => {
  const filePath = stateFile()
  const rejected = [
    'https://example.test/file;session=short_token',
    'https://example.test/file;token=12345',
    'https://example.test/file;code=12345',
    'https://example.test/file;credential=12345',
    'https://example.test/file;secret=12345',
    'https://example.test/file;password=12345',
    'https://example.test/file;passcode=12345',
    'https://example.test/file;pin=12345',
    'https://example.test/file;otp=12345',
    'http://example.test\\?token=12345',
    'https://example.test/path/%3Ftoken%3D12345',
    'https://example.test/path/%253Ftoken%253D12345',
    'https://example.test/login/12345',
    'https://example.test/login/code/12345',
    'https://example.test/login/token/abcdefgh',
    'https://example.test/oauth/token/abcdefgh',
    'https://example.test/callback/code/12345',
    'https://example.test/reset/password/12345678',
    'https://example.test/verification/pin/482913',
    'https://example.test/magic/link/abcdefgh',
    'https://example.test/recovery/482913',
    'https://example.test/verify/482913',
    'https://example.test/magic/482913'
  ]

  for (const value of rejected) {
    assert.equal(safeRestorableUrlMetadata(value), null, value)
  }

  const ordinaryCustomer = 'https://example.test/customers/482913'
  const ordinaryDocs = 'https://example.test/docs/code-style'

  assert.equal(safeRestorableUrlMetadata(ordinaryCustomer), ordinaryCustomer)
  assert.equal(safeRestorableUrlMetadata(ordinaryDocs), ordinaryDocs)

  const persistence = new BrowserSessionStateFilePersistence(filePath)

  persistence.load()
  persistence.saveSession(
    [
      ...rejected.map((value, index) => tab(`rejected-${index}`, value)),
      tab('ordinary-customer', ordinaryCustomer),
      tab('ordinary-docs', ordinaryDocs)
    ],
    'ordinary-customer'
  )

  const persisted = readComposite(filePath)

  for (let index = 0; index < rejected.length; index += 1) {
    assert.equal(persisted.tabs.find(candidate => candidate.id === `rejected-${index}`)?.safeUrl, null)
  }

  assert.equal(persisted.tabs.find(candidate => candidate.id === 'ordinary-customer')?.safeUrl, ordinaryCustomer)
  assert.equal(persisted.tabs.find(candidate => candidate.id === 'ordinary-docs')?.safeUrl, ordinaryDocs)

  const reloaded = new BrowserSessionStateFilePersistence(filePath).load()

  assert.ok(reloaded)
  for (let index = 0; index < rejected.length; index += 1) {
    assert.equal(reloaded.tabs.find(candidate => candidate.id === `rejected-${index}`)?.safeUrl, null)
  }

  assert.equal(reloaded.tabs.find(candidate => candidate.id === 'ordinary-customer')?.safeUrl, ordinaryCustomer)
  assert.equal(reloaded.tabs.find(candidate => candidate.id === 'ordinary-docs')?.safeUrl, ordinaryDocs)
})
