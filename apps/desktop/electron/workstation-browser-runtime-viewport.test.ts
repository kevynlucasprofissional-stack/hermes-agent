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
    frameRate = 60
    focused = false
    readonly navigationHistory = {
      canGoBack: () => false,
      canGoForward: () => false,
      goBack: () => undefined,
      goForward: () => undefined
    }

    on(event: string, listener: Listener): this {
      const current = this.listeners.get(event) ?? []
      current.push(listener)
      this.listeners.set(event, current)

      return this
    }

    private emit(event: string, ...args: unknown[]): void {
      for (const listener of this.listeners.get(event) ?? []) {
        listener(...args)
      }
    }

    setWindowOpenHandler(): void {}

    setFrameRate(rate: number): void {
      this.frameRate = rate
    }

    loadError: Error | null = null

    async loadURL(url: string): Promise<void> {
      if (this.loadError) {
        const err = this.loadError
        this.loadError = null
        throw err
      }

      this.url = url
      this.emit('did-start-loading')
      this.emit('did-navigate')
      this.emit('did-stop-loading')
    }

    emitEvent(event: string, ...args: unknown[]): void {
      this.emit(event, ...args)
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
      if (this.destroyed) {
        return
      }

      this.destroyed = true
      this.emit('destroyed')
    }

    focus(): void {
      this.focused = true
    }

    reload(): void {}
    stop(): void {}
  }

  class FakeWebContentsView {
    readonly webContents = new FakeWebContents()
    bounds = { x: 0, y: 0, width: 0, height: 0 }
    visible = true
    setBackgroundColor(): void {}
    setBounds(bounds: { x: number; y: number; width: number; height: number }): void {
      this.bounds = bounds
    }
    setVisible(visible: boolean): void {
      this.visible = visible
    }
  }

  class FakeBrowserWindow {
    destroyed = false
    private readonly listeners = new Map<string, Listener[]>()
    contentBounds = { x: 0, y: 0, width: 1200, height: 800 }
    readonly contentView = {
      children: [] as FakeWebContentsView[],
      addChildView: (view: FakeWebContentsView) => {
        if (!this.contentView.children.includes(view)) {
          this.contentView.children.push(view)
        }
      },
      removeChildView: (view: FakeWebContentsView) => {
        this.contentView.children = this.contentView.children.filter(candidate => candidate !== view)
      }
    }
    readonly webContents = { send: () => undefined, zoomFactor: 1 }

    constructor() {
      windows.push(this)
    }

    static getAllWindows(): FakeBrowserWindow[] {
      return windows.filter(window => !window.destroyed)
    }

    static fromWebContents(): FakeBrowserWindow | null {
      return null
    }

    on(event: string, listener: Listener): this {
      const current = this.listeners.get(event) ?? []
      current.push(listener)
      this.listeners.set(event, current)

      return this
    }

    off(event: string, listener: Listener): this {
      this.listeners.set(
        event,
        (this.listeners.get(event) ?? []).filter(candidate => candidate !== listener)
      )

      return this
    }

    emit(event: string): void {
      for (const listener of this.listeners.get(event) ?? []) {
        listener()
      }
    }

    isDestroyed(): boolean {
      return this.destroyed
    }

    getContentBounds(): { x: number; y: number; width: number; height: number } {
      return this.contentBounds
    }

    destroy(): void {
      this.destroyed = true
    }
  }

  return {
    BrowserWindow: FakeBrowserWindow,
    WebContentsView: FakeWebContentsView,
    app: {
      getPath: () => os.tmpdir(),
      isReady: () => true,
      whenReady: async () => undefined,
      on: () => undefined
    },
    ipcMain: {
      handle: () => undefined
    },
    session: {
      fromPath: () => ({
        getCacheSize: async () => 4096,
        clearCache: async () => undefined,
        clearStorageData: async () => undefined,
        setPermissionRequestHandler: () => undefined,
        webRequest: {
          onBeforeSendHeaders: () => undefined,
          onHeadersReceived: () => undefined
        }
      })
    }
  }
})

