import assert from 'node:assert/strict'
import fs from 'node:fs'
import type { Server } from 'node:http'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test, vi } from 'vitest'

const electron = vi.hoisted(() => {
  type Listener = (...args: unknown[]) => void
  const windows: FakeBrowserWindow[] = []
  const loadedUrls: string[] = []

  class FakeWebContents {
    private destroyed = false
    private readonly listeners = new Map<string, Listener[]>()
    private title = ''
    private url = 'about:blank'
    frameRate = 60
    focused = false
    readonly ipc = { on: () => undefined }
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
      for (const listener of this.listeners.get(event) ?? []) {
        listener(...args)
      }
    }

    setWindowOpenHandler(): void {}
    setFrameRate(rate: number): void {
      this.frameRate = rate
    }

    async loadURL(url: string): Promise<void> {
      loadedUrls.push(url)
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
      if (source.includes('__hermesWorkstationRefs')) {
        if (source.includes('ClipboardEvent') && source.includes("'paste'")) {
          return { success: true, count: 12 }
        }

        if (source.includes('byRef.get')) {
          return {
            success: true,
            x: 150,
            y: 150,
            target: {
              ref: '@e1',
              tag: 'textarea',
              role: 'textbox',
              label: 'Description editor',
              testid: 'desc-editor',
              name: 'description'
            }
          }
        }
      }

      if (source.includes('fetch(')) {
        return {
          success: true,
          status: 200,
          ok: true,
          url: 'https://example.com/api/v1/resource',
          content_type: 'application/json',
          text: '{"status":"ok","id":123}',
          json: { status: 'ok', id: 123 }
        }
      }

      if (source.includes('isSkeletonOrLoading') || source.includes('hasProgress')) {
        return false
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
            tag: 'textarea',
            role: 'textbox',
            label: 'Description editor',
            name: 'description',
            value: '',
            x: 150,
            y: 150,
            w: 300,
            h: 120
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
    private bounds = { x: 0, y: 0, width: 1280, height: 800 }
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
    loadedUrls,
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
      },
      fromPath: () => ({clearCache: async () => undefined})
    }
  }
})

vi.mock('electron', () => electron)

import { WorkstationBrowserRuntime, WorkstationControllerFault } from './workstation-browser-runtime'
import { BrowserSessionStateFilePersistence } from './workstation-browser-session-state'

const tempHomes: string[] = []

function runtimeHome(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-runtime-test-'))
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

test('browser_type supports plain_text_paste returning semantic_effect paste_text', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-paste-1',
    arguments: { url: 'https://example.com/editor' }
  })

  const pasteResult = (await executeControlRequest({
    action: 'browser_type',
    task_id: 'task-paste-1',
    arguments: {
      ref: '@e1',
      text: 'Line 1\nLine 2',
      mode: 'plain_text_paste',
      semantic_anchor: { type: 'testid', value: 'desc-editor' }
    }
  })) as Record<string, unknown>

  assert.equal(pasteResult.semantic_effect, 'paste_text')
  assert.equal(pasteResult.chars_inserted, 13)
  assert.equal((pasteResult.target as Record<string, unknown>)?.ref, '@e1')

  await runtime.destroy()
})

test('browser_read_http executes GET and returns structured JSON/text', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-http-1',
    arguments: { url: 'https://example.com/dashboard' }
  })

  const httpResult = (await executeControlRequest({
    action: 'browser_read_http',
    task_id: 'task-http-1',
    arguments: {
      url: 'https://example.com/api/v1/resource',
      method: 'GET'
    }
  })) as Record<string, unknown>

  assert.equal(httpResult.status, 200)
  assert.equal(httpResult.ok, true)
  assert.equal(httpResult.content_type, 'application/json')
  assert.deepEqual(httpResult.json, { status: 'ok', id: 123 })

  const relativeHead = (await executeControlRequest({
    action: 'browser_read_http', task_id: 'task-http-1',
    arguments: { url: '/api/v1/resource', method: 'HEAD' }
  })) as Record<string, unknown>

  assert.equal(relativeHead.status, 200)

  await runtime.destroy()
})

