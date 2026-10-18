// health: allow FILE_LINES -- OL-MVP P2 and P2.1 native browser and taskrun verification probe
/**
 * Integrated Desktop/Browser load evidence.
 *
 * This test intentionally runs the real dev Electron shell with the real
 * `hermes serve` backend from the mock-backend fixture. The inference server
 * is fake, but Chromium, BrowserTask lifecycle, the authenticated controller,
 * resource projection, and the renderer IPC bridge are real.
 *
 * `headless: true` is mandatory here: the test must never reveal a desktop
 * window while exercising native WebContentsView instances.
 */

import * as fs from 'node:fs'
import * as http from 'node:http'
import * as path from 'node:path'
import { DatabaseSync } from 'node:sqlite'

import {
  buildAppEnv,
  launchDesktop,
  type MockBackendFixture,
  setupMockBackend,
  waitForAppReady
} from './fixtures'
import { OL_MVP_READONLY_CARDS, OL_MVP_READONLY_PATH, OL_MVP_READONLY_TITLE, renderOlMvpReadOnlyCards } from './ol-mvp-p1-readonly-cards'
import { expect, test } from './test'

interface ControllerFile {
  url: string
  token: string
  runtime: string
}

interface ControllerResponse {
  success: boolean
  schema_version?: number
  result?: Record<string, unknown>
  runtime?: string
  task_id?: string | null
  generated_at?: string
  resources?: Array<Record<string, unknown>>
  events?: Array<Record<string, unknown>>
  error?: string
}

interface BrowserTaskRecord {
  taskId: string
  sessionHost?: string | null
  status?: string
  parked?: boolean
}

interface WorkstationBridge {
  ensure: () => Promise<Record<string, unknown>>
  attach: (
    bounds: Record<string, number>,
    host?: string,
    preferredTaskId?: string
  ) => Promise<Record<string, unknown>>
  setBounds: (bounds: Record<string, number>, expectedHost?: string) => Promise<Record<string, unknown>>
  detach: (expectedHost?: string) => Promise<Record<string, unknown>>
  setVisible: (visible: boolean, expectedHost?: string) => Promise<Record<string, unknown>>
  transferViewport: (targetHost: string, bounds: Record<string, number>) => Promise<Record<string, unknown>>
  resources: () => Promise<{ runtime: string; resources: Array<Record<string, unknown>> }>
  events: (
    taskId?: string | null,
    limit?: number
  ) => Promise<{ runtime: string; task_id: string | null; events: Array<Record<string, unknown>> }>
  listTasks: () => Promise<BrowserTaskRecord[]>
  showTask: (taskId: string, bounds: Record<string, number>, host?: string) => Promise<BrowserTaskRecord>
  hideTask: (taskId: string) => Promise<unknown>
  parkTask: (taskId: string) => Promise<unknown>
  destroyTask: (taskId: string) => Promise<unknown>
}

interface DesktopBridgeWindow {
  hermesDesktop: {
    api: <T>(request: { path: string; timeoutMs?: number; connectionId?: string }) => Promise<T>
    workstationBrowser: WorkstationBridge
  }
}

interface NativeViewportBounds {
  x: number
  y: number
  width: number
  height: number
}

interface NativeViewportChild {
  bounds: NativeViewportBounds
  webContentsId: number | null
  url: string
}

interface NativeViewportSnapshot {
  contentBounds: NativeViewportBounds
  children: NativeViewportChild[]
  maximized: boolean
}

interface SustainedLoadEvidence {
  accepted: true
  task_count: number
  requested_rounds: number
  completed_rounds: number
  requested_duration_ms: number
  observed_duration_ms: number
  chat_turns: number
}

function readBoundedInteger(name: string, fallback: number, minimum: number, maximum: number): number {
  const raw = process.env[name]?.trim()

  if (!raw) {
    return fallback
  }

  const value = Number(raw)

  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name} must be an integer between ${minimum} and ${maximum}`)
  }

  return value
}

const TASK_COUNT = 4
const SUSTAINED_TASK_COUNT = readBoundedInteger('HERMES_DESKTOP_E2E_SUSTAINED_TASKS', 8, 1, 32)
const SUSTAINED_ROUNDS = readBoundedInteger('HERMES_DESKTOP_E2E_SUSTAINED_ROUNDS', 3, 1, 300)
const SUSTAINED_DURATION_MS = readBoundedInteger('HERMES_DESKTOP_E2E_SUSTAINED_DURATION_MS', 0, 0, 300_000)
const SUSTAINED_CHAT_TURNS = readBoundedInteger('HERMES_DESKTOP_E2E_SUSTAINED_CHAT_TURNS', 3, 1, 32)

let fixture: MockBackendFixture | null = null
let pageServer: http.Server | null = null
let pageBaseUrl = ''
let controller: ControllerFile | null = null
let sustainedLoadEvidence: SustainedLoadEvidence | null = null
// Isolated loopback side-effect counter for the uncertain native Browser proof.
let uncertainNativeEffectCount = 0

async function startDeterministicPageServer(): Promise<void> {
  pageServer = http.createServer((request, response) => {
    if (request.url === OL_MVP_READONLY_PATH) {
      response.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
      response.end(renderOlMvpReadOnlyCards())

      return
    }

    if (request.url === '/p0-native-effect-state') {
      response.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' })
      response.end(JSON.stringify({ applied: uncertainNativeEffectCount }))

      return
    }

    if (request.url === '/p0-native-effect-commit' && request.method === 'POST') {
      uncertainNativeEffectCount += 1
      response.writeHead(200, { 'content-type': 'text/plain' })
      setTimeout(() => response.end('committed'), 300)

      return
    }

    const taskId = decodeURIComponent((request.url ?? '/').replace(/^\//, '')) || 'unknown'

    if (taskId === 'p0-uncertain-native') {
      response.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
      response.end(`<!doctype html><html><head><title>H013 ${taskId}</title></head><body>
        <button type="button" data-testid="commit-once" onclick="fetch('/p0-native-effect-commit', {method:'POST'}).then(() => { document.getElementById('effect-state').textContent = 'COMMITTED'; })">Commit external side effect</button>
        <output id="effect-state">PENDING external effect. This page is intentionally deterministic and local.</output>
        </body></html>`)

      return
    }

    if (taskId.startsWith('hwh-form')) {
      response.writeHead(200, {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store'
      })
      response.end(`<!doctype html><html><head><title>HWH Form ${taskId}</title></head><body>
        <main data-task="${taskId}">
          <h1>HWH Form ${taskId}</h1>
          <form onsubmit="return false;">
            <label for="form-input">Input ${taskId}</label>
            <input id="form-input" name="field_${taskId}" value="initial_${taskId}" />
          </form>
        </main>
      </body></html>`)

      return
    }

    response.writeHead(200, {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store'
    })
    response.end(
      `<!doctype html><html><head><title>H013 ${taskId}</title></head><body><main data-task="${taskId}">H013 ${taskId}</main></body></html>`
    )
  })

  await new Promise<void>((resolve, reject) => {
    pageServer!.once('error', reject)
    pageServer!.listen(0, '127.0.0.1', () => resolve())
  })

  const address = pageServer.address()

  if (!address || typeof address === 'string') {
    throw new Error('H013 deterministic page server did not bind a TCP port')
  }

  pageBaseUrl = `http://127.0.0.1:${address.port}`
}

async function readControllerFile(filePath: string): Promise<ControllerFile> {
  const raw = JSON.parse(await fs.promises.readFile(filePath, 'utf8')) as Partial<ControllerFile>

  if (!raw.url || !raw.token || raw.runtime !== 'electron-chromium') {
    throw new Error('H013 controller file is incomplete')
  }

  return { url: raw.url, token: raw.token, runtime: raw.runtime }
}

async function controllerRequest(endpoint: string, init: RequestInit = {}): Promise<ControllerResponse> {
  if (!controller) {
    throw new Error('H013 controller is not ready')
  }

  const response = await fetch(`${controller.url}${endpoint}`, {
    ...init,
    headers: {
      authorization: `Bearer ${controller.token}`,
      ...(init.headers ?? {})
    }
  })

  const body = (await response.json()) as ControllerResponse

  if (!response.ok || body.success !== true) {
    throw new Error(`H013 controller request failed (${response.status}): ${body.error ?? 'unknown error'}`)
  }

  return body
}

function comparableResourceSnapshot(snapshot: { schema_version?: unknown; runtime?: unknown; resources?: unknown[] }): {
  schema_version: unknown
  runtime: unknown
  resources: unknown[]
} {
  const resources = Array.isArray(snapshot.resources)
    ? snapshot.resources.map(resource => {
        if (!resource || typeof resource !== 'object') {
          return resource
        }

        const comparable = { ...(resource as Record<string, unknown>) }

        if (comparable.resource_type === 'browser') {
          comparable.updated_at = '<generated>'
        }

        return comparable
      })
    : []

  return {
    schema_version: snapshot.schema_version,
    runtime: snapshot.runtime,
    resources
  }
}

async function browserAction(taskId: string, sessionId: string, url: string): Promise<ControllerResponse> {
  return controllerRequest('/v1/action', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_navigate',
      arguments: { url },
      task_id: taskId,
      session_id: sessionId
    })
  })
}

async function nativeViewportSnapshot(app: MockBackendFixture['app']): Promise<NativeViewportSnapshot | null> {
  return app.evaluate(({ BrowserWindow }): NativeViewportSnapshot | null => {
    const allWindows = BrowserWindow.getAllWindows()
    const window = allWindows.find((w: { isDestroyed(): boolean; contentView: { children: unknown[] } }) => !w.isDestroyed() && w.contentView.children.length > 0) || allWindows[0]

    if (!window || window.isDestroyed()) {
      return null
    }

    const children = window?.contentView.children ?? []

    return {
      contentBounds: window.getContentBounds(),
      maximized: window.isMaximized(),
      children: children.flatMap((child: unknown) => {
        const view = child as unknown as {
          getBounds?: () => NativeViewportBounds
          webContents?: { id?: number; getURL?: () => string }
        }

        if (typeof view.getBounds !== 'function') {
          return []
        }

        return [
          {
            bounds: view.getBounds(),
            webContentsId: typeof view.webContents?.id === 'number' ? view.webContents.id : null,
            url: typeof view.webContents?.getURL === 'function' ? view.webContents.getURL() : ''
          }
        ]
      })
    }
  })
}

