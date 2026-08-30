import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test, vi } from 'vitest'

const electron = vi.hoisted(() => {
  type Listener = (...args: unknown[]) => void
  const windows: FakeBrowserWindow[] = []

  class FakeWebContents {
    private destroyed = false
    private readonly listeners = new Map<string, Listener[]>()
    private title = ''
    private url = 'about:blank'
    private windowOpenHandler: ((details: { url: string }) => { action: string }) | null = null
    frameRate = 60
    focused = false
    readonly navigationHistory = {
      canGoBack: () => false,
      canGoForward: () => false,
      goBack: () => undefined,
      goForward: () => undefined
    }
    readonly debugger = {
      isAttached: () => false,
      attach: () => undefined,
      sendCommand: async () => ({})
    }

    on(event: string, listener: Listener): this {
      const current = this.listeners.get(event) ?? []
      current.push(listener)
      this.listeners.set(event, current)
      return this
    }

    private emit(event: string, ...args: unknown[]): void {
      for (const listener of this.listeners.get(event) ?? []) listener(...args)
    }

    setWindowOpenHandler(handler: (details: { url: string }) => { action: string }): void {
      this.windowOpenHandler = handler
    }

    setFrameRate(rate: number): void {
      this.frameRate = rate
    }

    async loadURL(url: string): Promise<void> {
      this.url = url
      this.emit('did-start-loading')
      this.emit('did-navigate')
      this.emit('did-stop-loading')
    }

    getURL(): string {
      return this.url
    }

    getTitle(): string {
      return this.title
    }

    setTitle(title: string): void {
      this.title = title
      this.emit('page-title-updated')
    }

    isDestroyed(): boolean {
      return this.destroyed
    }

    close(): void {
      if (this.destroyed) return
      this.destroyed = true
      this.emit('destroyed')
    }

    focus(): void {
      this.focused = true
    }

    reload(): void {}
    stop(): void {}
    async executeJavaScript(source: string): Promise<unknown> {
      if (source.includes('__hermesWorkstationRefs')) {
        return {
          url: this.url,
          title: this.title,
          text: '',
          totalTextChars: 0,
          truncated: false,
          elements: []
        }
      }
      return {}
    }
    async capturePage(): Promise<{ toPNG: () => Uint8Array }> { return { toPNG: () => new Uint8Array() } }

    simulateRenderProcessGone(): void {
      this.emit('render-process-gone', {}, { reason: 'crashed' })
    }
  }

  class FakeWebContentsView {
    readonly webContents = new FakeWebContents()
    bounds = { x: 0, y: 0, width: 0, height: 0 }
    setBackgroundColor(): void {}
    setBounds(bounds: { x: number; y: number; width: number; height: number }): void {
      this.bounds = bounds
    }
  }

  class FakeBrowserWindow {
    destroyed = false
    readonly contentView = {
      children: [] as FakeWebContentsView[],
      addChildView: (view: FakeWebContentsView) => {
        if (!this.contentView.children.includes(view)) this.contentView.children.push(view)
      },
      removeChildView: (view: FakeWebContentsView) => {
        this.contentView.children = this.contentView.children.filter(candidate => candidate !== view)
      }
    }
    readonly webContents = { send: () => undefined }

    constructor() {
      windows.push(this)
    }

    static getAllWindows(): FakeBrowserWindow[] {
      return windows.filter(window => !window.destroyed)
    }

    static fromWebContents(): FakeBrowserWindow | null {
      return null
    }

    isDestroyed(): boolean {
      return this.destroyed
    }

    getContentBounds(): { x: number; y: number; width: number; height: number } {
      return { x: 0, y: 0, width: 1440, height: 900 }
    }
  }

  const browserSession = {
    getCacheSize: async () => 0,
    clearCache: async () => undefined
  }

  return {
    windows,
    FakeBrowserWindow,
    FakeWebContents,
    FakeWebContentsView,
    app: {
      getPath: () => 'C:/tmp/hermes-runtime-task-app',
      whenReady: () => new Promise<never>(() => undefined),
      on: () => undefined
    },
    ipcMain: { handle: () => undefined },
    session: { fromPath: () => browserSession }
  }
})

vi.mock('electron', () => ({
  app: electron.app,
  BrowserWindow: electron.FakeBrowserWindow,
  ipcMain: electron.ipcMain,
  session: electron.session,
  WebContentsView: electron.FakeWebContentsView
}))

import { WorkstationBrowserRuntime, workstationBrowserSessionStatePath } from './workstation-browser-runtime'

const tempRoots: string[] = []
afterEach(() => {
  delete process.env.HERMES_WORKSTATION_HOME
  electron.windows.splice(0)
  for (const root of tempRoots.splice(0)) fs.rmSync(root, { recursive: true, force: true })
})