test('browser_read_http rejects mutation methods, request body, and loopback destinations', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()

  const executeControlRequest = (
    runtime as unknown as {
      executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    }
  ).executeControlRequest.bind(runtime)

  await executeControlRequest({
    action: 'browser_navigate',
    task_id: 'task-http-sec',
    arguments: { url: 'https://example.com' }
  })

  // 1. Rejects POST
  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http',
      task_id: 'task-http-sec',
      arguments: { url: 'https://example.com/api', method: 'POST' }
    })
  }, /only GET and HEAD methods allowed/)

  // 2. Rejects request body
  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http',
      task_id: 'task-http-sec',
      arguments: { url: 'https://example.com/api', method: 'GET', body: 'payload' }
    })
  }, /request body not permitted/)

  // 3. Rejects cross-origin destinations by default (including loopback/private)
  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http',
      task_id: 'task-http-sec',
      arguments: { url: 'http://127.0.0.1:8080/secret', method: 'GET' }
    })
  }, /cross-origin browser readback denied/)

  // 4. Rejects RFC1918 private IP
  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http',
      task_id: 'task-http-sec',
      arguments: { url: 'http://192.168.1.50/admin', method: 'GET' }
    })
  }, /cross-origin browser readback denied/)

  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http', task_id: 'task-http-sec',
      arguments: { url: 'https://other.example/api', method: 'GET' }
    })
  }, /cross-origin browser readback denied/)

  await assert.rejects(async () => {
    await executeControlRequest({
      action: 'browser_read_http', task_id: 'task-http-sec',
      arguments: { url: '/api', method: 'GET', headers: { Authorization: 'secret' } }
    })
  }, /forbidden request header/)

  await runtime.destroy()
})

test('WorkstationControllerFault correctly classifies TIMEOUT_UNCERTAIN and FORBIDDEN_DESTINATION', () => {
  try {
    throw new WorkstationControllerFault({
      error_code: 'TIMEOUT_UNCERTAIN',
      message: 'Mutation timed out during dispatch',
      retryable: false,
      retry_after_ms: 0,
      state_changed: true,
      recommended_action: 'RECONCILE_EFFECT',
      details: {}
    })
  } catch (err) {
    assert.ok(err instanceof WorkstationControllerFault)
    assert.equal(err.structured.error_code, 'TIMEOUT_UNCERTAIN')
    assert.equal(err.structured.state_changed, true)
    assert.equal(err.structured.retryable, false)
    assert.equal(err.structured.recommended_action, 'RECONCILE_EFFECT')
  }
})


test('live Browser controller repairs stale discovery descriptor', async () => {
  const home = runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  try {
    await runtime.startControlServer()
    const file = path.join(home, 'Runtime', 'browser-control.json')
    const original = JSON.parse(fs.readFileSync(file, 'utf8'))
    fs.writeFileSync(file, JSON.stringify({...original, pid: 999999999, url: 'http://127.0.0.1:1', token: 'stale-test'}))
    await new Promise(resolve => setTimeout(resolve, 2100))
    const repaired = JSON.parse(fs.readFileSync(file, 'utf8'))
    assert.equal(repaired.pid, process.pid)
    assert.equal(repaired.url, original.url)
    assert.equal(repaired.token, original.token)
  } finally {
    await runtime.destroy()
  }
})


test('live Browser controller relistens without restarting its runtime', async () => {
  const home = runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  try {
    await runtime.startControlServer()
    const owner = runtime as unknown as {control: {server: Server; url: string; token: string}}
    const originalServer = owner.control.server
    const originalToken = owner.control.token
    await new Promise<void>((resolve, reject) => originalServer.close(error => error ? reject(error) : resolve()))
    assert.equal(originalServer.listening, false)
    await new Promise(resolve => setTimeout(resolve, 2200))
    assert.equal(owner.control.server, originalServer)
    assert.equal(originalServer.listening, true)
    const discovered = JSON.parse(fs.readFileSync(path.join(home, 'Runtime', 'browser-control.json'), 'utf8'))
    assert.equal(discovered.url, owner.control.url)
    assert.equal(discovered.token, originalToken)
  } finally {
    await runtime.destroy()
  }
})

test('P02 authority: agent controller cannot reconcile a pending admission with self-asserted review', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  try {
    const controller = runtime as unknown as {
      executeControlRequest(req: Record<string, unknown>): Promise<Record<string, unknown>>
      sessionStatePersistence(): {
        admitBrowserMutation(req: Record<string, string>): string
        load(): {operationAdmissions: Record<string, {terminal?: {kind: string}}>} | null
      }
    }
    const store = controller.sessionStatePersistence()
    const operationId = 'p02-agent-forgery'
    assert.equal(store.admitBrowserMutation({
      operationId, action: 'browser_click', taskId: 'task-security',
      sessionId: 'session-security', runId: 'run-security', tabId: 'tab-security',
      argumentsDigest: 'a'.repeat(64)
    }), 'admitted')
    await assert.rejects(
      controller.executeControlRequest({
        action: 'browser_admissions_reconcile', task_id: 'task-security',
        session_id: 'session-security', run_id: 'run-security',
        arguments: {operation_id: operationId, reason: 'OPERATOR_RECONCILED', evidence: 'OPERATOR_REVIEW', resolved_by: 'human'}
      }),
      /agent_reconciliation_forbidden/
    )
    assert.equal(store.load()?.operationAdmissions?.[operationId]?.terminal, undefined)
    const pending = await controller.executeControlRequest({
      action: 'browser_admissions_inspect', task_id: 'task-security', arguments: {task_id: 'task-security'}
    })
    assert.equal(pending.pending_count, 1)
  } finally {
    await runtime.destroy()
  }
})