async function nativePageUrls(app: MockBackendFixture['app']): Promise<string[]> {
  return app.evaluate(({ webContents }) =>
    webContents
      .getAllWebContents()
      .filter((contents: any) => !contents.isDestroyed())
      .map((contents: any) => contents.getURL())
  )
}

async function openStoredSessionByTitle(
  page: MockBackendFixture['page'],
  title: string,
  expectedPrompt?: string
): Promise<void> {
  const row = page.locator('[data-slot="sidebar"] button').filter({ hasText: title }).first()
  await row.waitFor({ state: 'visible', timeout: 60_000 })
  await row.click()

  if (expectedPrompt) {
    await expect.poll(() => page.locator('body').textContent(), { timeout: 30_000 }).toContain(expectedPrompt)
  }
}

async function createRealChat(fixture: MockBackendFixture, prompt: string, expectedReply = 'boot chain is working', sessionMarker = prompt, existingSession?: { id: string; label: string }): Promise<{ id: string; label: string }> {
  if (!existingSession) {
    const newSession = fixture.page.locator('[data-slot="sidebar"] button').filter({ hasText: 'New session' }).first()
    await newSession.waitFor({ state: 'visible', timeout: 30_000 })
    await newSession.click()
  }

  const before = fixture.mock.receivedPrompts.length
  const assistantMessages = fixture.page.locator('[data-slot="aui_assistant-message-content"]')
  const assistantCount = await assistantMessages.count()
  const composer = fixture.page.locator('[contenteditable="true"]').first()
  await composer.click()
  await composer.fill(prompt)
  await fixture.page.keyboard.press('Enter')
  await expect.poll(() => fixture.mock.receivedPrompts.length, { timeout: 60_000 }).toBeGreaterThan(before)
  await expect.poll(() => assistantMessages.count(), { timeout: 60_000 }).toBeGreaterThan(assistantCount)
  await expect.poll(() => assistantMessages.last().textContent(), { timeout: 60_000 }).toContain(expectedReply)
  await expect.poll(() => fixture.page.locator('[data-slot="composer-root"] button[aria-label="Stop"]').count(), { timeout: 60_000 }).toBe(0)

  if (existingSession) {return existingSession}

  return expect
    .poll(
      async () =>
        fixture.page.evaluate(async expected => {
          const response = await (window as unknown as DesktopBridgeWindow).hermesDesktop.api<{
            sessions: Array<{ id: string; preview?: string | null; title?: string | null }>
          }>({ path: '/api/sessions?limit=50&offset=0&min_messages=1&archived=exclude&order=recent' })

          return response.sessions.find(session => session.preview?.includes(expected))?.id
        }, sessionMarker),
      { timeout: 60_000 }
    )
    .not.toBeUndefined()
    .then(async () =>
      fixture.page.evaluate(async expected => {
        const response = await (window as unknown as DesktopBridgeWindow).hermesDesktop.api<{
          sessions: Array<{ id: string; preview?: string | null; title?: string | null }>
        }>({ path: '/api/sessions?limit=50&offset=0&min_messages=1&archived=exclude&order=recent' })

        const session = response.sessions.find(row => row.preview?.includes(expected))

        if (!session) {throw new Error(`H013 real chat did not persist: ${expected}`)}

        return { id: session.id, label: session.title || session.preview || expected }
      }, sessionMarker)
    )
}

function activeViewportChildren(snapshot: NativeViewportSnapshot | null): NativeViewportChild[] {
  const content = snapshot?.contentBounds

  if (!content) {
    return []
  }

  return (snapshot?.children ?? []).filter(child => {
    return (
      child.bounds.x >= 0 &&
      child.bounds.y >= 0 &&
      child.bounds.width > 0 &&
      child.bounds.height > 0 &&
      child.bounds.x + child.bounds.width <= content.width &&
      child.bounds.y + child.bounds.height <= content.height
    )
  })
}

function activeViewportChild(snapshot: NativeViewportSnapshot | null): NativeViewportChild {
  const content = snapshot?.contentBounds

  const activeChildren = (snapshot?.children ?? []).filter(child => {
    if (!content) {
      return false
    }

    return (
      child.bounds.x >= 0 &&
      child.bounds.y >= 0 &&
      child.bounds.x + child.bounds.width <= content.width &&
      child.bounds.y + child.bounds.height <= content.height
    )
  })

  const viewport = activeChildren[0]

  // Parked BrowserTasks may remain attached at the compositor edge to keep
  // Chromium warm. Only one native view may occupy the actual content area.
  expect(activeChildren, `native viewport snapshot: ${JSON.stringify(snapshot)}`).toHaveLength(1)

  return activeChildren[0] as NativeViewportChild
}

function expectViewportWithinContent(snapshot: NativeViewportSnapshot | null): void {
  const viewport = activeViewportChild(snapshot)
  const content = snapshot?.contentBounds

  expect(viewport?.bounds.x).toBeGreaterThanOrEqual(0)
  expect(viewport?.bounds.y).toBeGreaterThanOrEqual(0)
  expect(viewport?.bounds.width).toBeGreaterThan(0)
  expect(viewport?.bounds.height).toBeGreaterThan(0)
  expect((viewport?.bounds.x ?? 0) + (viewport?.bounds.width ?? 0)).toBeLessThanOrEqual(content?.width ?? 0)
  expect((viewport?.bounds.y ?? 0) + (viewport?.bounds.height ?? 0)).toBeLessThanOrEqual(content?.height ?? 0)
}

test.beforeAll(async () => {
  // P1/OL-MVP: the readiness wait below takes up to 120s. Playwright's
  // default 90s hook limit previously killed the diagnostic prematurely.
  // This is a bounded test-only limit; it does NOT change production boot.
  test.setTimeout(160_000)
  let phase = 'start'

  try {
    phase = 'fixture-http'
    await startDeterministicPageServer()
    phase = 'mock-backend-and-electron'
    fixture = await setupMockBackend({ headless: true })
    phase = 'renderer-and-backend-ready'
    await waitForAppReady(fixture, 120_000, false)

    phase = 'native-controller-file'
    const controlPath = path.join(fixture.sandbox.root, 'workstation', 'Runtime', 'browser-control.json')
    await expect.poll(() => fs.existsSync(controlPath), { timeout: 25_000 }).toBe(true)
    controller = await readControllerFile(controlPath)

    phase = 'native-controller-health'
    expect(controller.runtime).toBe('electron-chromium')
    const health = await controllerRequest('/health')
    expect(health.runtime).toBe('electron-chromium')
  } catch (error) {
    // Only test-created mock data. No credentials, user session or DOM dump.
    // Keep the actual stack; readiness failures are NOT compiler failures.
    const status = fixture
      ? await fixture.page.locator('body').innerText({ timeout: 2_000 })
          .then(text => {
        if (/Reconnecting to Hermes/i.test(text)) {
          return 'reconnecting'
        }

        if (/Waking up/i.test(text)) {
          return 'waking-up'
        }

        if (/Preparing/i.test(text)) {
          return 'preparing'
        }

            return 'other-renderer-state'
          })
          .catch(() => 'renderer-inaccessible')
      : 'electron-not-launched'

    console.error('[P1/OL-MVP] Electron native smoke blocked', {
      phase,
      status,
      reason: error instanceof Error ? error.message : String(error)
    })
    throw error
  }
})

test.afterAll(async () => {
  const reportPath = process.env.HERMES_DESKTOP_E2E_REPORT?.trim()

  if (reportPath && sustainedLoadEvidence) {
    await fs.promises.mkdir(path.dirname(reportPath), { recursive: true })
    await fs.promises.writeFile(reportPath, `${JSON.stringify(sustainedLoadEvidence, null, 2)}\n`, 'utf8')
  }

  await fixture?.cleanup()
  fixture = null
  controller = null

  await new Promise<void>(resolve => {
    if (!pageServer) {
      resolve()

      return
    }

    pageServer.close(() => resolve())
  })
  pageServer = null
})

function parseCallResultJson(raw: string | null): Record<string, any> | null {
  if (!raw) {return null}
  const marker = 'E2E_CALL_RESULT:'
  const markerIndex = raw.lastIndexOf(marker)

  if (markerIndex < 0) {return null}
  const start = raw.indexOf('{', markerIndex + marker.length)

  if (start < 0) {return null}
  let depth = 0
  let inString = false
  let escaped = false

  for (let position = start; position < raw.length; position++) {
    const ch = raw[position]

    if (inString) {
      if (escaped) {escaped = false}
      else if (ch === '\\') {escaped = true}
      else if (ch === '"') {inString = false}
    } else if (ch === '"') {inString = true}
    else if (ch === '{') {depth++}
    else if (ch === '}') {
      depth--

      if (depth === 0) {
        try { return JSON.parse(raw.slice(start, position + 1)) }
        catch { return null }
      }
    }
  }

  return null
}

function collectArtifactFiles(root: string, unresolved: string[]): Array<{ path: string; value: any }> {
  const artifacts: Array<{ path: string; value: any }> = []

  try {
    const pending = [root]

    while (pending.length) {
      const directory = pending.pop()!

      for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        const file = path.join(directory, entry.name)

        if (entry.isDirectory()) {pending.push(file)}
        else if (entry.isFile() && entry.name.endsWith('.json')) {
          try { artifacts.push({ path: path.relative(root, file), value: JSON.parse(fs.readFileSync(file, 'utf8')) }) }
          catch (error) { unresolved.push(`${path.relative(root, file)}: ${String(error)}`) }
        }
      }
    }
  } catch (error) { unresolved.push(String(error)) }

  return artifacts
}

function extractP2LearningEvidence(attempts: Array<Record<string, any>>): {
  learningCheckpoints: any[]
  candidateCapabilities: any[]
  compilerAdoption: string
} {
  const learningCheckpoints = attempts.flatMap(a => (a.artifacts || []).filter((art: any) => art.value?.schema === 'workstation.run_learning_checkpoint.v1'))
  const candidateCapabilities = attempts.flatMap(a => (a.artifacts || []).filter((art: any) => typeof art.path === 'string' && art.path.includes('operational_capabilities') && !art.path.endsWith('.meta.json')))
  const compilerAdoption = candidateCapabilities.length > 0 ? 'candidates_compiled_shadow' : 'not_demonstrated'

  return { learningCheckpoints, candidateCapabilities, compilerAdoption }
}