function runtimeHome(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-runtime-task-'))
  tempRoots.push(root)
  process.env.HERMES_WORKSTATION_HOME = root
  return root
}

function hostWindow(): InstanceType<typeof electron.FakeBrowserWindow> {
  return new electron.FakeBrowserWindow()
}

test('ordinary tabs restore in order with the active logical tab and only safe URL/title metadata', async () => {
  const home = runtimeHome()
  const first = new WorkstationBrowserRuntime()
  const initial = first.ensure().tabs[0]
  assert.ok(initial)
  const initialContents = first.getWebContents(initial.id) as unknown as InstanceType<typeof electron.FakeWebContents>
  assert.ok(initialContents)
  await initialContents.loadURL('https://example.test/account?access_token=page-secret#fragment-secret')
  initialContents.setTitle('Access token = title-secret')

  const withSecond = first.createTab('https://docs.example.test/guide?q=ordinary-search', true)
  const secondTab = withSecond.tabs.at(-1)
  assert.ok(secondTab)
  const secondContents = first.getWebContents(secondTab.id) as unknown as InstanceType<typeof electron.FakeWebContents>
  assert.ok(secondContents)
  secondContents.setTitle('Example Docs — Guide')
  assert.equal(first.state().activeTabId, secondTab.id)

  await first.destroy()

  const persisted = fs.readFileSync(path.join(home, 'Runtime', 'browser-session.json'), 'utf-8')
  assert.equal(persisted.includes('page-secret'), false)
  assert.equal(persisted.includes('fragment-secret'), false)
  assert.equal(persisted.includes('title-secret'), false)
  assert.equal(persisted.includes('ordinary-search'), false)
  assert.equal(persisted.includes('WebContents'), false)

  const second = new WorkstationBrowserRuntime()
  const restored = second.ensure()
  assert.deepEqual(
    restored.tabs.map(tab => tab.id),
    [initial.id, secondTab.id]
  )
  assert.deepEqual(
    restored.tabs.map(tab => tab.url),
    ['https://example.test/account', 'https://docs.example.test/guide']
  )
  assert.equal(restored.tabs[0].title, 'New Tab')
  assert.equal(restored.tabs[1].title, 'Example Docs — Guide')
  assert.equal(restored.activeTabId, secondTab.id)

  await second.destroy()
})

test('BrowserTask metadata coexists with ordinary tabs and restores one task page lazily', async () => {
  runtimeHome()
  const first = new WorkstationBrowserRuntime()
  const ordinary = first.ensure().tabs[0]
  first.createTask({ taskId: 'task-session', sessionHost: 'hermes-session-1' })
  const taskTab = first.state().tabs.find(tab => tab.ownerTaskId === 'task-session')
  assert.ok(taskTab)
  const taskContents = first.getWebContents(taskTab.id) as unknown as InstanceType<typeof electron.FakeWebContents>
  assert.ok(taskContents)
  await taskContents.loadURL('https://task.example.test/work?session_id=page-secret')
  taskContents.setTitle('Task Workspace')
  const tail = first.createTab('https://tail.example.test/ordinary', false).tabs.at(-1)
  assert.ok(tail)
  await first.destroy()

  const second = new WorkstationBrowserRuntime()
  const beforeShow = second.ensure()
  assert.deepEqual(
    beforeShow.tabs.map(tab => tab.id),
    [ordinary.id, tail.id]
  )
  assert.equal(second.listTasks()[0]?.taskId, 'task-session')
  assert.equal(second.listTasks()[0]?.sessionHost, 'hermes-session-1')
  assert.equal(
    beforeShow.tabs.some(tab => tab.ownerTaskId === 'task-session'),
    false
  )

  const shown = second.showTask('task-session', hostWindow() as never, { x: 0, y: 0, width: 900, height: 600 })
  assert.equal(shown.recoveryState, 'recreated')
  const recovered = second.state().tabs.filter(tab => tab.ownerTaskId === 'task-session')
  assert.equal(recovered.length, 1)
  assert.equal(recovered[0].id, taskTab.id)
  assert.equal(recovered[0].url, 'https://task.example.test/work')
  assert.equal(recovered[0].title, 'Task Workspace')
  assert.deepEqual(
    second.state().tabs.map(tab => tab.id),
    [ordinary.id, taskTab.id, tail.id]
  )

  second.showTask('task-session', hostWindow() as never, { x: 0, y: 0, width: 900, height: 600 })
  assert.equal(second.state().tabs.filter(tab => tab.ownerTaskId === 'task-session').length, 1)
  await second.destroy()
})

