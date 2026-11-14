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
    readonly ipc = { on: () => undefined }
    frameRate = 60
    focused = false
    private clickDeliveryArmed = false
    private clickDelivered = false
    readbackEnabled = false
    inputValue = ''
    suppressInsertText = false
    selected = false
    simulateSelection = false
    simulatePanelScroll = false
    panelScrollTop = 10
    onInsertText: (() => void) | null = null
    onEventWait: (() => void) | null = null
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

        if (method === 'Input.dispatchMouseEvent' && (params as any)?.type === 'mouseReleased' && this.clickDeliveryArmed) {this.clickDelivered = true}
        if (method === 'Input.dispatchMouseEvent' && this.simulateSelection && (params as any)?.type === 'mouseReleased') {this.selected = true}
        if (method === 'Input.dispatchMouseEvent' && this.simulatePanelScroll && (params as any)?.type === 'mouseWheel') {this.panelScrollTop += 120}
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
      if (source.includes('window.__hermesNativeClickDelivery = proof')) {this.clickDeliveryArmed = true; this.clickDelivered = false; return true}
      if (source.includes('const p = window.__hermesNativeClickDelivery')) {return this.clickDelivered}
      if (source.includes('__HERMES_BATCH_EVENT_WAIT_V1__')) {
        this.onEventWait?.()
        return true
      }
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
              selected: this.selected ? 'true' : 'false',
              focused: true,
              scrollContainerToken: this.simulatePanelScroll ? 9 : null,
              scrollTop: this.simulatePanelScroll ? this.panelScrollTop : null,
              scrollY: 0
            }
          : null
      }

      if (source.includes('__hermesWorkstationRefs') && !source.includes('var roots = [document]')) {
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

      if (source.includes('innerHeight') && !source.includes('var roots = [document]')) {
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
      getAppPath: () => process.cwd(),
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

test('P0: event-driven local readback verifies delayed editor update without another action', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>
  try {
    await dispatch({action: 'browser_navigate', task_id: 'task-event-readback',
      arguments: {url: 'https://example.com'}})
    const entry = (runtime as any).entryForTask('task-event-readback', false)
    entry.view.webContents.readbackEnabled = true
    entry.view.webContents.suppressInsertText = true
    let events = 0
    entry.view.webContents.onEventWait = () => {
      events++
      entry.view.webContents.inputValue = 'delayed local draft'
    }
    const result = await dispatch({action: 'browser_batch_actions',
      task_id: 'task-event-readback', operation_id: 'event-readback-one',
      arguments: {steps: [{kind: 'type', ref: '@e1', text: 'delayed local draft'}]}})
    assert.equal(result.status, 'verified')
    assert.equal(result.verified_steps, 1)
    assert.equal(entry.view.webContents.inputValue, 'delayed local draft')
    assert.equal(events, 1)
    assert.equal(result.receipts.length, 1)
  } finally {
    await runtime.destroy()
  }
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
  const store = (runtime as any).sessionStatePersistence()
  assert.equal(store.listPendingAdmissions('task-batch-bad').length, 0, 'invalid batch must not fence future work')
  const next = await executeControlRequest({
    action: 'browser_navigate', task_id: 'task-batch-bad',
    operation_id: 'after-invalid-batch', arguments: {url: 'https://example.com/recovered'}
  })
  assert.notEqual(next.status, 'reconciliation_required')

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


test('P01 RED: verified batch parent is durable across restart and permits next distinct mutation', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>
  const lineage = { task_id: 'task-p01-parent', session_id: 'session-p01-parent', run_id: 'run-p01-parent' }
  await dispatch({ ...lineage, action: 'browser_navigate', operation_id: 'op-p01-setup',
    arguments: { url: 'https://example.com' } })
  const entry = (runtime as any).entryForTask(lineage.task_id, false)
  entry.view.webContents.readbackEnabled = true
  const batch = await dispatch({ ...lineage, action: 'browser_batch_actions',
    operation_id: 'op-p01-batch', arguments: { steps: [
      { kind: 'type', ref: '@e1', text: 'first', clear: true },
      { kind: 'type', ref: '@e1', text: 'second', append: true }
    ] } })
  assert.equal(batch.status, 'verified', JSON.stringify({ status: batch.status, reason: batch.reason, error: (runtime as any).lastError, receipts: batch.receipts }))
  const stateFile = (runtime as any).sessionStatePersistence().filePath as string
  const onDisk = JSON.parse(fs.readFileSync(stateFile, 'utf8'))
  assert.equal(onDisk.operationAdmissions['op-p01-batch'].acknowledged, true,
    'the parent receipt (not its child) must durably close the admitted batch')
  assert.equal(onDisk.receipts[lineage.task_id].operationId, 'op-p01-batch')
  assert.equal(onDisk.receipts[lineage.task_id].action, 'browser_batch_actions')
  await runtime.destroy()
  const rebooted = new WorkstationBrowserRuntime()
  const reopened = (rebooted as any).sessionStatePersistence().load()
  assert.equal(reopened.operationAdmissions['op-p01-batch'].acknowledged, true)
  const next = await (rebooted as any).executeControlRequest({
    ...lineage, action: 'browser_navigate', operation_id: 'op-p01-next',
    arguments: { url: 'https://example.com/after' }
  })
  assert.notEqual(next.reason, 'prior_operation_requires_reconciliation')
  await rebooted.destroy()
})

test('BROW-N2 RED: an unverified click must not mint an owner receipt that looks verified', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (
    request: Record<string, unknown>
  ) => Promise<Record<string, any>>
  const taskId = 'task-no-unverified-receipt'
  await dispatch({action: 'browser_navigate', task_id: taskId,
    operation_id: 'op-setup-n2', arguments: {url:'https://example.com'} })
  const first = await dispatch({action: 'browser_batch_actions', task_id: taskId,
    operation_id: 'op-batch-n2', arguments: {steps:[{kind:'click',ref:'@e1'}]} })
  assert.equal(first.status, 'uncertain')
  assert.equal(first.completed_steps, 1)
  assert.equal(first.verified_steps, 0)
  assert.deepEqual(first.receipts, [null], 'no verified receipt should be published for an unverified action')
  const state = (runtime as any).sessionStatePersistence().load()
  assert.equal(state.operationAdmissions['op-batch-n2'].acknowledged, undefined)
  assert.equal(state.operationAdmissions['op-batch-n2'].uncertainty?.reason, 'readback_unavailable')
  assert.equal(state.operationAdmissions['op-batch-n2'].uncertainty?.verifiedSteps, 0)
  assert.notEqual(state.receipts?.[taskId]?.operationId, 'op-batch-n2:0')
  await runtime.destroy()
})

test('BROW-N2: synthetic selected conversation closes a verified batch and allows next navigation', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (x: Record<string, unknown>) => Promise<Record<string, any>>
  const ids = { task_id: 'task-semantic-n2', session_id: 'session-semantic-n2', run_id: 'run-semantic-n2' }
  await dispatch({ ...ids, action: 'browser_navigate', operation_id: 'op-semantic-setup',
    arguments: {url:'https://example.com'} })
  const entry = (runtime as any).entryForTask(ids.task_id, false)
  entry.view.webContents.readbackEnabled = true
  entry.view.webContents.simulateSelection = true
  const batch = await dispatch({ ...ids, action: 'browser_batch_actions', operation_id: 'op-semantic-selected',
    arguments: {steps:[{kind:'click',ref:'@e1',postcondition:{kind:'selected'}}]} })
  assert.equal(batch.status,'verified',JSON.stringify({reason:batch.reason,receipts:batch.receipts}))
  assert.equal(batch.verified_steps,1)
  const ledger = (runtime as any).sessionStatePersistence().load()
  assert.equal(ledger.operationAdmissions['op-semantic-selected'].acknowledged,true)
  await runtime.destroy()
  const rebooted = new WorkstationBrowserRuntime()
  const navigate = await (rebooted as any).executeControlRequest({ ...ids, action:'browser_navigate',
    operation_id:'op-semantic-next',arguments:{url:'https://example.com/next'} })
  assert.notEqual(navigate.reason,'prior_operation_requires_reconciliation')
  await rebooted.destroy()
})
test('BROW-N2: panel-wheel movement uses verified container offset rather than window scrollY', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const dispatch = (runtime as any).executeControlRequest.bind(runtime) as (x: Record<string, unknown>) => Promise<Record<string, any>>
  const ids = { task_id:'task-semantic-scroll',session_id:'session-semantic-scroll',run_id:'run-semantic-scroll' }
  await dispatch({...ids,action:'browser_navigate',operation_id:'op-scroll-setup',
    arguments:{url:'https://example.com'} })
  const entry = (runtime as any).entryForTask(ids.task_id,false)
  entry.view.webContents.readbackEnabled=true
  entry.view.webContents.simulatePanelScroll=true
  const batch = await dispatch({...ids,action:'browser_batch_actions',operation_id:'op-scroll-batch',
    arguments:{steps:[{kind:'scroll',direction:'down'}]} })
  assert.equal(batch.status,'verified',JSON.stringify({reason:batch.reason}))
  assert.equal(batch.verified_steps,1)
  await runtime.destroy()
})
