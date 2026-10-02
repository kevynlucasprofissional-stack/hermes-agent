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

import { WorkstationBrowserRuntime, WorkstationControllerFault } from './workstation-browser-runtime'

const tempHomes: string[] = []

function runtimeHome(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-runtime-test-'))
  tempHomes.push(dir)
  process.env.HERMES_HOME = dir

  return dir
}

afterEach(() => {
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