test('OL-MVP P2: two real chat work_execute batches require canonical owner evidence', async () => {
  test.setTimeout(240_000)

  if (!fixture) {
    throw new Error('Fixture not initialized')
  }

  const activeFixture = fixture
  const url = `${pageBaseUrl}${OL_MVP_READONLY_PATH}`
  const attempts: Array<Record<string, any>> = []
  const artifactRoot = path.join(activeFixture.sandbox.hermesHome, 'workstation', 'artifacts')

  for (const [index, cards] of [OL_MVP_READONLY_CARDS, [...OL_MVP_READONLY_CARDS].reverse()].entries()) {
    const marker = `OLP2-${Date.now()}-${index}`

    const request = {
      operation_key: 'ol-mvp-p2-readonly-cards', kind: 'batch', title: 'Read three cards without mutation', verbosity: 'full',
      items: cards.map(card => ({ card_id: card.id, selector: index === 0 ? `article[data-card-id="${card.id}"]` : `article[data-testid="ol-mvp-card"][data-card-id="${card.id}"]` })),
      steps: [
        { id: 'extract', tool: 'browser_extract_items', args: { mode: 'inspect', selector: '$item.selector', limit: 1, attributes: ['data-card-id', 'data-list'], output_artifact: false }, expect: { success: true } }
      ]
    }

    const attempt: Record<string, any> = { marker, request, session: null, result: null, raw: null, product_failure: null, inspection_unresolved: [] }
    attempts.push(attempt)

    try {
      attempt.preparation = { request: { url }, raw: null, error: null }

      try {
        attempt.session = await createRealChat(activeFixture, `${marker} E2E_CALL(browser_navigate)[${JSON.stringify({ url })}]`, 'E2E_CALL_RESULT:', marker)
        attempt.preparation.raw = await activeFixture.page.locator('[data-slot="aui_assistant-message-content"]').last().textContent()
      } catch (error) {
        attempt.preparation.error = String(error)
        throw error
      }

      attempt.session = await createRealChat(activeFixture, `${marker} Execute this multistep workflow to read 3 cards without mutating them. E2E_CALL(work_execute)[${JSON.stringify(request)}]`, 'E2E_CALL_RESULT:', marker, attempt.session)
      await expect.poll(async () => {
        attempt.raw = await activeFixture.page.locator('[data-slot="aui_assistant-message-content"]').last().textContent()
        const parsed = parseCallResultJson(attempt.raw)

        if (parsed) {
          attempt.result = parsed

          return true
        }

        return false
      }, { timeout: 60_000 }).toBe(true)
    } catch (error) {
      attempt.product_failure = String(error)
      attempt.raw = await activeFixture.page.locator('body').textContent().catch(() => null)
    } finally {
      attempt.tables = {}
      let db: DatabaseSync | undefined

      try {
        db = new DatabaseSync(path.join(activeFixture.sandbox.hermesHome, 'kanban.db'), { readOnly: true })

        for (const table of ['tasks', 'task_runs', 'work_plans', 'work_items']) {
          try { attempt.tables[table] = db.prepare(`SELECT * FROM ${table}`).all() }
          catch (error) { attempt.inspection_unresolved.push(`${table}: ${String(error)}`) }
        }
      } catch (error) { attempt.inspection_unresolved.push(String(error)) }
      finally { db?.close() }

      attempt.artifacts = collectArtifactFiles(artifactRoot, attempt.inspection_unresolved)
      const tasks = (attempt.tables.tasks || []).filter((row: any) => row.session_id === attempt.session?.id)
      attempt.canonical_runs = (attempt.tables.task_runs || []).filter((run: any) => tasks.some((task: any) => task.id === run.task_id)).map((run: any) => {
        const plans = (attempt.tables.work_plans || []).filter((plan: any) => {
          try {
            const metadata = typeof plan.metadata === 'string' ? JSON.parse(plan.metadata) : plan.metadata

            return metadata?.canonical_task_id === run.task_id && String(metadata?.canonical_run_id) === String(run.id)
          } catch { return false }
        })

        const items = (attempt.tables.work_items || []).filter((item: any) => plans.some((plan: any) => plan.id === item.plan_id))
        const readbacks = attempt.artifacts.filter((artifact: any) => artifact.value?.schema === 'hermes.browser_card_readback.v1' && artifact.value.task_id === run.task_id && String(artifact.value.run_id) === String(run.id))

        return { run, plans, items, readbacks }
      })
    }
  }

  const observation: Record<string, any> = { viewport: null, cards: null, error: null }

  try {
    observation.viewport = await nativeViewportSnapshot(activeFixture.app)
    const children: any[] = []

    const collect = (value: any): void => {
      if (!value || typeof value !== 'object') {return}

      if (value.url === url) {children.push(value)}

      for (const child of Object.values(value)) {collect(child)}
    }

    collect(observation.viewport)
    const child = children.find(value => typeof (value.webContentsId ?? value.id) === 'number')

    if (!child) {throw new Error('P2: requested native viewport is absent')}
    observation.cards = await activeFixture.app.evaluate(({ webContents }, id) => {
      const contents = webContents.fromId(id)

      if (!contents) {throw new Error('P2: native viewport webContents missing')}

      return contents.executeJavaScript(`Array.from(document.querySelectorAll('article[data-testid="ol-mvp-card"]')).map(card => ({id:card.getAttribute('data-card-id'),list:card.getAttribute('data-list'),title:card.querySelector('h2')?.textContent,description:card.querySelector('p')?.textContent}))`)
    }, child.webContentsId ?? child.id)
  } catch (error) { observation.error = String(error) }

  const { learningCheckpoints, candidateCapabilities, compilerAdoption } = extractP2LearningEvidence(attempts)
  const evidence = { schema: 'hermes.ol_mvp_p2_native_probe.v1', scripted_provider: true, mode: 'SHADOW', compiler_adoption: compilerAdoption, learning_checkpoints: learningCheckpoints.map(c => c.value), candidate_capabilities: candidateCapabilities.map(c => ({ id: c.value?.id, version: c.value?.version, lifecycle: c.value?.lifecycle, family_id: c.value?.family_id })), attempts, observation, real_llm_calls: null, tokens: null, economics: null }
  const evidencePath = test.info().outputPath('ol-mvp-p2-native-chat-work-execute-evidence.json')
  fs.writeFileSync(evidencePath, JSON.stringify(evidence, null, 2))
  await test.info().attach('ol-mvp-p2-native-chat-work-execute-evidence', { path: evidencePath, contentType: 'application/json' })
  expect(candidateCapabilities.length).toBeGreaterThan(0)
  expect(learningCheckpoints.length).toBeGreaterThan(0)
  const runIds: string[] = []

  for (const attempt of attempts) {
    expect(attempt.product_failure).toBeNull()
    expect(attempt.session?.id).toBeTruthy()
    expect(attempt.result?.status).toBe('completed')
    expect(attempt.result?.completed).toBe(3)
    expect(attempt.result?.total).toBe(3)
    expect(attempt.result?.needs_reasoning).toBe(0)
    expect(attempt.canonical_runs).toHaveLength(1)
    const canonical = attempt.canonical_runs[0]
    runIds.push(canonical.run.id)
    expect(canonical.plans.length).toBeGreaterThan(0)
    expect(canonical.items).toHaveLength(3)

    for (const item of canonical.items) {expect(['completed', 'done']).toContain(item.status)}
    expect(canonical.readbacks.length).toBeGreaterThan(0)

    for (const artifact of canonical.readbacks) {
      for (const field of ['operation_id', 'raw_result_ref', 'transition_ref', 'browser_task_id']) {expect(artifact.value[field]).toBeTruthy()}

      for (const field of ['raw_result_ref', 'transition_ref']) {
        const reference = artifact.value[field]
        expect(attempt.artifacts.some((candidate: any) =>
          candidate.path === reference ||
          candidate.value?.artifact_id === reference ||
          candidate.value?.id === reference ||
          candidate.value?.ref === reference ||
          `artifact://tasks/${candidate.path.replace(/\\/g, '/')}` === reference
        )).toBe(true)
      }
    }

    const output = JSON.stringify(attempt.result)

    for (const card of OL_MVP_READONLY_CARDS) {
      for (const field of [card.id, card.title, card.list, card.description]) {expect(output).toContain(field)}
    }
  }

  expect(new Set(runIds).size).toBe(2)
  expect(observation.error).toBeNull()
  expect(observation.cards).toEqual(OL_MVP_READONLY_CARDS)
})

