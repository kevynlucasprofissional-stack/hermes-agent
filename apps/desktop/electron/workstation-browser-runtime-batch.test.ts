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
    readbackEnabled = false
    inputValue = ''
    suppressInsertText = false
    onInsertText: (() => void) | null = null
    readonly navigationHistory = {
      canGoBack: () => false,
      canGoForward: () => false,
      goBack: () => undefined,
      goForward: () => undefined
    }
    readonly debugger = {
      isAttached: () => false,
      attach: () => undefined,
      sendCommand: async (method: string, params?: { text?: string }) => {
        if (method === 'Input.insertText' && this.readbackEnabled) {
          if (!this.suppressInsertText) {this.inputValue += String(params?.text ?? '')}
          this.onInsertText?.()
        }

        return {}
      }
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
      if (this.destroyed) {return}
      this.destroyed = true
      this.emit('destroyed')
    }

    focus(): void {
      this.focused = true
    }

    reload(): void {}
    stop(): void {}

    async executeJavaScript(source: string): Promise<unknown> {
      if (source.includes('__HERMES_BATCH_READBACK_V1__')) {
        return this.readbackEnabled
          ? {
              url: this.url,
              documentToken: 'test-document',
              elementToken: 1,
              found: true,
              editable: true,
              value: this.inputValue,
              checked: null,
              pressed: null,
              expanded: null,
              scrollY: 0
            }
          : null
      }

      if (source.includes('__hermesWorkstationRefs')) {
        if (source.includes('byRef.get')) {
          return {
            success: true,
            x: 100,
            y: 100,
            target: {
              ref: '@e1',
              tag: 'input',
              role: 'textbox',
              label: 'Field',
              name: 'field'
            }
          }
        }
      }

      if (source.includes('innerHeight')) {
        return { width: 1280, height: 720 }
      }

      return {
        url: this.url,
        title: this.title || 'Example App',
        text: 'Hello world page content',
        totalTextChars: 24,
        truncated: false,
        elements: [
          {
            ref: '@e1',
            tag: 'input',
            role: 'textbox',
            label: 'Field',
            name: 'field',
            value: '',
            x: 100,
            y: 100,
            w: 200,
            h: 40
          }
        ]
      }
    }
  }

  class FakeWebContentsView {
    readonly webContents = new FakeWebContents()
    private bounds = { x: 0, y: 0, width: 0, height: 0 }
    setBackgroundColor(): void {}
    setBounds(bounds: { x: number; y: number; width: number; height: number }): void {
      this.bounds = bounds
    }
    getBounds(): { x: number; y: number; width: number; height: number } {
      return this.bounds
    }
  }

  class FakeBrowserWindow {
    readonly webContents = {
      send: () => undefined
    }
    readonly views: FakeWebContentsView[] = []
    private bounds = { x: 1280, y: 800, width: 1280, height: 800 }
    constructor() {
      windows.push(this)
    }
    static getAllWindows(): FakeBrowserWindow[] {
      return windows.filter(w => !w.isDestroyed())
    }
    getBounds(): { x: number; y: number; width: number; height: number } {
      return this.bounds
    }
    getContentBounds(): { x: number; y: number; width: number; height: number } {
      return this.bounds
    }
    isDestroyed(): boolean {
      return false
    }
    close(): void {}
    contentView = {
      addChildView: (view: FakeWebContentsView) => {
        this.views.push(view)
      },
      removeChildView: (view: FakeWebContentsView) => {
        const idx = this.views.indexOf(view)

        if (idx >= 0) {this.views.splice(idx, 1)}
      }
    }
  }

  return {
    windows,
    app: {
      getPath: (name: string) => path.join(os.tmpdir(), `hermes-app-${name}`),
      isPackaged: false,
      getVersion: () => '1.0.0',
      whenReady: () => new Promise<never>(() => undefined),
      on: () => undefined
    },
    BrowserWindow: FakeBrowserWindow,
    WebContentsView: FakeWebContentsView,
    ipcMain: {
      handle: () => undefined,
      removeHandler: () => undefined
    },
    session: {
      defaultSession: {
        clearCache: async () => undefined
      }
    }
  }
})

vi.mock('electron', () => electron)

import { WorkstationBrowserRuntime } from './workstation-browser-runtime'

const tempHomes: string[] = []

function runtimeHome(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-batch-test-'))
  tempHomes.push(dir)
  process.env.HERMES_WORKSTATION_HOME = dir
  process.env.HERMES_HOME = dir

  return dir
}

afterEach(() => {
  delete process.env.HERMES_WORKSTATION_HOME
  delete process.env.HERMES_HOME

  for (const dir of tempHomes.splice(0)) {
    fs.rmSync(dir, { recursive: true, force: true })
  }
})

