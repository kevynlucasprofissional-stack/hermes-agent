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


type RuntimeDouble = { cdp: (_wc: unknown, method: string, args?: unknown) => Promise<unknown>; assertAgentControl: (taskId: string) => void }
type Request = { action: string; task_id: string; session_id?: string; run_id?: string; operation_id?: string; arguments?: Record<string, unknown> }

async function runControl(runtime: WorkstationBrowserRuntime, req: Request): Promise<Record<string, unknown>> {
  return (runtime as unknown as { executeControlRequest(r: Request): Promise<Record<string, unknown>> }).executeControlRequest(req)
}

function configGrant(home: string, dir: string) {
  const config = ['browser:', '  workstation:', '    upload_grants:', '      - task_id: task-upload',
    '        session_id: session-upload', '        run_id: run-upload',
    '        expires_at: 2099-01-01T00:00:00Z', '        allowed_origins:', '          - https://example.test', '        allowed_roots:',
    `          - ${JSON.stringify(dir)}`].join('\n')

  fs.writeFileSync(path.join(home, 'config.yaml'), config)
}

async function boundRuntime(home: string) {
  const runtime = new WorkstationBrowserRuntime()
  await runControl(runtime, {
    action: 'browser_navigate', task_id: 'task-upload', session_id: 'session-upload', run_id: 'run-upload',
    arguments: { url: 'https://example.test/upload' }
  })

  return runtime
}

const fileRequest = (file: string, operation_id = 'upload-op-1'): Request => ({
  action: 'browser_file_upload', task_id: 'task-upload', session_id: 'session-upload',
  run_id: 'run-upload', operation_id, arguments: { files: [file], selector: 'input[type=file]' }
})

test('no operator grant fails before any CDP file selection', async () => {
  const home = runtimeHome()
  const file = path.join(home, 'image.png')
  fs.writeFileSync(file, 'fixture')
  const runtime = await boundRuntime(home)

  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp').mockImplementation(async (_wc: unknown, method: string) => {
    if (method === 'Runtime.evaluate') {return { result: { objectId: 'object-1' } }}

    if (method === 'Runtime.callFunctionOn') {return { result: { value: 1 } }}

    return {}
  })

  await assert.rejects(() => runControl(runtime, fileRequest(file)), /upload_scope_required/)
  assert.equal(cdp.mock.calls.some(call => call[1] === 'DOM.setFileInputFiles'), false)
  await runtime.destroy()
})

test('valid grant selects file and returns only safe receipt; replay cannot select again', async () => {
  const home = runtimeHome()
  const root = path.join(home, 'assets')
  fs.mkdirSync(root)
  const file = path.join(root, 'image.png')
  fs.writeFileSync(file, 'fixture')
  configGrant(home, root)
  const runtime = await boundRuntime(home)

  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp').mockImplementation(async (_wc: unknown, method: string) => {
    if (method === 'Runtime.evaluate') {return { result: { objectId: 'object-1' } }}

    if (method === 'Runtime.callFunctionOn') {return { result: { value: 1 } }}

    return {}
  })

  const selected = await runControl(runtime, fileRequest(file))
  assert.equal(selected.status, 'selected')
  assert.equal(selected.file_count, 1)
  assert.ok(selected.receipt)
  assert.equal(JSON.stringify(selected).includes(home), false)
  assert.equal(cdp.mock.calls.filter(call => call[1] === 'DOM.setFileInputFiles').length, 1)
  const replay = await runControl(runtime, fileRequest(file))
  assert.equal(replay.status, 'uncertain')
  assert.equal(cdp.mock.calls.filter(call => call[1] === 'DOM.setFileInputFiles').length, 1)
  await runtime.destroy()
})

test('human control guard denies file upload before CDP', async () => {
  const home = runtimeHome()
  const root = path.join(home, 'assets')
  fs.mkdirSync(root)
  const file = path.join(root, 'image.png')
  fs.writeFileSync(file, 'fixture')
  configGrant(home, root)
  const runtime = await boundRuntime(home)
  vi.spyOn(runtime as unknown as RuntimeDouble, 'assertAgentControl').mockImplementation(() => { throw new Error('USER_CONTROL_ACTIVE') })
  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp')
  await assert.rejects(() => runControl(runtime, fileRequest(file, 'upload-op-human')), /USER_CONTROL_ACTIVE/)
  assert.equal(cdp.mock.calls.some(call => call[1] === 'DOM.setFileInputFiles'), false)
  await runtime.destroy()
})

test('outside-grant file is rejected before CDP without revealing the local path', async () => {
  const home = runtimeHome()
  const root = path.join(home, 'assets')
  fs.mkdirSync(root)
  const file = path.join(home, 'private.txt')
  fs.writeFileSync(file, 'private')
  configGrant(home, root)
  const runtime = await boundRuntime(home)
  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp')
  await assert.rejects(() => runControl(runtime, fileRequest(file, 'upload-private')), /upload_scope_denied/)
  assert.equal(cdp.mock.calls.some(call => call[1] === 'DOM.setFileInputFiles'), false)
  await runtime.destroy()
})

test('absent or ambiguous file input terminalizes before CDP selection', async () => {
  const home = runtimeHome()
  const root = path.join(home, 'assets')
  fs.mkdirSync(root)
  const file = path.join(root, 'fixture.txt')
  fs.writeFileSync(file, 'fixture')
  configGrant(home, root)
  const runtime = await boundRuntime(home)
  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp').mockImplementation(async () => ({result:{subtype:'null'}}))
  await assert.rejects(() => runControl(runtime, fileRequest(file, 'upload-no-input')), /file_input_not_found_or_ambiguous/)
  assert.equal(cdp.mock.calls.some(call => call[1] === 'DOM.setFileInputFiles'), false)
  const replay = await runControl(runtime, fileRequest(file, 'upload-no-input'))
  assert.equal(replay.status, 'not_dispatched')
  await runtime.destroy()
})

test('ambiguous CDP failure must not leak a path or select twice on replay', async () => {
  const home = runtimeHome()
  const root = path.join(home, 'assets')
  fs.mkdirSync(root)
  const file = path.join(root, 'fixture.txt')
  fs.writeFileSync(file, 'fixture')
  configGrant(home, root)
  const runtime = await boundRuntime(home)

  const cdp = vi.spyOn(runtime as unknown as RuntimeDouble, 'cdp').mockImplementation(async (_wc, method) => {
    if (method === 'Runtime.evaluate') {return { result: { objectId: 'input-object-1' } }}

    if (method === 'DOM.setFileInputFiles') {throw new Error('CDP failed for local path: ' + file)}

    return {}
  })

  await assert.rejects(async () => {
    try { await runControl(runtime, fileRequest(file, 'upload-uncertain')) }
    catch (error) { assert.equal(String(error).includes(file), false); throw error }
  }, /upload_cdp_effect_uncertain/)
  assert.equal(cdp.mock.calls.filter(call => call[1] === 'DOM.setFileInputFiles').length, 1)
  const replay = await runControl(runtime, fileRequest(file, 'upload-uncertain'))
  assert.equal(replay.status, 'uncertain')
  assert.equal(cdp.mock.calls.filter(call => call[1] === 'DOM.setFileInputFiles').length, 1)
  await runtime.destroy()
})