test('a lazy BrowserTask remains the logical active tab until its page is recreated', async () => {
  runtimeHome()
  const first = new WorkstationBrowserRuntime()
  first.ensure()
  first.createTask({ taskId: 'task-active' })
  const taskTab = first.state().tabs.find(tab => tab.ownerTaskId === 'task-active')
  assert.ok(taskTab)
  first.activateTab(taskTab.id)
  await first.destroy()

  const second = new WorkstationBrowserRuntime()
  const beforeShow = second.ensure()
  assert.equal(beforeShow.tabs.some(tab => tab.ownerTaskId === 'task-active'), false)
  assert.equal(JSON.parse(fs.readFileSync(workstationBrowserSessionStatePath(), 'utf-8')).activeTabId, taskTab.id)

  second.showTask('task-active', hostWindow() as never, { x: 0, y: 0, width: 900, height: 600 })
  const recovered = second.state().tabs.filter(tab => tab.ownerTaskId === 'task-active')
  assert.equal(recovered.length, 1)
  assert.equal(recovered[0].id, taskTab.id)
  assert.equal(second.state().activeTabId, taskTab.id)
  await second.destroy()
})

test('an unexpectedly destroyed ordinary entry remains a logical stale tab and reconciles on restart', async () => {
  runtimeHome()
  const first = new WorkstationBrowserRuntime()
  const tab = first.ensure().tabs[0]
  const contents = first.getWebContents(tab.id) as unknown as InstanceType<typeof electron.FakeWebContents>
  assert.ok(contents)
  await contents.loadURL('https://stale.example.test/recover')
  contents.setTitle('Recoverable Page')
  contents.close()
  assert.equal(first.state().tabs.length, 0)
  await first.destroy()

  const second = new WorkstationBrowserRuntime()
  const restored = second.ensure()
  assert.equal(restored.tabs.length, 1)
  assert.equal(restored.tabs[0].id, tab.id)
  assert.equal(restored.tabs[0].url, 'https://stale.example.test/recover')
  assert.equal(restored.tabs[0].title, 'Recoverable Page')
  await second.destroy()
})

test('an unknown BrowserSessionState version starts safely without importing stale legacy state', async () => {
  const home = runtimeHome()
  fs.mkdirSync(path.dirname(workstationBrowserSessionStatePath()), { recursive: true })
  fs.writeFileSync(workstationBrowserSessionStatePath(), JSON.stringify({ version: 999, tabs: [] }))
  fs.writeFileSync(
    path.join(home, 'Runtime', 'browser-tasks.json'),
    JSON.stringify({ version: 1, browserTaskCounter: 1, tasks: [{ taskId: 'stale-task' }] })
  )

  const runtime = new WorkstationBrowserRuntime()
  const state = runtime.ensure()
  assert.equal(state.tabs.length, 1)
  assert.equal(state.tabs[0].url, 'about:blank')
  assert.deepEqual(runtime.listTasks(), [])
  await runtime.destroy()
  assert.equal(JSON.parse(fs.readFileSync(workstationBrowserSessionStatePath(), 'utf-8')).version, 999)
})

test('ownerTaskId is idempotent at the Chromium tab primitive', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  runtime.createTab('about:blank', false, 'task-a')
  const first = runtime.state().tabs.find(tab => tab.ownerTaskId === 'task-a')
  assert.ok(first)

  runtime.createTab('about:blank', false, 'task-a')
  const owned = runtime.state().tabs.filter(tab => tab.ownerTaskId === 'task-a')
  assert.equal(owned.length, 1)
  assert.equal(owned[0].id, first.id)

  await runtime.destroy()
})

test('runtime BrowserTask hide/park/show preserves one WebContents and its URL', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const window = hostWindow()
  const bounds = { x: 20, y: 80, width: 1000, height: 700 }

  runtime.createTask({ taskId: 'task-a' })
  const tab = runtime.state().tabs.find(candidate => candidate.ownerTaskId === 'task-a')
  assert.ok(tab)
  const contents = runtime.getWebContents(tab.id)
  assert.ok(contents)
  await contents.loadURL('https://example.test/current')

  const hidden = runtime.hideTask('task-a')
  assert.equal(hidden.status, 'hidden')
  assert.equal(contents.isDestroyed(), false)

  const shown = runtime.showTask('task-a', window as never, bounds)
  assert.equal(shown.status, 'visible')
  assert.equal(runtime.getWebContents(tab.id), contents)
  assert.equal(contents.getURL(), 'https://example.test/current')

  const parked = runtime.parkTask('task-a')
  assert.equal(parked.status, 'parked')
  runtime.showTask('task-a', window as never, bounds)
  assert.equal(runtime.getWebContents(tab.id), contents)
  assert.equal(contents.getURL(), 'https://example.test/current')

  assert.equal(runtime.state().tabs.filter(candidate => candidate.ownerTaskId === 'task-a').length, 1)
  assert.equal(runtime.destroyTask('task-a'), true)
  assert.equal(contents.isDestroyed(), true)
  assert.equal(runtime.listTasks().length, 0)

  await runtime.destroy()
})