test('OL-MVP P1: reads three isolated cards through native BrowserTask without mutation', async () => {
  // Gate P1.0: real Chromium/HTTP live DOM, still NOT a compiler-adoption proof.
  if (!fixture || !controller) {
    throw new Error('P1: native controller not initialized')
  }

  const taskId = 'ol-mvp-p1-readonly-task'
  const sessionId = 'ol-mvp-p1-readonly-session'
  const url = `${pageBaseUrl}${OL_MVP_READONLY_PATH}`
  const navigation = await browserAction(taskId, sessionId, url)
  expect(navigation.success).toBe(true)
  expect(navigation.result?.url).toBe(url)
  expect(navigation.result?.title).toBe(OL_MVP_READONLY_TITLE)

  interface ExtractedCard {
    text: string
    tag: string
    attributes: Record<string, string | null>
  }
  interface NativeExtraction {
    count: number
    items: ExtractedCard[]
    runtime: string
    url: string
    title: string
  }

  const extractionArguments = {
    mode: 'inspect',
    selector: 'article[data-testid="ol-mvp-card"]',
    limit: 3,
    attributes: ['data-card-id', 'data-list'],
    output_artifact: false,
  }

  const extraction = await controllerRequest('/v1/action', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_extract_items',
      arguments: extractionArguments,
      task_id: taskId,
      session_id: sessionId,
    }),
  })

  expect(extraction.success).toBe(true)
  const extracted = extraction.result as NativeExtraction | undefined
  expect(extracted?.runtime).toBe('electron-chromium')
  expect(extracted?.url).toBe(url)
  expect(extracted?.title).toBe(OL_MVP_READONLY_TITLE)
  expect(extracted?.count).toBe(3)
  expect(Array.isArray(extracted?.items)).toBe(true)
  const extractedItems = extracted?.items ?? []
  expect(extractedItems).toHaveLength(3)

  for (const card of OL_MVP_READONLY_CARDS) {
    const item = extractedItems.find((candidate) => candidate.attributes['data-card-id'] === card.id)
    expect(item, `Native extraction missing card ${card.id}`).toBeDefined()
    expect(item?.attributes['data-list']).toBe(card.list)
    expect(item?.text).toContain(card.title)
    expect(item?.text).toContain(card.description)
  }

  const snapshot = await controllerRequest('/v1/action', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_snapshot',
      arguments: { full: true },
      task_id: taskId,
      session_id: sessionId
    })
  })

  expect(snapshot.success).toBe(true)
  expect(snapshot.result?.url).toBe(url)
  // Fail explicitly if the controller only supplies URL/title and does NOT
  // expose live card text; the implementer must then use an authorized typed
  // DOM-read action, never an opaque browser_console macro.
  const observed = JSON.stringify(snapshot.result ?? {})

  for (const card of OL_MVP_READONLY_CARDS) {
    expect(observed, `Native snapshot missing live DOM text for ${card.id}`).toContain(card.title)
    expect(observed, `Native snapshot missing live DOM description for ${card.id}`).toContain(card.description)
  }

  const nativeState = await nativeViewportSnapshot(fixture.app)

  if (!nativeState) {
    throw new Error('P1: native viewport state unavailable')
  }

  const matchingChildren = nativeState.children.filter((candidate) => candidate.url === url)
  expect(matchingChildren).toHaveLength(1)
  const child = matchingChildren[0]

  if (!child) {
    throw new Error('P1: native fixture webContents unavailable')
  }

  expect(child.url).toBe(url)
  const webContentsId = child.webContentsId

  if (webContentsId === null) {
    throw new Error('P1: native Browser webContents id unavailable')
  }

  const liveCards = await fixture.app.evaluate(({ webContents }, id) => {
    const contents = webContents.fromId(id)

    if (!contents) {
      throw new Error('P1: native viewport webContents missing')
    }

    return contents.executeJavaScript(`Array.from(document.querySelectorAll('article[data-testid="ol-mvp-card"]')).map(card => ({
      id: card.getAttribute('data-card-id'),
      list: card.getAttribute('data-list'),
      title: card.querySelector('h2')?.textContent,
      description: card.querySelector('p')?.textContent,
    }))`)
  }, webContentsId)

  expect(liveCards).toEqual(OL_MVP_READONLY_CARDS)

  await test.info().attach('ol-mvp-p1-native-readonly-evidence', {
    body: Buffer.from(JSON.stringify({
      native: true,
      live_dom: true,
      verified_card_count: 3,
      verified_fields: ['id', 'list', 'title', 'description'],
      operation: { action: 'browser_extract_items', arguments: extractionArguments },
      browser_task: { task_id: taskId, session_id: sessionId },
      extraction: extracted,
      independent_dom_readback: liveCards,
      snapshot_verified: true,
      real_llm_calls: null,
      real_llm_tokens: null,
      compiled_calls: null,
      learning_cost_usd: null,
      gross_savings_usd: null,
      net_savings_usd: null,
      compiler_adoption: 'not_demonstrated',
    }, null, 2)),
    contentType: 'application/json',
  })
})

