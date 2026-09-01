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

    setWindowOpenHandler(): void {}
    setFrameRate(): void {}
    focus(): void {}
    reload(): void {}
    stop(): void {}

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

    async capturePage(): Promise<{ toPNG: () => Uint8Array }> {
      return { toPNG: () => new Uint8Array() }
    }
  }

  class FakeWebContentsView {
    readonly webContents = new FakeWebContents()
    setBackgroundColor(): void {}
    setBounds(): void {}
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
      getPath: () => 'C:/tmp/hermes-runtime-resilience-app',
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
import { BrowserSessionStateFilePersistence } from './workstation-browser-session-state'

const tempRoots: string[] = []

afterEach(() => {
  delete process.env.HERMES_WORKSTATION_HOME
  electron.windows.splice(0)
  for (const root of tempRoots.splice(0)) fs.rmSync(root, { recursive: true, force: true })
})

function runtimeHome(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-runtime-resilience-'))
  tempRoots.push(root)
  process.env.HERMES_WORKSTATION_HOME = root
  return root
}

function failNextRenamePersistence(home: string): {
  persistence: BrowserSessionStateFilePersistence
  failNextRename(): void
} {
  let shouldFail = false
  const io = {
    ...fs,
    renameSync: (...args: Parameters<typeof fs.renameSync>) => {
      if (shouldFail) {
        shouldFail = false
        throw new Error('simulated BrowserTask destroy persistence failure')
      }
      fs.renameSync(...args)
    }
  }

  return {
    persistence: new BrowserSessionStateFilePersistence(
      workstationBrowserSessionStatePath(),
      path.join(home, 'Runtime', 'browser-tasks.json'),
      io
    ),
    failNextRename(): void {
      shouldFail = true
    }
  }
}

function persistedTaskIds(): string[] {
  const composite = JSON.parse(fs.readFileSync(workstationBrowserSessionStatePath(), 'utf-8')) as {
    browserTasks: { tasks: Array<{ taskId: string }> }
  }
  return composite.browserTasks.tasks.map(task => task.taskId)
}

test('failed BrowserTask destroy persistence completes in-memory cleanup before the same task id is recreated', async () => {
  const home = runtimeHome()
  const fault = failNextRenamePersistence(home)
  const runtime = new WorkstationBrowserRuntime(fault.persistence)

  runtime.createTask({ taskId: 'task-destroy-failure' })
  const originalTab = runtime.state().tabs.find(tab => tab.ownerTaskId === 'task-destroy-failure')
  assert.ok(originalTab)
  const originalContents = runtime.getWebContents(originalTab.id) as unknown as InstanceType<
    typeof electron.FakeWebContents
  >
  assert.ok(originalContents)
  await originalContents.loadURL('https://task.example.test/workspace')
  assert.deepEqual(persistedTaskIds(), ['task-destroy-failure'])

  fault.failNextRename()
  assert.throws(
    () => runtime.destroyTask('task-destroy-failure'),
    /simulated BrowserTask destroy persistence failure/
  )

  // The explicit destroy already completed its process-local semantic mutation:
  // task metadata is gone and the prior page is dead, even though disk remains
  // at the previous complete snapshot until another composite save succeeds.
  assert.deepEqual(runtime.listTasks(), [])
  assert.equal(originalContents.isDestroyed(), true)
  assert.deepEqual(persistedTaskIds(), ['task-destroy-failure'])

  // An unrelated runtime save must converge the durable composite to the
  // intended deletion rather than resurrecting the task.
  await runtime.navigate('https://ordinary.example.test/after-destroy-failure')
  assert.deepEqual(persistedTaskIds(), [])

  // Reusing the same task id after an explicit destroy is a new BrowserTask.
  // It must not inherit the destroyed page's pending URL/identity metadata.
  runtime.createTask({ taskId: 'task-destroy-failure' })
  const recreated = runtime.state().tabs.filter(tab => tab.ownerTaskId === 'task-destroy-failure')
  assert.equal(recreated.length, 1)
  assert.notEqual(recreated[0].id, originalTab.id)
  assert.equal(recreated[0].url, 'about:blank')

  await runtime.destroy()
})