test('controller actions preserve a visible task through Take Control and Release Control', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const window = hostWindow()
  const bounds = { x: 20, y: 80, width: 1000, height: 700 }

  runtime.createTask({ taskId: 'task-a' })
  const tab = runtime.state().tabs.find(candidate => candidate.ownerTaskId === 'task-a')
  assert.ok(tab)
  const contents = runtime.getWebContents(tab.id)
  assert.ok(contents)
  runtime.showTask('task-a', window as never, bounds)

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  runtime.takeControl()
  await executeControlRequest({ action: 'browser_snapshot', task_id: 'task-a', arguments: {} })
  assert.equal(runtime.state().controlOwner, 'human')
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.listTasks()[0]?.status, 'visible')
  assert.equal(runtime.getWebContents(tab.id), contents)

  runtime.releaseControl()
  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-a',
    arguments: { url: 'https://example.test/agent' }
  })
  assert.equal(runtime.state().controlOwner, 'agent')
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.listTasks()[0]?.status, 'visible')
  assert.equal(runtime.getWebContents(tab.id), contents)

  await runtime.destroy()
})

test('runtime replaces one crashed BrowserTask page and preserves logical ownership', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  runtime.createTask({ taskId: 'task-a' })
  const firstTab = runtime.state().tabs.find(candidate => candidate.ownerTaskId === 'task-a')
  assert.ok(firstTab)
  const crashed = runtime.getWebContents(firstTab.id) as unknown as InstanceType<typeof electron.FakeWebContents>
  assert.ok(crashed)
  crashed.simulateRenderProcessGone()

  const recovered = runtime.createTask({ taskId: 'task-a' })
  const owned = runtime.state().tabs.filter(candidate => candidate.ownerTaskId === 'task-a')
  assert.equal(recovered.recoveryState, 'recreated')
  assert.equal(owned.length, 1)
  assert.notEqual(owned[0].id, firstTab.id)
  assert.notEqual(runtime.getWebContents(owned[0].id), crashed)
  assert.equal(crashed.isDestroyed(), true)

  await runtime.destroy()
})

test('destroying the active BrowserTask activates the remaining isolated task page', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  runtime.createTask({ taskId: 'task-a' })
  runtime.createTask({ taskId: 'task-b' })
  const taskA = runtime.state().tabs.find(candidate => candidate.ownerTaskId === 'task-a')
  const taskB = runtime.state().tabs.find(candidate => candidate.ownerTaskId === 'task-b')
  assert.ok(taskA)
  assert.ok(taskB)
  runtime.activateTab(taskA.id)

  assert.equal(runtime.destroyTask('task-a'), true)
  const state = runtime.state()
  assert.equal(state.tabs.some(candidate => candidate.ownerTaskId === 'task-a'), false)
  assert.equal(state.tabs.filter(candidate => candidate.ownerTaskId === 'task-b').length, 1)
  assert.equal(state.activeTabId, taskB.id)
  assert.equal(runtime.listTasks().map(task => task.taskId).join(','), 'task-b')

  await runtime.destroy()
})

test('runtime restart keeps task metadata parked and recreates a page only on show', async () => {
  runtimeHome()
  const first = new WorkstationBrowserRuntime()
  first.createTask({ taskId: 'task-persisted', panelHost: 'panel-1' })
  first.showTask('task-persisted', hostWindow() as never, { x: 0, y: 0, width: 900, height: 600 })
  await first.destroy()

  const second = new WorkstationBrowserRuntime()
  second.ensure()
  const restored = second.listTasks()
  assert.equal(restored.length, 1)
  assert.equal(restored[0].taskId, 'task-persisted')
  assert.equal(restored[0].status, 'parked')
  assert.equal(restored[0].recoveryState, 'restored')
  assert.equal(second.state().tabs.some(tab => tab.ownerTaskId === 'task-persisted'), false)

  const shown = second.showTask('task-persisted', hostWindow() as never, { x: 0, y: 0, width: 900, height: 600 })
  assert.equal(shown.recoveryState, 'recreated')
  assert.equal(second.state().tabs.filter(tab => tab.ownerTaskId === 'task-persisted').length, 1)

  await second.destroy()
})