test('P02 identity: mutating Browser calls without task, run or session never create unbound admissions', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  try {
    const controller = runtime as unknown as {
      executeControlRequest(req: Record<string, unknown>): Promise<Record<string, unknown>>
      sessionStatePersistence(): {load(): {operationAdmissions: Record<string, unknown>} | null}
    }
    await assert.rejects(
      controller.executeControlRequest({
        action: 'browser_navigate', operation_id: 'p02-unbound-forbidden',
        arguments: {url: 'https://example.test/no-owner'}
      }),
      /browser_owner_identity_required/
    )
    assert.equal(controller.sessionStatePersistence().load()?.operationAdmissions?.['p02-unbound-forbidden'], undefined)
  } finally {
    await runtime.destroy()
  }
})

test('P02 restart: pending batch prevents implicit remote URL load on snapshot', async () => {
  runtimeHome()
  const identity = {task_id: 'p02-restart-task', session_id: 'p02-restart-session', run_id: 'p02-restart-run'}
  const first = new WorkstationBrowserRuntime()
  let second: WorkstationBrowserRuntime | null = null
  const owner = (runtime: WorkstationBrowserRuntime) => runtime as unknown as {
    executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    sessionStatePersistence(): BrowserSessionStateFilePersistence
  }
  try {
    await owner(first).executeControlRequest({
      ...identity, action: 'browser_navigate', operation_id: 'p02-prior-nav',
      arguments: {url: 'https://example.com/previous'}
    })
    const persistence = owner(first).sessionStatePersistence()
    const previous = persistence.load()!
    const tab = previous.tabs.find(item => item.browserTaskId === identity.task_id)
    assert.ok(tab)
    assert.equal(previous.operationAdmissions['p02-prior-nav']?.acknowledged, true)
    const file = persistence.filePath
    await first.destroy()
    const store = new BrowserSessionStateFilePersistence(file)
    assert.equal(store.admitBrowserMutation({
      operationId: 'p02-pending-batch', action: 'browser_batch_actions',
      taskId: identity.task_id, sessionId: identity.session_id, runId: identity.run_id,
      tabId: tab.id, argumentsDigest: 'b'.repeat(64)
    }), 'admitted')
    electron.loadedUrls.length = 0
    second = new WorkstationBrowserRuntime()
    await owner(second).executeControlRequest({...identity, action: 'browser_snapshot', arguments: {}})
    assert.deepEqual(electron.loadedUrls.filter(url => url.startsWith('https://')), [],
      'snapshot must not replay a remote URL while a batch is uncertain')
    const blocked = await owner(second).executeControlRequest({
      ...identity, action: 'browser_navigate', operation_id: 'p02-next-nav',
      arguments: {url: 'https://example.com/next'}
    })
    assert.equal(blocked.status, 'reconciliation_required')
    assert.equal(store.load()?.operationAdmissions['p02-pending-batch']?.terminal, undefined)
  } finally {
    await second?.destroy()
    await first.destroy()
  }
})