vi.mock('electron', () => electron)

import { BrowserWindow } from 'electron'

import { WorkstationBrowserRuntime } from './workstation-browser-runtime'
import { BrowserSessionStateFilePersistence } from './workstation-browser-session-state'

const createdDirs: string[] = []

function createPersistence(name: string): BrowserSessionStateFilePersistence {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `hermes-viewport-test-${name}-`))
  createdDirs.push(dir)

  return new BrowserSessionStateFilePersistence(
    path.join(dir, 'browser-session.json'),
    path.join(dir, 'browser-tasks.json')
  )
}

afterEach(() => {
  for (const dir of createdDirs.splice(0)) {
    try {
      fs.rmSync(dir, { recursive: true, force: true })
    } catch {
      // Best effort cleanup in tests.
    }
  }
})

test('viewportHost tracks host on attach and clears on detach', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('attach-detach'))
  const window = new BrowserWindow()
  const bounds = { x: 10, y: 10, width: 800, height: 600 }

  runtime.ensure()
  assert.equal(runtime.state().attached, false)
  assert.equal(runtime.state().viewportHost, null)

  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'hub')
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.state().viewportHost, 'hub')

  runtime.detach(window as unknown as Electron.BrowserWindow)
  assert.equal(runtime.state().attached, false)
  assert.equal(runtime.state().viewportHost, null)
})

test('transferViewport moves single live WebContentsView between hub and chat without page reload', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('transfer'))
  const window = new BrowserWindow()
  const hubBounds = { x: 0, y: 0, width: 1000, height: 700 }
  const chatBounds = { x: 400, y: 0, width: 600, height: 700 }

  runtime.ensure()
  const activeTabId = runtime.state().activeTabId
  assert.ok(activeTabId)

  // Attach to hub
  runtime.attach(window as unknown as Electron.BrowserWindow, hubBounds, 'hub')
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.state().viewportHost, 'hub')
  assert.equal(window.contentView.children.length, 1)

  // Transfer to chat
  runtime.transferViewport(window as unknown as Electron.BrowserWindow, 'chat', chatBounds)
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.state().viewportHost, 'chat')
  // Same tab identity preserved
  assert.equal(runtime.state().activeTabId, activeTabId)
  // View count remains exactly 1 — no duplicate lane
  assert.equal(window.contentView.children.length, 1)
})

test('setBounds ignores stale host geometry and normalizes the owning host bounds', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('host-bounds'))
  const window = new BrowserWindow()
  window.webContents.zoomFactor = 1.25
  const viewBounds = { x: 10, y: 10, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, viewBounds, 'hub')

  const view = window.contentView.children[0] as unknown as {
    bounds: { x: number; y: number; width: number; height: number }
  }

  assert.ok(view)
  const initialBounds = { ...view.bounds }

  runtime.setBounds(window as unknown as Electron.BrowserWindow, { x: 20, y: 20, width: 400, height: 300 }, 'chat')
  assert.deepEqual(view.bounds, initialBounds)
  assert.equal(runtime.state().viewportHost, 'hub')

  runtime.setBounds(window as unknown as Electron.BrowserWindow, { x: -4, y: 5, width: 400, height: 300 }, 'hub')
  assert.deepEqual(view.bounds, { x: 0, y: 6, width: 500, height: 375 })

  runtime.setBounds(
    window as unknown as Electron.BrowserWindow,
    { x: Number.NaN, y: 0, width: 400, height: 300 },
    'hub'
  )
  assert.deepEqual(view.bounds, { x: 0, y: 6, width: 500, height: 375 })

  runtime.setBounds(window as unknown as Electron.BrowserWindow, { x: 1100, y: 700, width: 400, height: 300 }, 'hub')
  assert.deepEqual(view.bounds, { x: 1199, y: 799, width: 1, height: 1 })
})