test('browser_batch_actions verifies observed type steps and produces receipts', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-batch-1',
    arguments: { url: 'https://example.com' }
  })

  const entry = (runtime as any).entryForTask('task-batch-1', false)
  entry.view.webContents.readbackEnabled = true

  const batchResponse = await executeControlRequest({
    action: 'browser_batch_actions',
    task_id: 'task-batch-1',
    operation_id: 'op-batch-test-1',
    arguments: {
      steps: [
        { kind: 'type', ref: '@e1', text: 'typed text', clear: true },
        { kind: 'type', ref: '@e1', text: ' and more', append: true }
      ]
    }
  })

  assert.equal(batchResponse.status, 'verified')
  assert.equal(batchResponse.completed_steps, 2)
  assert.equal(batchResponse.verified_steps, 2)
  assert.equal(entry.view.webContents.inputValue, 'typed text and more')
  assert.equal(batchResponse.stopped_at, null)
  const receipts = batchResponse.receipts as Array<string | null>
  assert.equal(receipts.length, 2)
  assert.ok(receipts[0]?.startsWith('op-batch-test-1:0:'))
  assert.ok(receipts[1]?.startsWith('op-batch-test-1:1:'))

  await runtime.destroy()
})

test('browser_batch_actions rejects malformed step before executing any operation', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-batch-bad',
    arguments: { url: 'https://example.com' }
  })

  const res = await executeControlRequest({
    action: 'browser_batch_actions',
    task_id: 'task-batch-bad',
    arguments: {
      steps: [
        { kind: 'click', ref: '@e1' },
        { kind: 'press', key: '' } // malformed press
      ]
    }
  })

  assert.equal(res.status, 'rejected')
  assert.equal(res.completed_steps, 0)
  assert.equal(res.verified_steps, 0)
  assert.equal(res.stopped_at, 1)

  await runtime.destroy()
})

test('browser_batch_actions halts immediately when human takes over during batch', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-batch-human',
    arguments: { url: 'https://example.com' }
  })

  // Acquire human control lease on the task
  const taskLifecycle = (
    runtime as unknown as {
      taskLifecycle(): {
        acquireHumanControl(
          taskId: string,
          details: {
            sessionId: string | null
            tabId: string | null
            pageId: number | null
            profileScope: string | null
          },
          ttlMs: number
        ): void
      }
    }
  ).taskLifecycle()

  taskLifecycle.acquireHumanControl(
    'task-batch-human',
    { sessionId: null, tabId: null, pageId: null, profileScope: null },
    60_000
  )

  // When human control is active, agent batch execution must be blocked/rejected
  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_batch_actions',
      task_id: 'task-batch-human',
      arguments: {
        steps: [{ kind: 'click', ref: '@e1' }]
      }
    })
  }, /under human control/)

  await runtime.destroy()
})

test('browser_batch_actions rejects batches exceeding maximum limit (20)', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-batch-oversize',
    arguments: { url: 'https://example.com' }
  })

  const steps = Array.from({ length: 21 }, () => ({ kind: 'press', key: 'Tab' }))

  const res = await executeControlRequest({
    action: 'browser_batch_actions',
    task_id: 'task-batch-oversize',
    arguments: { steps }
  })

  assert.equal(res.status, 'rejected')
  assert.equal(res.completed_steps, 0)
  assert.equal(res.reason, 'invalid_batch_identity_or_size')

  await runtime.destroy()
})

test('BROW-N1: an action ACK and persisted receipt without readback must not verify a batch', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>

  await dispatch({
    action: 'browser_navigate',
    task_id: 'task-proof-negative',
    arguments: { url: 'https://example.com' }
  })

  const response = await dispatch({
    action: 'browser_batch_actions',
    task_id: 'task-proof-negative',
    operation_id: 'proof-negative',
    arguments: {
      steps: [
        { kind: 'click', ref: '@e1' },
        { kind: 'type', ref: '@e1', text: 'SHOULD_NOT_EXECUTE' }
      ]
    }
  })

  assert.equal(response.status, 'uncertain')
  assert.equal(response.completed_steps, 1)
  assert.equal(response.verified_steps, 0)
  assert.equal(response.stopped_at, 0)
  assert.notEqual(response.receipts.length, 0, 'ACK receipt remains visible without implying VERIFIED')
  await runtime.destroy()
})

async function batchFixture(taskId: string) {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>

  await dispatch({ action: 'browser_navigate', task_id: taskId, arguments: { url: 'https://example.com' } })
  const entry = (runtime as any).entryForTask(taskId, false)
  entry.view.webContents.readbackEnabled = true

  const execute = () =>
    dispatch({
      action: 'browser_batch_actions',
      task_id: taskId,
      operation_id: 'op-' + taskId,
      arguments: {
        steps: [
          { kind: 'type', ref: '@e1', text: 'first' },
          { kind: 'type', ref: '@e1', text: 'second' }
        ]
      }
    })

  return { runtime, entry, execute }
}

