import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import {
  BrowserTaskFilePersistence,
  BrowserTaskLifecycle,
  type BrowserTaskBindings
} from './workstation-browser-task'

interface FakePage {
  id: number
  taskId: string
  url: string
  destroyed: boolean
  visible: boolean
  parked: boolean
}

function fakeBrowser() {
  const pages = new Map<string, FakePage>()
  let pageCounter = 0
  let destroyCalls = 0

  const bindings: BrowserTaskBindings<FakePage, { host: string }> = {
    ensurePage(taskId) {
      const existing = pages.get(taskId)
      if (existing && !existing.destroyed) return existing
      const page: FakePage = {
        id: ++pageCounter,
        taskId,
        url: 'about:blank',
        destroyed: false,
        visible: false,
        parked: true
      }
      pages.set(taskId, page)
      return page
    },
    pageForTask: taskId => pages.get(taskId) ?? null,
    pageIsAlive: page => !page.destroyed,
    showPage(_taskId, page) {
      page.visible = true
      page.parked = false
    },
    hidePage(_taskId, page) {
      page.visible = false
      page.parked = false
    },
    parkPage(_taskId, page) {
      page.visible = false
      page.parked = true
    },
    destroyPage(taskId, page) {
      destroyCalls += 1
      page.destroyed = true
      pages.delete(taskId)
    }
  }

  return {
    bindings,
    pages,
    pageCount: () => pageCounter,
    destroyCount: () => destroyCalls
  }
}

const tempRoots: string[] = []
afterEach(() => {
  for (const root of tempRoots.splice(0)) fs.rmSync(root, { recursive: true, force: true })
})

function tempStateFile(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-browser-task-'))
  tempRoots.push(root)
  return path.join(root, 'browser-tasks.json')
}

test('create -> hide -> show keeps the same live page and current URL', () => {
  const browser = fakeBrowser()
  const lifecycle = new BrowserTaskLifecycle(browser.bindings)

  lifecycle.createTask({ taskId: 'task-a' })
  const original = browser.pages.get('task-a')
  assert.ok(original)
  original.url = 'https://example.test/current'

  const hidden = lifecycle.hideTask('task-a')
  assert.equal(hidden.status, 'hidden')
  assert.equal(original.destroyed, false)

  const shown = lifecycle.showTask('task-a', { host: 'panel' })
  assert.equal(shown.status, 'visible')
  assert.equal(browser.pages.get('task-a'), original)
  assert.equal(browser.pages.get('task-a')?.url, 'https://example.test/current')
  assert.equal(browser.pageCount(), 1)
})

test('create -> park -> show keeps the same page identity', () => {
  const browser = fakeBrowser()
  const lifecycle = new BrowserTaskLifecycle(browser.bindings)

  lifecycle.createTask({ taskId: 'task-a' })
  const original = browser.pages.get('task-a')
  assert.ok(original)
  original.url = 'https://example.test/parked'

  const parked = lifecycle.parkTask('task-a')
  assert.equal(parked.status, 'parked')
  assert.equal(parked.parked, true)
  assert.equal(original.parked, true)

  lifecycle.showTask('task-a', { host: 'control' })
  assert.equal(browser.pages.get('task-a'), original)
  assert.equal(browser.pages.get('task-a')?.url, 'https://example.test/parked')
  assert.equal(browser.pageCount(), 1)
})

test('hide never destroys the page; destroy is explicit and removes the task', () => {
  const browser = fakeBrowser()
  const lifecycle = new BrowserTaskLifecycle(browser.bindings)

  lifecycle.createTask({ taskId: 'task-a' })
  lifecycle.hideTask('task-a')
  assert.equal(browser.destroyCount(), 0)
  assert.ok(lifecycle.task('task-a'))
  assert.ok(browser.pages.get('task-a'))

  assert.equal(lifecycle.destroyTask('task-a'), true)
  assert.equal(browser.destroyCount(), 1)
  assert.equal(lifecycle.task('task-a'), null)
  assert.equal(browser.pages.has('task-a'), false)
  assert.equal(lifecycle.destroyTask('task-a'), false)
})