test('keeps four native Browser tasks aligned across controller and IPC while headless', async () => {
  if (!fixture || !controller) {
    throw new Error('H013 fixture was not initialized')
  }

  const tasks = Array.from({ length: TASK_COUNT }, (_, index) => ({
    taskId: `h013-task-${index}`,
    sessionId: `h013-session-${index}`,
    url: `${pageBaseUrl}/h013-task-${index}`
  }))

  const navigations = await Promise.all(tasks.map(task => browserAction(task.taskId, task.sessionId, task.url)))

  expect(navigations).toHaveLength(TASK_COUNT)

  for (const [index, navigation] of navigations.entries()) {
    expect(navigation.result?.url).toBe(tasks[index].url)
    expect(navigation.result?.title).toBe(`H013 ${tasks[index].taskId}`)
  }

  for (const task of tasks) {
    const snapshot = await controllerRequest('/v1/action', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        action: 'browser_snapshot',
        arguments: { full: false },
        task_id: task.taskId,
        session_id: task.sessionId
      })
    })

    expect(snapshot.result?.url).toBe(task.url)
    expect(snapshot.result?.title).toBe(`H013 ${task.taskId}`)
  }

  const controllerResources = await controllerRequest('/resources')

  const taskResources = (controllerResources.resources ?? []).filter(
    resource => resource.resource_type === 'browser_task'
  )

  const taskResourceIds = new Set(taskResources.map(resource => resource.task_id))

  expect(controllerResources.runtime).toBe('electron-chromium')
  expect(taskResources).toHaveLength(TASK_COUNT)
  expect(taskResourceIds).toEqual(new Set(tasks.map(task => task.taskId)))

  const controllerEvents = await controllerRequest('/events?limit=100')

  for (const resource of taskResources) {
    expect(resource.session_id).toBe(`h013-session-${String(resource.task_id).replace('h013-task-', '')}`)
    expect((resource.state as { tab_id?: string }).tab_id).toEqual(expect.any(String))
    expect((resource.state as { evidence?: string[] }).evidence).toEqual(
      expect.arrayContaining(['browser://controller'])
    )
  }

  const ipcSnapshot = await fixture.page.evaluate(async () => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop?.workstationBrowser

    if (!api) {
      throw new Error('H013 renderer IPC bridge is unavailable')
    }

    return {
      resources: await api.resources(),
      events: await api.events(null, 100),
      tasks: await api.listTasks()
    }
  })

  expect(ipcSnapshot.resources.runtime).toBe(controllerResources.runtime)
  expect(comparableResourceSnapshot(ipcSnapshot.resources)).toEqual(comparableResourceSnapshot(controllerResources))

  const resourceIdentity = (snapshot: { resources?: Array<Record<string, unknown>> }) =>
    (snapshot.resources ?? []).map(resource => [
      resource.resource_type,
      resource.resource_id,
      resource.task_id,
      resource.session_id
    ])

  expect(resourceIdentity(ipcSnapshot.resources)).toEqual(resourceIdentity(controllerResources))
  expect(ipcSnapshot.events.runtime).toBe('electron-chromium')
  expect(ipcSnapshot.events.task_id).toBe(controllerEvents.task_id)
  expect(ipcSnapshot.events.events).toEqual(controllerEvents.events)
  expect(ipcSnapshot.tasks).toHaveLength(TASK_COUNT)
  expect(ipcSnapshot.events.events).toEqual(expect.any(Array))

  const hubBounds = { x: 12, y: 18, width: 720, height: 520 }
  const chatBounds = { x: 300, y: 22, width: 500, height: 480 }

  const attached = await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.attach(bounds, 'hub')
  }, hubBounds)

  expect(attached.viewportHost).toBe('hub')
  // The renderer's ResizeObserver may publish its first layout immediately after
  // attach. Reassert the owning host's requested bounds after that projection and
  // wait for the native child to converge before evaluating the invariant.
  await fixture.page.waitForTimeout(100)
  await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.setBounds(bounds, 'hub')
  }, hubBounds)
  await expect.poll(async () => {
    const snapshot = await nativeViewportSnapshot(fixture!.app)

    return activeViewportChild(snapshot).bounds
  }).toEqual(hubBounds)
  const initialNativeViewport = await nativeViewportSnapshot(fixture.app)
  const initialNativeChild = activeViewportChild(initialNativeViewport)
  expect(initialNativeChild.bounds).toEqual(hubBounds)
  const initialNativeChildId = initialNativeChild.webContentsId

  const stale = await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.setBounds(bounds, 'chat')
  }, chatBounds)

  expect(stale.viewportHost).toBe('hub')
  const staleNativeViewport = await nativeViewportSnapshot(fixture.app)
  const staleNativeChild = activeViewportChild(staleNativeViewport)
  expect(staleNativeChild.webContentsId).toBe(initialNativeChildId)
  expect(staleNativeChild.bounds).toEqual(initialNativeChild.bounds)

  const resized = await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.setBounds(bounds, 'hub')
  }, chatBounds)

  expect(resized.viewportHost).toBe('hub')
  const resizedNativeViewport = await nativeViewportSnapshot(fixture.app)
  const resizedNativeChild = activeViewportChild(resizedNativeViewport)
  expect(resizedNativeChild.webContentsId).toBe(initialNativeChildId)
  expect(resizedNativeChild.bounds).toEqual(chatBounds)

  const transferred = await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.transferViewport('chat', bounds)
  }, chatBounds)

  expect(transferred.viewportHost).toBe('chat')
  const transferredNativeViewport = await nativeViewportSnapshot(fixture.app)
  const transferredNativeChild = activeViewportChild(transferredNativeViewport)
  expect(transferredNativeChild.webContentsId).toBe(initialNativeChildId)
  expect(transferredNativeChild.bounds).toEqual({
    x: expect.any(Number),
    y: expect.any(Number),
    width: expect.any(Number),
    height: expect.any(Number)
  })

  const restoredWindowViewport = await nativeViewportSnapshot(fixture.app)
  expect(restoredWindowViewport?.maximized).toBe(false)
  expectViewportWithinContent(restoredWindowViewport)

  const maximized = await fixture.app.evaluate(({ BrowserWindow }): boolean => {
    const window = BrowserWindow.getAllWindows()[0]

    if (!window || window.isDestroyed()) {
      throw new Error('H013 BrowserWindow disappeared before maximize')
    }

    window.maximize()
    const maximized = window.isMaximized()
    // Windows may reveal a hidden BrowserWindow as a side effect of native
    // maximize. Immediately re-hide it so this E2E never paints a desktop
    // surface while still exercising the real maximize transition.
    window.hide()

    return maximized
  })

  expect(maximized).toBe(true)
  await fixture.page.waitForTimeout(250)

  const maximizedViewport = await nativeViewportSnapshot(fixture.app)
  expect(maximizedViewport?.maximized).toBe(true)
  expect(activeViewportChild(maximizedViewport).webContentsId).toBe(initialNativeChildId)
  expectViewportWithinContent(maximizedViewport)

  const restored = await fixture.app.evaluate(({ BrowserWindow }): boolean => {
    const window = BrowserWindow.getAllWindows()[0]

    if (!window || window.isDestroyed()) {
      throw new Error('H013 BrowserWindow disappeared before restore')
    }

    window.unmaximize()
    const restored = window.isMaximized()
    window.hide()

    return restored
  })

  expect(restored).toBe(false)
  await fixture.page.waitForTimeout(250)

  const afterRestoreViewport = await nativeViewportSnapshot(fixture.app)
  expect(afterRestoreViewport?.maximized).toBe(false)
  expect(activeViewportChild(afterRestoreViewport).webContentsId).toBe(initialNativeChildId)
  expectViewportWithinContent(afterRestoreViewport)

  const hiddenWindows = await fixture.app.evaluate(({ BrowserWindow }): boolean[] =>
    BrowserWindow.getAllWindows().map((window: { isVisible: () => boolean }) => window.isVisible())
  )

  expect(hiddenWindows.length).toBeGreaterThan(0)
  expect(hiddenWindows.every(visible => visible === false)).toBe(true)

  await fixture.page.evaluate(async taskId => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser
    await api.hideTask(taskId)
    await api.parkTask(taskId)
  }, tasks[0].taskId)

  const parkedTasks = await fixture.page.evaluate(() =>
    (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.listTasks()
  )

  const parkedTask = parkedTasks.find(task => task.taskId === 'h013-task-0')

  expect(parkedTask?.status).toBe('parked')
  expect(parkedTask?.parked).toBe(true)

  for (const task of tasks) {
    await fixture.page.evaluate(
      taskId => (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.destroyTask(taskId),
      task.taskId
    )
  }

  const finalTasks = await fixture.page.evaluate(() =>
    (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.listTasks()
  )

  expect(finalTasks).toHaveLength(0)
})

test('sustains concurrent BrowserTasks and real backend chat turns while headless', async () => {
  test.setTimeout(Math.max(90_000, SUSTAINED_DURATION_MS + 60_000))

  if (!fixture || !controller) {
    throw new Error('H013 fixture was not initialized')
  }

  const hubBounds = { x: 12, y: 18, width: 720, height: 520 }
  const chatBounds = { x: 300, y: 22, width: 500, height: 480 }

  const tasks = Array.from({ length: SUSTAINED_TASK_COUNT }, (_, index) => ({
    taskId: `h013-sustained-task-${index}`,
    sessionId: `h013-sustained-session-${index}`
  }))

  const attached = await fixture.page.evaluate(async bounds => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return api.attach(bounds, 'hub')
  }, hubBounds)

  expect(attached.viewportHost).toBe('hub')

  const startedAt = Date.now()
  let completedRounds = 0

  for (let round = 0; round < SUSTAINED_ROUNDS; round += 1) {
    if (round > 0 && SUSTAINED_DURATION_MS > 0 && Date.now() - startedAt >= SUSTAINED_DURATION_MS) {
      break
    }

    const navigations = await Promise.all(
      tasks.map(task =>
        browserAction(task.taskId, task.sessionId, `${pageBaseUrl}/sustained-round-${round}/${task.taskId}`)
      )
    )

    expect(navigations).toHaveLength(SUSTAINED_TASK_COUNT)

    for (const [index, navigation] of navigations.entries()) {
      expect(navigation.result?.url).toBe(`${pageBaseUrl}/sustained-round-${round}/${tasks[index].taskId}`)
      expect(navigation.result?.title).toBe(`H013 sustained-round-${round}/${tasks[index].taskId}`)
    }

    const snapshots = await Promise.all(
      tasks.map(task =>
        controllerRequest('/v1/action', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            action: 'browser_snapshot',
            arguments: { full: false },
            task_id: task.taskId,
            session_id: task.sessionId
          })
        })
      )
    )

    expect(snapshots).toHaveLength(SUSTAINED_TASK_COUNT)

    for (const [index, snapshot] of snapshots.entries()) {
      expect(snapshot.result?.url).toBe(`${pageBaseUrl}/sustained-round-${round}/${tasks[index].taskId}`)
      expect(snapshot.result?.title).toBe(`H013 sustained-round-${round}/${tasks[index].taskId}`)
    }

    const shownTask = tasks[round % tasks.length]

    const shown = await fixture.page.evaluate(
      async ({ bounds, taskId, host }) => {
        const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

        return api.showTask(taskId, bounds, host)
      },
      {
        bounds: round % 2 === 0 ? hubBounds : chatBounds,
        taskId: shownTask.taskId,
        host: round % 2 === 0 ? 'hub' : 'chat'
      }
    )

    expect(shown.taskId).toBe(shownTask.taskId)
    expect(shown.status).toBe('visible')
    expectViewportWithinContent(await nativeViewportSnapshot(fixture.app))
    completedRounds += 1
  }

  expect(completedRounds).toBeGreaterThan(0)
  const observedDurationMs = Date.now() - startedAt

  const controllerResources = await controllerRequest('/resources')
  const controllerEvents = await controllerRequest('/events?limit=200')

  const taskResources = (controllerResources.resources ?? []).filter(
    resource => resource.resource_type === 'browser_task'
  )

  expect(taskResources).toHaveLength(SUSTAINED_TASK_COUNT)
  expect(new Set(taskResources.map(resource => resource.task_id))).toEqual(new Set(tasks.map(task => task.taskId)))

  const chatTurns = Math.min(SUSTAINED_CHAT_TURNS, completedRounds)

  for (let turn = 0; turn < chatTurns; turn += 1) {
    const prompt = `H013 sustained backend turn ${turn}`
    const before = fixture.mock.receivedPrompts.length
    const composer = fixture.page.locator('[contenteditable="true"]').first()

    await composer.click()
    await composer.type(prompt)
    await fixture.page.keyboard.press('Enter')
    await expect.poll(() => fixture?.mock.receivedPrompts.length ?? 0, { timeout: 60_000 }).toBeGreaterThan(before)
    await expect
      .poll(() => fixture?.page.locator('body').textContent() ?? '', { timeout: 60_000 })
      .toContain('boot chain is working')
  }

  const ipcSnapshot = await fixture.page.evaluate(async () => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

    return {
      resources: await api.resources(),
      events: await api.events(null, 200),
      tasks: await api.listTasks()
    }
  })

  const ipcTaskResources = ipcSnapshot.resources.resources.filter(resource => resource.resource_type === 'browser_task')
  expect(comparableResourceSnapshot(ipcSnapshot.resources)).toEqual(comparableResourceSnapshot(controllerResources))
  expect(ipcSnapshot.resources.resources.length).toBeGreaterThan(SUSTAINED_TASK_COUNT)
  expect(ipcTaskResources).toHaveLength(SUSTAINED_TASK_COUNT)
  expect(new Set(ipcTaskResources.map(resource => resource.task_id))).toEqual(new Set(tasks.map(task => task.taskId)))
  expect(ipcSnapshot.events.task_id).toBe(controllerEvents.task_id)
  expect(ipcSnapshot.events.events).toEqual(controllerEvents.events)
  expect(ipcSnapshot.events.events).toEqual(expect.any(Array))
  expect(ipcSnapshot.tasks).toHaveLength(SUSTAINED_TASK_COUNT)

  for (const task of tasks) {
    await fixture.page.evaluate(async taskId => {
      const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser
      await api.hideTask(taskId)
      await api.parkTask(taskId)
      await api.destroyTask(taskId)
    }, task.taskId)
  }

  const finalTasks = await fixture.page.evaluate(() =>
    (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.listTasks()
  )

  expect(finalTasks).toHaveLength(0)

  sustainedLoadEvidence = {
    accepted: true,
    task_count: SUSTAINED_TASK_COUNT,
    requested_rounds: SUSTAINED_ROUNDS,
    completed_rounds: completedRounds,
    requested_duration_ms: SUSTAINED_DURATION_MS,
    observed_duration_ms: observedDurationMs,
    chat_turns: chatTurns
  }
})

