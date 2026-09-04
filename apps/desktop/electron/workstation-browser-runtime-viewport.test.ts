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
        if (!this.contentView.children.includes(view)) {
          this.contentView.children.push(view)
        }
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
      return { x: 0, y: 0, width: 1200, height: 800 }
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