test('transferViewport rehomes the same live view between BrowserWindow hosts', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('window-transfer'))
  const hubWindow = new BrowserWindow()
  const chatWindow = new BrowserWindow()

  runtime.ensure()
  runtime.attach(hubWindow as unknown as Electron.BrowserWindow, { x: 0, y: 0, width: 1000, height: 700 }, 'hub')
  const view = hubWindow.contentView.children[0]
  assert.ok(view)

  runtime.transferViewport(chatWindow as unknown as Electron.BrowserWindow, 'chat', {
    x: 30,
    y: 40,
    width: 600,
    height: 500
  })
  assert.equal(hubWindow.contentView.children.length, 0)
  assert.equal(chatWindow.contentView.children.length, 1)
  assert.strictEqual(chatWindow.contentView.children[0], view)
  assert.equal(runtime.state().viewportHost, 'chat')

  runtime.transferViewport(hubWindow as unknown as Electron.BrowserWindow, 'hub', {
    x: 0,
    y: 0,
    width: 1000,
    height: 700
  })
  assert.equal(chatWindow.contentView.children.length, 0)
  assert.equal(hubWindow.contentView.children.length, 1)
  assert.strictEqual(hubWindow.contentView.children[0], view)
  assert.equal(runtime.state().viewportHost, 'hub')
})

test('native window geometry events keep the attached view inside resized content', async () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('native-resize'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentBounds: { x: number; y: number; width: number; height: number }
    contentView: {
      children: Array<{
        bounds: { x: number; y: number; width: number; height: number }
        webContents: { isDestroyed: () => boolean }
      }>
    }
    emit: (event: string) => void
  }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, { x: 600, y: 100, width: 500, height: 500 }, 'hub')
  const view = fakeWindow.contentView.children[0]
  assert.ok(view)
  assert.deepEqual(view.bounds, { x: 600, y: 100, width: 500, height: 500 })

  fakeWindow.contentBounds = { x: 0, y: 0, width: 800, height: 600 }
  fakeWindow.emit('resize')
  assert.deepEqual(view.bounds, { x: 600, y: 100, width: 200, height: 500 })

  await runtime.destroy()
  fakeWindow.contentBounds = { x: 0, y: 0, width: 400, height: 300 }
  fakeWindow.emit('maximize')
  assert.equal(view.webContents.isDestroyed(), true)
})

test('showTask activates task tab and attaches with specified host', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('show-task'))
  const window = new BrowserWindow()
  const bounds = { x: 0, y: 0, width: 500, height: 500 }

  runtime.ensure()
  const task = runtime.createTask({ taskId: 'task-viewport-1' })
  assert.ok(task)

  // Show task in chat host
  runtime.showTask('task-viewport-1', window as unknown as Electron.BrowserWindow, bounds, 'chat')
  assert.equal(runtime.state().attached, true)
  assert.equal(runtime.state().viewportHost, 'chat')

  // List tasks reflects task
  const tasks = runtime.listTasks()
  assert.equal(tasks.length, 1)
  assert.equal(tasks[0].taskId, 'task-viewport-1')
  assert.equal(runtime.state().tasks.length, 1)
  assert.equal(runtime.state().tasks[0].taskId, 'task-viewport-1')
})

test('attach with visible: false does not mount child view until setVisible(true)', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('attach-hidden'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentView: { children: any[] }
  }

  const bounds = { x: 0, y: 0, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'hub', undefined, undefined, false)

  assert.equal(runtime.state().attached, true)
  assert.equal(fakeWindow.contentView.children.length, 0)

  // When overlay closes, setVisible(true) mounts the child view with valid bounds
  runtime.setVisible(true, 'hub')
  assert.equal(fakeWindow.contentView.children.length, 1)
  const view = fakeWindow.contentView.children[0]
  assert.deepEqual(view.bounds, bounds)
  assert.equal(view.visible, true)

  // When overlay opens, setVisible(false) unmounts the child view
  runtime.setVisible(false, 'hub')
  assert.equal(fakeWindow.contentView.children.length, 0)
})