test('restores the selected chat BrowserTask on the first real viewport attach without foreground theft', async () => {
  test.setTimeout(180_000)

  if (!fixture) {
    throw new Error('H013 fixture was not initialized')
  }

  // Create two chats through the real renderer/gateway, then run two Electron
  // processes against the same BrowserSessionState and user-data.
  const sessionA = await createRealChat(fixture, 'H013 restart Chat A')
  const sessionB = await createRealChat(fixture, 'H013 restart Chat B')
  const env = buildAppEnv(fixture.sandbox, { HERMES_DESKTOP_E2E_HEADLESS: '1' })
  const controlPath = path.join(fixture.sandbox.root, 'workstation', 'Runtime', 'browser-control.json')

  const urlA = `${pageBaseUrl}/restart-a`
  const urlAWorking = `${pageBaseUrl}/restart-a-working`
  const urlB = `${pageBaseUrl}/restart-b`

  await openStoredSessionByTitle(fixture.page, sessionA.label, 'H013 restart Chat A')
  await browserAction('h013-restart-task-a', sessionA.id, urlA)
  await expect.poll(async () => activeViewportChild(await nativeViewportSnapshot(fixture!.app)).url).toBe(urlA)

  await openStoredSessionByTitle(fixture.page, sessionB.label, 'H013 restart Chat B')
  await browserAction('h013-restart-task-b', sessionB.id, urlB)
  await expect.poll(async () => activeViewportChild(await nativeViewportSnapshot(fixture!.app)).url).toBe(urlB)

  // A runs through the authenticated controller while B owns the viewport.
  await browserAction('h013-restart-task-a', sessionA.id, urlAWorking)
  expect(activeViewportChild(await nativeViewportSnapshot(fixture.app)).url).toBe(urlB)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlAWorking)).toHaveLength(1)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlB)).toHaveLength(1)

  const firstControllerToken = controller?.token
  await fixture.app.close()
  const second = await launchDesktop(env)
  fixture.app = second.app
  fixture.page = second.page
  await waitForAppReady(fixture, 120_000, false)
  await expect
    .poll(async () => (await readControllerFile(controlPath)).token, { timeout: 30_000 })
    .not.toBe(firstControllerToken)
  controller = await readControllerFile(controlPath)

  // Chat B and its persisted preview are restored by the real renderer. Its
  // first visible native child must already be B; A remains lazy.
  await openStoredSessionByTitle(fixture.page, sessionB.label, 'H013 restart Chat B')
  await expect.poll(async () => activeViewportChild(await nativeViewportSnapshot(fixture!.app)).url).toBe(urlB)
  expect(activeViewportChild(await nativeViewportSnapshot(fixture.app)).url).not.toBe('about:blank')
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlB)).toHaveLength(1)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlAWorking)).toHaveLength(0)

  await openStoredSessionByTitle(fixture.page, sessionA.label, 'H013 restart Chat A')
  await expect.poll(async () => activeViewportChild(await nativeViewportSnapshot(fixture!.app)).url).toBe(urlAWorking)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlAWorking)).toHaveLength(1)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlB)).toHaveLength(1)

  await openStoredSessionByTitle(fixture.page, sessionB.label, 'H013 restart Chat B')
  await expect.poll(async () => activeViewportChild(await nativeViewportSnapshot(fixture!.app)).url).toBe(urlB)
  expect((await nativePageUrls(fixture.app)).filter(url => url === urlB)).toHaveLength(1)

  const bounds = { x: 12, y: 18, width: 720, height: 520 }

  const hubAfterStaleChat = await fixture.page.evaluate(async ({ bounds, taskId }) => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser
    await api.attach(bounds, 'hub', taskId)
    await api.detach('chat')

    return api.setVisible(false, 'chat')
  }, { bounds, taskId: 'h013-restart-task-b' })

  expect(hubAfterStaleChat.viewportHost).toBe('hub')
  expect(hubAfterStaleChat.attached).toBe(true)

  const chatAfterStaleHub = await fixture.page.evaluate(async ({ bounds, taskId }) => {
    const api = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser
    await api.attach(bounds, 'chat', taskId)
    await api.detach('hub')

    return api.setVisible(false, 'hub')
  }, { bounds, taskId: 'h013-restart-task-b' })

  expect(chatAfterStaleHub.viewportHost).toBe('chat')
  expect(chatAfterStaleHub.attached).toBe(true)
  expect(activeViewportChild(await nativeViewportSnapshot(fixture.app)).url).toBe(urlB)

  for (const taskId of ['h013-restart-task-a', 'h013-restart-task-b']) {
    await fixture.page.evaluate(
      id => (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.destroyTask(id),
      taskId
    )
  }
})


test('P0: native two-session human takeover denies writes with 409 then safely resumes', async () => {
  if (!fixture || !controller) {
    throw new Error('P0 native authority fixture is not ready')
  }

  // This test runs in a fresh isolated HERMES_HOME with real Electron
  // WebContentsViews, controller HTTP, renderer IPC, and loopback pages.
  const a = { taskId: 'p0-native-a', sessionId: 'p0-session-a' }
  const b = { taskId: 'p0-native-b', sessionId: 'p0-session-b' }
  const first = await browserAction(a.taskId, a.sessionId, `${pageBaseUrl}/p0-native-a`)
  const second = await browserAction(b.taskId, b.sessionId, `${pageBaseUrl}/p0-native-b`)
  expect(first.result?.title).toBe('H013 p0-native-a')
  expect(second.result?.title).toBe('H013 p0-native-b')

  const owner = await fixture.page.evaluate(async ({ taskId, sessionId }) => {
    const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
      WorkstationBridge & { takeControl: (id: string, session: string) => Promise<Record<string, unknown>> }

    return bridge.takeControl(taskId, sessionId)
  }, a)

  // Global controlOwner projects the active tab (session B), not every task.
  // Lease authority is owned per BrowserTask; verify A explicitly.
  const ownedTasks = owner.tasks as Array<BrowserTaskRecord & { humanControlLease?: { owner?: string } }>
  expect(ownedTasks.find(task => task.taskId === a.taskId)?.humanControlLease?.owner).toBe('human')

  const denied = await fetch(`${controller.url}/v1/action`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${controller.token}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      action: 'browser_navigate',
      arguments: { url: `${pageBaseUrl}/p0-denied-should-not-load` },
      task_id: a.taskId,
      session_id: a.sessionId
    })
  })

  const deniedBody = (await denied.json()) as Record<string, unknown>
  expect(denied.status).toBe(409)
  expect(deniedBody.error_code).toBe('USER_CONTROL_ACTIVE')

  // The unrelated session must remain operable while the human owns A.
  const unaffected = await browserAction(b.taskId, b.sessionId, `${pageBaseUrl}/p0-native-b-continued`)
  expect(unaffected.result?.title).toBe('H013 p0-native-b-continued')

  const released = await fixture.page.evaluate(async taskId => {
    const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
      WorkstationBridge & { releaseControl: (id: string) => Promise<Record<string, unknown>> }

    return bridge.releaseControl(taskId)
  }, a.taskId)

  expect(released.controlOwner).toBe('agent')

  const resumed = await browserAction(a.taskId, a.sessionId, `${pageBaseUrl}/p0-native-a-resumed`)
  expect(resumed.result?.title).toBe('H013 p0-native-a-resumed')

  const readback = await controllerRequest('/v1/action', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_snapshot',
      task_id: a.taskId,
      session_id: a.sessionId,
      arguments: { full: false }
    })
  })

  expect(readback.result?.url).toBe(`${pageBaseUrl}/p0-native-a-resumed`)
  const resources = await controllerRequest('/resources')
  const taskResources = (resources.resources ?? []).filter(resource => resource.resource_type === 'browser_task')
  expect(taskResources.find(resource => resource.task_id === a.taskId)?.session_id).toBe(a.sessionId)
  expect(taskResources.find(resource => resource.task_id === b.taskId)?.session_id).toBe(b.sessionId)
})


test('P0: Browser UI Take Control and Release Control buttons are actually clickable', async () => {
  if (!fixture || !controller) {
    throw new Error('P0 native UI fixture is not ready')
  }

  const taskId = 'p0-ui-clickability'
  const sessionId = 'p0-ui-click-session'
  const initial = await browserAction(taskId, sessionId, `${pageBaseUrl}/p0-ui-clickability`)
  expect(initial.result?.title).toBe('H013 p0-ui-clickability')

  // Exercise actual React controls and Electron hit testing, not simulated
  // state or direct bridge calls.
  await fixture.page.getByRole('button', { name: /^(Workstation|Browser)$/ }).click()
  const take = fixture.page.getByRole('button', { name: 'Take Control', exact: true })
  await expect(take).toBeVisible()
  await take.click()
  const release = fixture.page.getByRole('button', { name: 'Release Control', exact: true })
  await expect(release).toBeVisible()
  await release.click()
  await expect(take).toBeVisible()

  const result = await browserAction(taskId, sessionId, `${pageBaseUrl}/p0-ui-clickability-resumed`)
  expect(result.result?.title).toBe('H013 p0-ui-clickability-resumed')
})