test('BROW-N1: CDP ACK with unchanged input value halts subsequent steps', async () => {
  const { runtime, entry, execute } = await batchFixture('proof-no-effect')
  entry.view.webContents.suppressInsertText = true
  const result = await execute()
  assert.equal(result.status, 'uncertain')
  assert.equal(result.reason, 'input_value_mismatch')
  assert.equal(result.completed_steps, 1)
  assert.equal(result.verified_steps, 0)
  assert.equal(result.receipts.length, 1)
  await runtime.destroy()
})

test('BROW-N1: human takeover during first effect blocks subsequent steps', async () => {
  const { runtime, entry, execute } = await batchFixture('proof-takeover')

  entry.view.webContents.onInsertText = () => {
    ;(runtime as any)
      .taskLifecycle()
      .acquireHumanControl('proof-takeover', { sessionId: null, tabId: null, pageId: null, profileScope: null }, 60_000)
  }

  const result = await execute()
  assert.equal(result.status, 'uncertain')
  assert.equal(result.completed_steps, 1)
  assert.equal(result.verified_steps, 0)
  assert.equal(result.stopped_at, 0)
  await runtime.destroy()
})

test('BROW-N1: navigation during first effect invalidates document binding and halts', async () => {
  const { runtime, entry, execute } = await batchFixture('proof-navigation')

  entry.view.webContents.onInsertText = () => {
    void entry.view.webContents.loadURL('https://example.com/other')
  }

  const result = await execute()
  assert.equal(result.status, 'uncertain')
  assert.equal(result.completed_steps, 1)
  assert.equal(result.verified_steps, 0)
  assert.equal(result.stopped_at, 0)
  await runtime.destroy()
})

test('BROW-N1: failed owner receipt never upgrades a readback to VERIFIED', async () => {
  const { runtime, execute } = await batchFixture('proof-receipt-missing')
  const owner = (runtime as any).taskLifecycle()
  const original = owner.recordReceipt.bind(owner)

  owner.recordReceipt = () => {
    throw new Error('receipt_store_failed')
  }

  const result = await execute()
  assert.equal(result.status, 'uncertain')
  assert.equal(result.completed_steps, 1)
  assert.equal(result.verified_steps, 0)
  owner.recordReceipt = original
  await runtime.destroy()
})

test('BROW-N1: failed durable checkpoint halts even after readback and receipt', async () => {
  const { runtime, entry, execute } = await batchFixture('proof-checkpoint-failed')
  const original = (runtime as any).persistBrowserSessionState.bind(runtime)
  let failCheckpoint = false

  entry.view.webContents.onInsertText = () => {
    failCheckpoint = true
  }

  ;(runtime as any).persistBrowserSessionState = () => {
    if (failCheckpoint) {throw new Error('checkpoint_failed')}

    return original()
  }

  const result = await execute()
  assert.equal(result.status, 'uncertain')
  assert.equal(result.completed_steps, 1)
  assert.equal(result.verified_steps, 0)
  assert.equal(result.reason, 'verification_or_checkpoint_failed')
  ;(runtime as any).persistBrowserSessionState = original
  await runtime.destroy()
})

test('BROW-N1: explicit replay of an acknowledged batch operation cannot repeat its effects', async () => {
  const { runtime, entry, execute } = await batchFixture('proof-reentry')
  const first = await execute()
  assert.equal(first.status, 'uncertain')
  assert.equal(first.completed_steps, 2)
  const beforeReplay = entry.view.webContents.inputValue
  const replay = await execute()
  assert.equal(replay.status, 'uncertain')
  assert.equal(entry.view.webContents.inputValue, beforeReplay, 'no mutation replay on same operation ID')
  assert.equal(replay.completed_steps, 0)
  assert.equal(replay.reason, 'prior_batch_effect_requires_reconciliation')
  await runtime.destroy()
})

test('B1.1: runtime snapshot omits elements only for an opt-in compact view', async () => {
  runtimeHome()

  const runtime = new WorkstationBrowserRuntime()

  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>

  await dispatch({
    action: 'browser_navigate',
    task_id: 'task-snapshot-projection',
    arguments: { url: 'https://example.com' }
  })

  const compact = await dispatch({
    action: 'browser_snapshot',
    task_id: 'task-snapshot-projection',
    arguments: { view: 'action_map' }
  })

  assert.equal(compact.success, true)
  assert.equal(compact.snapshot_view, 'action_map')
  assert.match(String(compact.snapshot), /@e1/)
  assert.equal('elements' in compact, false)
  assert.equal(compact.element_count, 1)

  const legacy = await dispatch({
    action: 'browser_snapshot',
    task_id: 'task-snapshot-projection',
    arguments: {}
  })

  assert.equal(legacy.success, true)
  assert.equal(legacy.snapshot_view, undefined)
  assert.ok(Array.isArray(legacy.elements))
  assert.equal(legacy.elements.length, 1)

  await runtime.destroy()
})