test('setVisible enforces host and ownerId fencing in both directions', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('visible-fencing'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentView: { children: any[] }
  }

  const bounds = { x: 0, y: 0, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'chat', 'task-1', 'owner-chat-1', true)
  assert.equal(fakeWindow.contentView.children.length, 1)

  // Stale session or different host cannot hide the view
  runtime.setVisible(false, 'hub')
  assert.equal(fakeWindow.contentView.children.length, 1)

  runtime.setVisible(false, 'chat', 'other-session')
  assert.equal(fakeWindow.contentView.children.length, 1)

  // Right owner hides the view
  runtime.setVisible(false, 'chat', 'owner-chat-1')
  assert.equal(fakeWindow.contentView.children.length, 0)

  // Stale session cannot re-show the view and steal visibility
  runtime.setVisible(true, 'chat', 'other-session')
  assert.equal(fakeWindow.contentView.children.length, 0)

  // Right owner restores the view
  runtime.setVisible(true, 'chat', 'owner-chat-1')
  assert.equal(fakeWindow.contentView.children.length, 1)
})

test('activateTab respects viewVisible and does not force child view when hidden', () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('activatetab-hidden'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentView: { children: any[] }
  }

  const bounds = { x: 0, y: 0, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'hub', undefined, undefined, false)
  assert.equal(fakeWindow.contentView.children.length, 0)

  // Create a second tab
  const stateAfterCreate = runtime.createTab('https://example.com', false)
  const tab2 = stateAfterCreate.tabs[stateAfterCreate.tabs.length - 1]
  runtime.activateTab(tab2.id)

  // Must still NOT mount child view because viewVisible is false
  assert.equal(fakeWindow.contentView.children.length, 0)

  // Setting visible mounts tab2
  runtime.setVisible(true, 'hub')
  assert.equal(fakeWindow.contentView.children.length, 1)
  assert.equal(runtime.state().activeTabId, tab2.id)
})

test('navigate absorbs ERR_ABORTED (-3) without throwing or setting lastError', async () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('nav-aborted'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentView: { children: any[] }
  }

  const bounds = { x: 0, y: 0, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'hub')
  const view = fakeWindow.contentView.children[0]
  assert.ok(view)

  // Simulate ERR_ABORTED (-3) on loadURL
  const abortError: any = new Error('ERR_ABORTED (-3)')
  abortError.code = 'ERR_ABORTED'
  abortError.errno = -3
  view.webContents.loadError = abortError

  // navigate must NOT reject and must NOT set lastError
  await runtime.navigate('https://example.com/search?q=test')
  assert.equal(runtime.state().lastError, null)
})

test('did-fail-load ignores ERR_ABORTED and captures real network failure in lastError', async () => {
  const runtime = new WorkstationBrowserRuntime(createPersistence('nav-fail-load'))
  const window = new BrowserWindow()

  const fakeWindow = window as unknown as {
    contentView: { children: any[] }
  }

  const bounds = { x: 0, y: 0, width: 800, height: 600 }

  runtime.ensure()
  runtime.attach(window as unknown as Electron.BrowserWindow, bounds, 'hub')
  const view = fakeWindow.contentView.children[0]
  assert.ok(view)

  // Emitting did-fail-load with errorCode -3 (ERR_ABORTED) should NOT set lastError
  view.webContents.emitEvent('did-fail-load', {}, -3, 'ERR_ABORTED', 'https://example.com', true)
  assert.equal(runtime.state().lastError, null)

  // Emitting did-fail-load with real failure (e.g. -105 ERR_NAME_NOT_RESOLVED) sets lastError
  view.webContents.emitEvent('did-fail-load', {}, -105, 'ERR_NAME_NOT_RESOLVED', 'https://nonexistent.domain', true)
  assert.ok(runtime.state().lastError?.includes('ERR_NAME_NOT_RESOLVED'))

  // Next successful navigation clears lastError
  await runtime.navigate('https://example.com')
  assert.equal(runtime.state().lastError, null)
})