// Native Browser mutation tests must run before the deliberate cold restart
// test, which closes and replaces the shared Electron E2E fixture.
test('P0: native Browser mutation remains observable after lost controller acknowledgment', async () => {
  if (!fixture || !controller) {throw new Error('P0 native uncertainty fixture unavailable')}
  uncertainNativeEffectCount = 0
  const taskId = 'p0-native-uncertain-effect'
  const sessionId = 'p0-native-uncertain-session'
  const otherTask = 'p0-native-independent-read'
  const otherSession = 'p0-native-other-session'
  const navigation = await browserAction(taskId, sessionId, `${pageBaseUrl}/p0-uncertain-native`)
  expect(navigation.result?.title).toBe('H013 p0-uncertain-native')

  const initial = await controllerRequest('/v1/action', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ action: 'browser_snapshot', task_id: taskId, session_id: sessionId, arguments: {} })
  })

  const elements = (initial.result?.elements ?? []) as Array<{ ref?: string; testid?: string; label?: string }>
  const target = elements.find(el => el.testid === 'commit-once' || el.label?.includes('Commit external'))
  expect(target?.ref).toMatch(/^@e\d+$/)

  // Dispatch the real controller mutation and intentionally lose the HTTP
  // acknowledgement AFTER the external loopback server records the effect.
  // A client timeout must not be taken as evidence of mutation failure.
  const abandoned = new AbortController()

  const pending = fetch(`${controller.url}/v1/action`, {
    method: 'POST',
    signal: abandoned.signal,
    headers: { authorization: `Bearer ${controller.token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ action: 'browser_click', task_id: taskId, session_id: sessionId,
      operation_id: 'p0-native-uncertain-op-1', arguments: { ref: target!.ref } })
  }).then(() => 'acknowledged', () => 'client_timeout')

  await expect.poll(async () => {
    const read = await fetch(`${pageBaseUrl}/p0-native-effect-state`)
    const body = await read.json() as { applied: number }

    return body.applied
  }, { timeout: 10000 }).toBe(1)
  abandoned.abort(new Error('client_timeout_after_external_effect'))
  expect(await pending).toBe('client_timeout')

  // Independent read: do NOT resend browser_click to discover what happened.
  await expect.poll(async () => {
    const snap = await controllerRequest('/v1/action', { method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action: 'browser_snapshot', task_id: taskId, session_id: sessionId, arguments: {} })
    })

    return String(snap.result?.snapshot ?? '').includes('COMMITTED')
  }, { timeout: 10000 }).toBe(true)
  const recorded = await fetch(`${pageBaseUrl}/p0-native-effect-state`)
  expect((await recorded.json() as { applied: number }).applied).toBe(1)
  const unrelated = await browserAction(otherTask, otherSession, `${pageBaseUrl}/p0-independent-read-available`)
  expect(unrelated.result?.title).toBe('H013 p0-independent-read-available')
  expect(uncertainNativeEffectCount).toBe(1)
})

// A cold restart is only a BrowserTask persistence test when the BrowserTask
// belongs to an actual persisted Hermes chat. Synthetic controller-only
// session IDs are not discoverable by the renderer's lazy restore path.

test('P0: native UI acknowledges canonical uncertain Browser handoff without replay', async () => {
  if (!fixture || !controller) {throw new Error('P0 native review fixture unavailable')}
  const session = await createRealChat(fixture, 'P0 native review proof')
  await openStoredSessionByTitle(fixture.page, session.label, 'P0 native review proof')
  const taskId = 'p0-native-human-review'
  await browserAction(taskId, session.id, pageBaseUrl + '/p0-review-state')

  // Seed only the canonical HumanHandoffManager JSON under disposable HERMES_HOME.
  // The agent-to-review triggering path remains a separate unqualified gate.
  const reviewId = 'handoff-p0-native-review-once'
  const file = path.join(fixture.sandbox.hermesHome, 'workstation', 'human_handoffs.json')
  await fs.promises.mkdir(path.dirname(file), { recursive: true })
  await fs.promises.writeFile(file, JSON.stringify({
    schema_version: 1,
    handoffs: [{
      handoff_id: reviewId, task_id: taskId, session_id: session.id,
      reason: 'uncertain_mutation_requires_review',
      scope: { operation_key: 'p0-e2e-click', run_id: 'p0-run-e2e' },
      status: 'waiting-for-human', requested_at: new Date().toISOString(),
      resumed_at: null, returned_by: null
    }]
  }), 'utf8')

  // Prove the exact authenticated renderer-to-backend route first, rather than
  // assuming a missing banner is a React defect.
  const backendReviews = await fixture.page.evaluate(async sessionId => {
    return (window as unknown as DesktopBridgeWindow).hermesDesktop.api<{
      handoffs: Array<{ handoff_id: string; session_id: string }>
    }>({ path: '/api/workstation/handoffs?session_id=' + encodeURIComponent(sessionId), connectionId: 'local' })
  }, session.id)

  expect(backendReviews.handoffs).toEqual(expect.arrayContaining([
    expect.objectContaining({ handoff_id: reviewId, session_id: session.id })
  ]))

  await fixture.page.getByRole('button', { name: /^(Workstation|Browser)$/ }).click()
  const transfer = fixture.page.getByRole('button', { name: 'Transfer Viewport to Chat Right Rail' })
  await expect(transfer).toBeVisible()
  await transfer.click()
  // Hub exit can restore a prior draft tab and leave the preview rail folded.
  // Re-select the canonical conversation and expose the rail through real UI.
  await openStoredSessionByTitle(fixture.page, session.label, 'P0 native review proof')
  const showRail = fixture.page.getByRole('button', { name: 'Show right sidebar' })

  if (await showRail.isVisible()) {await showRail.click()}

  const review = fixture.page.getByRole('button', { name: 'Acknowledge uncertain Browser operation' })
  await expect(review).toBeVisible({ timeout: 25000 })
  await review.click()
  await expect(fixture.page.getByText(/Independent readback is required before work can continue/i)).toBeVisible()

  const saved = JSON.parse(await fs.promises.readFile(file, 'utf8')) as {
    handoffs: Array<{ handoff_id: string; status: string; returned_by: string }>
  }

  expect(saved.handoffs).toHaveLength(1)
  expect(saved.handoffs[0]).toMatchObject({
    handoff_id: reviewId, status: 'ready', returned_by: 'desktop-human'
  })

  const snapshot = await controllerRequest('/v1/action', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ action: 'browser_snapshot', task_id: taskId,
      session_id: session.id, arguments: { full: false } })
  })

  expect(snapshot.result?.url).toBe(pageBaseUrl + '/p0-review-state')

  const another = await browserAction('p0-independent-native-review', 'p0-other-native-review',
    pageBaseUrl + '/p0-review-unrelated')

  expect(another.result?.title).toBe('H013 p0-review-unrelated')
})

test('HWH-MVP: Creative Workstation internal tab, web tab switching, and manual tab adoption into session', async () => {
  if (!fixture || !controller) {
    throw new Error('HWH fixture is not ready')
  }

  // 1. Navigate to Workstation Hub
  await fixture.page.getByRole('button', { name: /^(Workstation|Browser)$/ }).click()

  // 2. Open Creative Workstation via button
  const openCreativeBtn = fixture.page.getByRole('button', { name: 'Abrir Creative Workstation' })
  await expect(openCreativeBtn).toBeVisible()
  await openCreativeBtn.click()

  // Verify internal Creative Workstation tab is present
  const creativeTab = fixture.page.getByRole('button', { name: 'Creative Workstation', exact: true })
  await expect(creativeTab).toBeVisible()
  // A new user can work immediately without a pre-existing JSON project.
  await expect(fixture.page.getByRole('button', { name: 'Add rectangle' })).toBeVisible()
  await expect(fixture.page.getByRole('button', { name: 'Importar assets' })).toBeVisible()
  // Closing Creative must reveal the original native Chromium viewport.
  await fixture.page.getByRole('button', { name: 'Fechar Creative Workstation' }).click()
  await expect(creativeTab).toHaveCount(0)

  // 3. Open a new web tab and verify web address bar is visible
  const newTabBtn = fixture.page.getByRole('button', { name: 'New browser tab' })
  await newTabBtn.click()

  const addressInput = fixture.page.locator('input[data-browser-address="true"]')
  await expect(addressInput).toBeVisible()

  // 4. Verify "Levar para sessão" button is present
  const adoptBtn = fixture.page.getByRole('button', { name: 'Levar para sessão' })
  await expect(adoptBtn).toBeVisible()

  // 5. Adopt tab via bridge and verify WebContentsView and BrowserTask association
  const adoptionResult = await fixture.page.evaluate(async () => {
    const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
      WorkstationBridge & { adoptTab: (tabId: string, sessionId: string, taskId?: string) => Promise<any> }

    const state = await bridge.ensure()
    const activeTab = (state.tabs as any[]).find((t: any) => t.id === state.activeTabId) || (state.tabs as any[])[0]

    if (!activeTab) {return null}

    return bridge.adoptTab(activeTab.id, 'session-e2e-mvp-1', 'session-e2e-mvp-1')
  })

  expect(adoptionResult).toBeTruthy()
  expect(adoptionResult.success).toBe(true)
  expect(adoptionResult.sessionId).toBe('session-e2e-mvp-1')
  expect(adoptionResult.taskId).toBe('session-e2e-mvp-1')

  // 6. Verify autonomous agent writes are blocked under human lease
  const denied = await fetch(`${controller.url}/v1/action`, {
    method: 'POST',
    headers: { authorization: `Bearer ${controller.token}`, 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_navigate',
      task_id: adoptionResult.taskId,
      session_id: 'session-e2e-mvp-1',
      arguments: { url: `${pageBaseUrl}/p0-adopt-human-denied` }
    })
  })

  expect(denied.status).toBe(409)
  expect(((await denied.json()) as { error_code?: string }).error_code).toBe('USER_CONTROL_ACTIVE')

  // 7. Explicit release allows resumed agent action
  await fixture.page.evaluate(async (taskId: string) => {
    const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
      WorkstationBridge & { releaseControl: (taskId?: string) => Promise<unknown> }

    await bridge.releaseControl(taskId)
  }, adoptionResult.taskId)

  const allowed = await fetch(`${controller.url}/v1/action`, {
    method: 'POST',
    headers: { authorization: `Bearer ${controller.token}`, 'content-type': 'application/json' },
    body: JSON.stringify({
      action: 'browser_navigate',
      task_id: adoptionResult.taskId,
      session_id: 'session-e2e-mvp-1',
      arguments: { url: `${pageBaseUrl}/p0-adopt-resumed` }
    })
  })

  expect(allowed.status).toBe(200)
})

test('HWH-OVERLAY: native Browser view detaches on New session and restores without state loss or cross-session leak', async () => {
  test.setTimeout(180_000)

  if (!fixture || !controller) {
    throw new Error('HWH-OVERLAY fixture was not initialized')
  }

  // 1. Create and open session A with native Browser
  const sessionA = await createRealChat(fixture, 'HWH-OVERLAY Chat A')
  const urlA = `${pageBaseUrl}/hwh-form-a`

  await openStoredSessionByTitle(fixture.page, sessionA.label, 'HWH-OVERLAY Chat A')
  await browserAction('hwh-overlay-task-a', sessionA.id, urlA)
  await expect.poll(async () => activeViewportChildren(await nativeViewportSnapshot(fixture!.app))[0]?.url, { timeout: 30_000 }).toBe(urlA)

  // 2. Local fixture page with form is loaded; register WebContents ID and modify form field
  const initialSnapshot = await nativeViewportSnapshot(fixture.app)
  const childA = activeViewportChild(initialSnapshot)
  const webContentsIdA = childA.webContentsId

  expect(webContentsIdA).toBeTruthy()

  // 3. User modifies form input
  await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    if (!wc) {
      throw new Error(`WebContents ${id} not found`)
    }

    await wc.executeJavaScript(`
      const input = document.getElementById('form-input');
      if (input) {
        input.value = 'user-typed-value-session-a';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `)
  }, webContentsIdA)

  const valueA = await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    return wc?.executeJavaScript(`document.getElementById('form-input')?.value`)
  }, webContentsIdA)

  expect(valueA).toBe('user-typed-value-session-a')

  // 4. Click "New session" to open B
  const newSessionBtn = fixture.page.locator('[data-slot="sidebar"] button').filter({ hasText: 'New session' }).first()

  await newSessionBtn.waitFor({ state: 'visible', timeout: 30_000 })
  await newSessionBtn.click()

  const composer = fixture.page.locator('[contenteditable="true"]').first()

  await expect(composer).toBeVisible({ timeout: 20_000 })
  await composer.click()
  await composer.fill('Hello from interactive fresh session B')

  // 5. Verify WebContentsView of session A was removed from visible children of BrowserWindow
  await expect.poll(async () => {
    const snap = await nativeViewportSnapshot(fixture!.app)

    return activeViewportChildren(snap).length === 0 && !snap?.children.some(c => c.webContentsId === webContentsIdA)
  }, { timeout: 20_000 }).toBe(true)

  // 6. Wait and check again to detect late re-attachment
  await new Promise(resolve => setTimeout(resolve, 2000))
  const delayedSnap = await nativeViewportSnapshot(fixture.app)

  expect(activeViewportChildren(delayedSnap)).toHaveLength(0)
  expect(delayedSnap?.children.some(c => c.webContentsId === webContentsIdA)).toBe(false)

  // 7. Click New session again and verify detachment remains solid
  await newSessionBtn.click()
  await expect(composer).toBeVisible({ timeout: 20_000 })
  await new Promise(resolve => setTimeout(resolve, 1500))
  const secondDelayedSnap = await nativeViewportSnapshot(fixture.app)

  expect(activeViewportChildren(secondDelayedSnap)).toHaveLength(0)
  expect(secondDelayedSnap?.children.some(c => c.webContentsId === webContentsIdA)).toBe(false)

  // 8. Return to session A
  await openStoredSessionByTitle(fixture.page, sessionA.label, 'HWH-OVERLAY Chat A')

  // 9. Verify page restored with same webContentsId, URL, and input value
  await expect.poll(async () => {
    const snap = await nativeViewportSnapshot(fixture!.app)
    const child = activeViewportChildren(snap)[0]

    return child?.webContentsId === webContentsIdA && child?.url === urlA
  }, { timeout: 20_000 }).toBe(true)

  const restoredValueA = await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    return wc?.executeJavaScript(`document.getElementById('form-input')?.value`)
  }, webContentsIdA)

  expect(restoredValueA).toBe('user-typed-value-session-a')

  const evidenceDir = path.join(fixture.sandbox.root, 'workstation')

  await fixture.page.screenshot({ path: path.join(evidenceDir, 'hwh-overlay-session-a-restored.png') })

  // 10. Switch between two sessions that both have Browser open, in both directions
  const sessionB = await createRealChat(fixture, 'HWH-OVERLAY Chat B')
  const urlB = `${pageBaseUrl}/hwh-form-b`

  await openStoredSessionByTitle(fixture.page, sessionB.label, 'HWH-OVERLAY Chat B')
  await browserAction('hwh-overlay-task-b', sessionB.id, urlB)

  await expect.poll(async () => {
    const snap = await nativeViewportSnapshot(fixture!.app)
    const child = activeViewportChildren(snap)[0]

    return child?.url === urlB
  }, { timeout: 20_000 }).toBe(true)

  const snapB = await nativeViewportSnapshot(fixture.app)
  const childB = activeViewportChildren(snapB)[0]
  const webContentsIdB = childB.webContentsId

  expect(webContentsIdB).toBeTruthy()
  expect(webContentsIdB).not.toBe(webContentsIdA)

  await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    await wc.executeJavaScript(`
      const input = document.getElementById('form-input');
      if (input) {
        input.value = 'user-typed-value-session-b';
      }
    `)
  }, webContentsIdB)

  // Direction 1: Switch B -> A
  await openStoredSessionByTitle(fixture.page, sessionA.label, 'HWH-OVERLAY Chat A')
  await expect.poll(async () => {
    const snap = await nativeViewportSnapshot(fixture!.app)
    const child = activeViewportChildren(snap)[0]

    return child?.webContentsId === webContentsIdA && child?.url === urlA
  }, { timeout: 20_000 }).toBe(true)

  const snapBackA = await nativeViewportSnapshot(fixture.app)

  expect(snapBackA?.children.some(c => c.webContentsId === webContentsIdB)).toBe(false)

  const valueAfterSwitchA = await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    return wc?.executeJavaScript(`document.getElementById('form-input')?.value`)
  }, webContentsIdA)

  expect(valueAfterSwitchA).toBe('user-typed-value-session-a')

  // Direction 2: Switch A -> B
  await openStoredSessionByTitle(fixture.page, sessionB.label, 'HWH-OVERLAY Chat B')
  await expect.poll(async () => {
    const snap = await nativeViewportSnapshot(fixture!.app)
    const child = activeViewportChildren(snap)[0]

    return child?.webContentsId === webContentsIdB && child?.url === urlB
  }, { timeout: 20_000 }).toBe(true)

  const snapBackB = await nativeViewportSnapshot(fixture.app)

  expect(snapBackB?.children.some(c => c.webContentsId === webContentsIdA)).toBe(false)

  const valueAfterSwitchB = await fixture.app.evaluate(async ({ webContents }, id) => {
    const wc = webContents.fromId(id!)

    return wc?.executeJavaScript(`document.getElementById('form-input')?.value`)
  }, webContentsIdB)

  expect(valueAfterSwitchB).toBe('user-typed-value-session-b')

  await fixture.page.screenshot({ path: path.join(evidenceDir, 'hwh-overlay-session-b.png') })

  // Clean up tasks
  for (const taskId of ['hwh-overlay-task-a', 'hwh-overlay-task-b']) {
    await fixture.page.evaluate(
      id => (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.destroyTask(id),
      taskId
    )
  }
})

test('P0: released and active human leases recover safely across cold Electron restarts', async () => {
  test.setTimeout(360_000)

  if (!fixture || !controller) {
    throw new Error('P0 restart fixture is not ready')
  }

  const session = await createRealChat(fixture, 'P0 cold restart real session')
  const taskId = 'p0-cold-restart-a'
  const url = `${pageBaseUrl}/p0-cold-restart-a`
  await openStoredSessionByTitle(fixture.page, session.label, 'P0 cold restart real session')
  const before = await browserAction(taskId, session.id, url)
  expect(before.result?.title).toBe('H013 p0-cold-restart-a')

  await fixture.page.evaluate(async ({ taskId, sessionId }) => {
    const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
      WorkstationBridge & {
        takeControl: (id: string, session: string) => Promise<unknown>
        releaseControl: (id: string) => Promise<unknown>
      }

    await bridge.takeControl(taskId, sessionId)
    await bridge.releaseControl(taskId)
  }, { taskId, sessionId: session.id })

  const env = buildAppEnv(fixture.sandbox, { HERMES_DESKTOP_E2E_HEADLESS: '1' })
  const oldToken = controller.token
  const controlPath = path.join(fixture.sandbox.root, 'workstation', 'Runtime', 'browser-control.json')
  await fixture.app.close()
  const restarted = await launchDesktop(env)
  // Unlike the previous fixture, the test must hand the *new* app/page to
  // readiness, session restore and later assertions.
  fixture.app = restarted.app
  fixture.page = restarted.page

  try {
    await waitForAppReady(fixture, 120_000, false)
    await expect.poll(
      async () => (await readControllerFile(controlPath)).token,
      { timeout: 30_000 }
    ).not.toBe(oldToken)
    controller = await readControllerFile(controlPath)
    await openStoredSessionByTitle(fixture.page, session.label, 'P0 cold restart real session')

    const restored = await fixture.page.evaluate(async taskId => {
      const tasks = await (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser.listTasks()

      return tasks.find(task => task.taskId === taskId) || null
    }, taskId)

    expect(restored?.sessionHost).toBe(session.id)

    const resumed = await browserAction(taskId, session.id, `${pageBaseUrl}/p0-cold-restart-resumed`)
    expect(resumed.result?.title).toBe('H013 p0-cold-restart-resumed')

    const readback = await controllerRequest('/v1/action', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        action: 'browser_snapshot', task_id: taskId, session_id: session.id, arguments: {}
      })
    })

    expect(readback.result?.url).toBe(`${pageBaseUrl}/p0-cold-restart-resumed`)

    // A second cold restart intentionally occurs with a live human lease.
    // Human control must block the old process, then must NOT be restored as
    // an authoritative lease of the new process (contract in browser-task.ts).
    const lease = await fixture.page.evaluate(async ({ taskId, sessionId }) => {
      const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser as
        WorkstationBridge & { takeControl: (id: string, session: string) => Promise<unknown> }

      await bridge.takeControl(taskId, sessionId)
      const current = (await bridge.listTasks()).find(task => task.taskId === taskId)

      return (current as BrowserTaskRecord & { humanControlLease?: { owner?: string } })?.humanControlLease
    }, { taskId, sessionId: session.id })

    expect(lease?.owner).toBe('human')

    const denied = await fetch(`${controller.url}/v1/action`, {
      method: 'POST',
      headers: { authorization: `Bearer ${controller.token}`, 'content-type': 'application/json' },
      body: JSON.stringify({
        action: 'browser_navigate', task_id: taskId, session_id: session.id,
        arguments: { url: `${pageBaseUrl}/p0-stale-human-denied` }
      })
    })

    expect(denied.status).toBe(409)
    expect((await denied.json() as { error_code?: string }).error_code).toBe('USER_CONTROL_ACTIVE')

    const leaseOwnerToken = controller.token
    await restarted.app.close()
    const activeRestart = await launchDesktop(env)
    fixture.app = activeRestart.app
    fixture.page = activeRestart.page

    try {
      await waitForAppReady(fixture, 120_000, false)
      await expect.poll(async () => (await readControllerFile(controlPath)).token,
        { timeout: 30_000 }).not.toBe(leaseOwnerToken)
      controller = await readControllerFile(controlPath)
      await openStoredSessionByTitle(fixture.page, session.label, 'P0 cold restart real session')

      const recovered = await fixture.page.evaluate(async taskId => {
        const bridge = (window as unknown as DesktopBridgeWindow).hermesDesktop.workstationBrowser

        return (await bridge.listTasks()).find(task => task.taskId === taskId)
      }, taskId)

      expect(recovered?.sessionHost).toBe(session.id)
      expect((recovered as BrowserTaskRecord & { humanControlLease?: unknown })?.humanControlLease).toBeUndefined()
      const safelyResumed = await browserAction(taskId, session.id, `${pageBaseUrl}/p0-active-lease-restart`)
      expect(safelyResumed.result?.title).toBe('H013 p0-active-lease-restart')

      const finalSnapshot = await controllerRequest('/v1/action', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ action: 'browser_snapshot', task_id: taskId,
          session_id: session.id, arguments: {} })
      })

      expect(finalSnapshot.result?.url).toBe(`${pageBaseUrl}/p0-active-lease-restart`)
    } finally {
      await activeRestart.app.close().catch(() => undefined)
    }
  } finally {
    // Fixture cleanup owns the first Electron instance captured at setup.
    // Explicitly stop the replacement so no E2E orphan contaminates later tests.
    await restarted.app.close().catch(() => undefined)
  }
})