test('P0: native operator batch review preserves durable terminal and prevents replay', async () => {
  runtimeHome()
  const runtime = new WorkstationBrowserRuntime()
  const controller = runtime as unknown as {
    executeControlRequest(request: Record<string, unknown>): Promise<Record<string, unknown>>
    sessionStatePersistence(): BrowserSessionStateFilePersistence
  }
  const taskId = 'p0-batch-human-review'
  const sessionId = 'p0-batch-review-session'
  const runId = 'p0-batch-review-run'
  const operationId = 'p0-batch-human-op-1'
  try {
    await controller.executeControlRequest({
      action: 'browser_navigate', task_id: taskId, session_id: sessionId,
      run_id: runId, operation_id: 'p0-batch-prior-navigate',
      arguments: {url: 'https://example.test/batch'}
    })
    const store = controller.sessionStatePersistence()
    const snapshot = store.load()!
    const tab = snapshot.tabs.find(t => t.browserTaskId === taskId)!
    assert.ok(tab)
    ;((runtime as any).entries.get(tab.id).view.webContents as any).id = 77
    assert.equal(store.admitBrowserMutation({
      operationId, action: 'browser_batch_actions', taskId, sessionId, runId,
      tabId: tab.id, argumentsDigest: 'c'.repeat(64)
    }), 'admitted')
    store.recordBatchUncertainty({
      operationId, reason:'click_postcondition_not_observed',
      completedSteps:1, verifiedSteps:0, stoppedAt:0
    })
    assert.equal(runtime.listUncertainBatchReviews().some(r => r.operationId === operationId), true)
    const readable = await controller.executeControlRequest({
      action:'browser_snapshot', task_id:taskId, session_id:sessionId, run_id:runId,
      arguments:{full:false}
    })
    assert.notEqual(readable.status, 'reconciliation_required', 'read-only inspection must work while writes are fenced')
    const cancel = await runtime.reviewUncertainBatch(operationId, async () => false)
    assert.equal(cancel.status, 'cancelled')
    assert.equal(store.load()?.operationAdmissions?.[operationId]?.terminal, undefined)
    const blocked = await controller.executeControlRequest({
      action:'browser_navigate',task_id:taskId,session_id:sessionId,run_id:runId,
      operation_id:'p0-batch-blocked-nav',
      arguments:{url:'https://example.test/should-not-load'}
    })
    assert.equal(blocked.status, 'reconciliation_required')
    const approved = await runtime.reviewUncertainBatch(operationId, async () => true)
    assert.equal(approved.status, 'reconciled')
    assert.equal(store.load()?.operationAdmissions?.[operationId]?.terminal?.reason, 'OPERATOR_RECONCILED')
    assert.equal(runtime.listUncertainBatchReviews().some(r => r.operationId === operationId), false)
    const after = await controller.executeControlRequest({
      action:'browser_navigate',task_id:taskId,session_id:sessionId,run_id:runId,
      operation_id:'p0-batch-after-reviewed',
      arguments:{url:'https://example.test/after-review'}
    })
    assert.notEqual(after.status, 'reconciliation_required')
    await assert.rejects(runtime.reviewUncertainBatch(operationId,async () => true),
      /human_batch_review_evidence_insufficient/)
  } finally {
    await runtime.destroy()
  }
})
test('P0 agent can safely recover a legacy zero-effect batch without human bypass', async () => {
  runtimeHome()
  const runtime=new WorkstationBrowserRuntime()
  const bridge=runtime as unknown as {
    executeControlRequest(req:Record<string,unknown>):Promise<Record<string,any>>
    sessionStatePersistence():BrowserSessionStateFilePersistence
  }
  const task='p0-auto-legacy-task'
  const identity={task_id:task,session_id:task,run_id:task}
  try{
    await bridge.executeControlRequest({...identity,action:'browser_navigate',
      operation_id:'p0-auto-first-navigation',arguments:{url:'https://example.test/pre'}})
    const store=bridge.sessionStatePersistence()
    const tabId=store.load()?.tabs.find(t=>t.browserTaskId===task)?.id
    assert.ok(tabId)
    const id='p0-agent-rejected-batch'
    assert.equal(store.admitBrowserMutation({
      operationId:id,taskId:task,sessionId:task,runId:task,
      tabId,action:'browser_batch_actions',argumentsDigest:'e'.repeat(64)
    }),'admitted')
    store.recordBatchUncertainty({
      operationId:id,reason:'invalid_step',stoppedAt:0,completedSteps:0,verifiedSteps:0
    })
    const safe=await bridge.executeControlRequest({...identity,action:'browser_admissions_recover_safe',arguments:{}})
    assert.equal(safe.status,'ready')
    assert.deepEqual(safe.safely_recovered,[id])
    assert.equal(store.load()?.operationAdmissions[id]?.terminal?.kind,'NOT_DISPATCHED')
    const next=await bridge.executeControlRequest({...identity,action:'browser_navigate',
      operation_id:'p0-auto-next-navigation',arguments:{url:'https://example.test/after'}})
    assert.notEqual(next.status,'reconciliation_required')
    // Real uncertain effects cannot be agent-approved by the same tool.
    const second='p0-agent-real-uncertainty'
    assert.equal(store.admitBrowserMutation({
      operationId:second,taskId:task,sessionId:task,runId:task,
      tabId,action:'browser_batch_actions',argumentsDigest:'f'.repeat(64)
    }),'admitted')
    store.recordBatchUncertainty({
      operationId:second,reason:'click_postcondition_not_observed',
      stoppedAt:0,completedSteps:1,verifiedSteps:0
    })
    const blocked=await bridge.executeControlRequest({...identity,action:'browser_admissions_recover_safe',arguments:{}})
    assert.equal(blocked.status,'reconciliation_required')
    assert.equal(blocked.blocked_operation_id,second)
    assert.deepEqual(blocked.safely_recovered,[])
    assert.equal(store.load()?.operationAdmissions[second]?.terminal,undefined)
  }finally{
    await runtime.destroy()
  }
})