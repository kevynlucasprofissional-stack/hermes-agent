import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test, vi } from 'vitest'

const electron = vi.hoisted(() => {
  const windows: FakeBrowserWindow[] = []

  class FakeWebContents extends EventEmitter {
    private destroyed = false
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
    async executeJavaScript(): Promise<unknown> { return {} }
    async capturePage(): Promise<{ toPNG: () => Buffer }> { return { toPNG: () => Buffer.from('') } }
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
      getPath: () => path.join(os.tmpdir(), 'hermes-runtime-task-app'),
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

import { WorkstationBrowserRuntime } from './workstation-browser-runtime'

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