test('one task owns exactly one live page across repeated create/show operations', () => {
  const browser = fakeBrowser()
  const lifecycle = new BrowserTaskLifecycle(browser.bindings)

  lifecycle.createTask({ taskId: 'task-a' })
  lifecycle.createTask({ taskId: 'task-a' })
  lifecycle.showTask('task-a', { host: 'panel' })
  lifecycle.hideTask('task-a')
  lifecycle.showTask('task-a', { host: 'session' })

  assert.equal(browser.pages.size, 1)
  assert.equal(browser.pageCount(), 1)
  assert.equal(lifecycle.listTasks().length, 1)
})

test('restart preserves metadata, normalizes it to parked, and lazily recreates one page', () => {
  const stateFile = tempStateFile()
  const persistence = new BrowserTaskFilePersistence(stateFile)
  const beforeBrowser = fakeBrowser()
  const before = new BrowserTaskLifecycle(beforeBrowser.bindings, persistence)

  before.createTask({
    taskId: 'task-persisted',
    panelHost: 'panel-1',
    controlHost: 'control-1',
    sessionHost: 'session-1',
    localConnection: 'local-1',
    leaseState: 'retained'
  })
  before.showTask('task-persisted', { host: 'panel' })

  const afterBrowser = fakeBrowser()
  const after = new BrowserTaskLifecycle(afterBrowser.bindings, persistence)
  const restored = after.restore()

  assert.equal(restored.length, 1)
  assert.deepEqual(
    {
      taskId: restored[0].taskId,
      panelHost: restored[0].panelHost,
      controlHost: restored[0].controlHost,
      sessionHost: restored[0].sessionHost,
      localConnection: restored[0].localConnection,
      leaseState: restored[0].leaseState,
      status: restored[0].status,
      parked: restored[0].parked,
      recoveryState: restored[0].recoveryState
    },
    {
      taskId: 'task-persisted',
      panelHost: 'panel-1',
      controlHost: 'control-1',
      sessionHost: 'session-1',
      localConnection: 'local-1',
      leaseState: 'retained',
      status: 'parked',
      parked: true,
      recoveryState: 'restored'
    }
  )
  assert.equal(afterBrowser.pages.size, 0)

  const shown = after.showTask('task-persisted', { host: 'panel' })
  assert.equal(shown.recoveryState, 'recreated')
  assert.equal(afterBrowser.pages.size, 1)
  assert.equal(afterBrowser.pageCount(), 1)
})

test('persistence prunes invalid and duplicate task metadata on restore', () => {
  const stateFile = tempStateFile()
  fs.writeFileSync(
    stateFile,
    JSON.stringify({
      version: 1,
      browserTaskCounter: 7,
      tasks: [
        {
          taskId: 'task-a',
          createdAt: '2026-08-25T10:00:00.000Z',
          panelHost: null,
          controlHost: null,
          sessionHost: null,
          localConnection: null,
          status: 'hidden',
          leaseState: null,
          parked: false,
          recoveryState: 'fresh',
          updatedAt: '2026-08-25T10:00:00.000Z'
        },
        {
          taskId: 'task-a',
          createdAt: '2026-08-25T10:00:00.000Z',
          panelHost: 'newer-panel',
          controlHost: null,
          sessionHost: null,
          localConnection: null,
          status: 'parked',
          leaseState: null,
          parked: true,
          recoveryState: 'fresh',
          updatedAt: '2026-08-25T11:00:00.000Z'
        },
        { taskId: '', status: 'parked' }
      ]
    })
  )

  const browser = fakeBrowser()
  const lifecycle = new BrowserTaskLifecycle(browser.bindings, new BrowserTaskFilePersistence(stateFile))
  const restored = lifecycle.restore()

  assert.equal(restored.length, 1)
  assert.equal(restored[0].taskId, 'task-a')
  assert.equal(restored[0].panelHost, 'newer-panel')
  assert.equal(restored[0].status, 'parked')
})
