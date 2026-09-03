import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'

const repoRoot = process.argv[2]
if (!repoRoot) {
  console.error('repo root argument is required')
  process.exit(2)
}

const expectedSha = '1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70'
const tempRoot = path.join(os.tmpdir(), 'HermesImpl4NativeSmokeV9')
const stateRoot = path.join(os.tmpdir(), 'HermesImpl4NativeSmokeStateV9')
const harnessTs = path.join(tempRoot, 'impl4-native-smoke.ts')
const appDir = path.join(tempRoot, 'electron-app')
const bundle = path.join(appDir, 'main.mjs')
const packageJsonPath = path.join(appDir, 'package.json')
const logPath = path.join(tempRoot, 'impl4-native-smoke.log')

fs.rmSync(tempRoot, { recursive: true, force: true })
fs.rmSync(stateRoot, { recursive: true, force: true })
fs.mkdirSync(tempRoot, { recursive: true })
fs.mkdirSync(appDir, { recursive: true })
fs.mkdirSync(stateRoot, { recursive: true })

const candidates = {
  electron: [
    path.join(repoRoot, 'apps', 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
    path.join(repoRoot, 'node_modules', 'electron', 'dist', 'electron.exe')
  ],
  esbuild: [
    path.join(repoRoot, 'apps', 'desktop', 'node_modules', 'esbuild', 'bin', 'esbuild'),
    path.join(repoRoot, 'node_modules', 'esbuild', 'bin', 'esbuild')
  ]
}

function firstExisting(items) {
  return items.find(p => fs.existsSync(p))
}

const electronExe = firstExisting(candidates.electron)
const esbuildCli = firstExisting(candidates.esbuild)

if (!electronExe) {
  console.error('Electron executable not found.')
  console.error(candidates.electron.join('\n'))
  process.exit(2)
}
if (!esbuildCli) {
  console.error('esbuild JS CLI not found.')
  console.error(candidates.esbuild.join('\n'))
  process.exit(2)
}

function log(...parts) {
  const line = parts.map(String).join(' ')
  console.log(line)
  fs.appendFileSync(logPath, line + '\n')
}

function run(cmd, args, { timeoutMs = 60000, env = process.env } = {}) {
  return new Promise((resolve, reject) => {
    log('[impl4-smoke] RUN:', cmd, ...args)
    const child = spawn(cmd, args, {
      cwd: repoRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: false,
      shell: false
    })

    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      log(`[impl4-smoke] TIMEOUT after ${timeoutMs}ms; killing PID ${child.pid}`)
      try { child.kill('SIGKILL') } catch {}
      reject(new Error(`timeout: ${cmd} ${args.join(' ')}`))
    }, timeoutMs)

    child.stdout.on('data', chunk => {
      const s = chunk.toString()
      process.stdout.write(s)
      fs.appendFileSync(logPath, s)
    })
    child.stderr.on('data', chunk => {
      const s = chunk.toString()
      process.stderr.write(s)
      fs.appendFileSync(logPath, s)
    })

    child.on('error', err => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      reject(err)
    })

    child.on('exit', (code, signal) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      if (code === 0) resolve({ code, signal, pid: child.pid })
      else reject(new Error(`exit code ${code}, signal ${signal ?? 'none'}: ${cmd} ${args.join(' ')}`))
    })
  })
}

const harnessSource = String.raw`
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { app, BrowserWindow } from 'electron'

const mode = process.env.IMPL4_SMOKE_MODE
if (!mode || !['live', 'restart1', 'restart2'].includes(mode)) throw new Error('IMPL4_SMOKE_MODE must be live, restart1, or restart2')

const home = process.env.HERMES_WORKSTATION_HOME
if (!home) throw new Error('HERMES_WORKSTATION_HOME is required')

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message)
}

async function startLocalPage(): Promise<{ url: string; close: () => Promise<void> }> {
  const server = http.createServer((_req, res) => {
    const html = '<!doctype html><html><head><meta charset="utf-8"><title>Hermes Impl4 Native Smoke</title></head><body style="font-family:sans-serif;padding:40px"><h1>Hermes Implementation 4 — Native Smoke</h1><p>REAL ELECTRON / REAL WEBCONTENTSVIEW</p><input value="native-smoke"/><div style="height:1400px"></div><p>Bottom</p></body></html>'
    res.writeHead(200, {
      'content-type': 'text/html; charset=utf-8',
      'content-length': Buffer.byteLength(html),
      'cache-control': 'no-store'
    })
    res.end(html)
  })
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => resolve())
  })
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('local server did not bind')
  return {
    url: 'http://127.0.0.1:' + address.port + '/?access_token=impl4-native-page-secret',
    close: () => new Promise(resolve => server.close(() => resolve()))
  }
}

console.log('HARNESS_BOOT', JSON.stringify({ pid: process.pid, mode, electron: process.versions.electron }))
await app.whenReady()
console.log('HARNESS_READY', JSON.stringify({ pid: process.pid, mode }))

const runtimeModule = await import(${JSON.stringify(path.join(repoRoot, 'apps', 'desktop', 'electron', 'workstation-browser-runtime.ts'))})
const { getWorkstationBrowserRuntime, workstationBrowserTaskStatePath } = runtimeModule
const runtime = getWorkstationBrowserRuntime()

async function shutdown(win?: BrowserWindow, closeServer?: () => Promise<void>) {
  try { await runtime.destroy() } catch {}
  if (win && !win.isDestroyed()) win.destroy()
  if (closeServer) await closeServer()
}

async function live() {
  const taskId = 'impl4-native-task-a'
  const page = await startLocalPage()
  const win = new BrowserWindow({ width: 1200, height: 820, show: true, title: 'Hermes Impl4 Native Smoke' })
  const bounds = { x: 20, y: 20, width: 1120, height: 730 }

  runtime.createTask({ taskId })
  runtime.showTask(taskId, win, bounds)

  const tab = runtime.state().tabs.find(t => t.ownerTaskId === taskId)
  assert(tab, 'task-owned tab missing')
  const wc = runtime.getWebContents(tab.id)
  assert(wc, 'task-owned WebContents missing')

  await wc.loadURL(page.url)
  const sentinel = 'sentinel-' + Date.now() + '-' + Math.random().toString(16).slice(2)
  await wc.executeJavaScript('window.__impl4SmokeSentinel=' + JSON.stringify(sentinel) + '; window.scrollTo(0,700); true', true)

  const before = {
    taskId, tabId: tab.id, webContentsId: wc.id, url: wc.getURL(),
    sentinel: await wc.executeJavaScript('window.__impl4SmokeSentinel', true),
    pageCount: runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length
  }
  console.log('SMOKE_A_BEFORE', JSON.stringify(before))
  console.log('VISUAL_CHECK_VISIBLE_3S')
  await sleep(3000)

  runtime.hideTask(taskId)
  assert(!wc.isDestroyed(), 'hideTask destroyed WebContents')
  console.log('VISUAL_CHECK_HIDDEN_2S')
  await sleep(2000)

  runtime.showTask(taskId, win, bounds)
  assert(runtime.getWebContents(tab.id) === wc, 'hide/show replaced WebContents')
  assert(wc.id === before.webContentsId, 'hide/show changed webContents.id')
  assert(wc.getURL() === before.url, 'hide/show changed URL')
  assert(await wc.executeJavaScript('window.__impl4SmokeSentinel', true) === sentinel, 'hide/show lost JS sentinel')
  assert(runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length === 1, 'hide/show duplicated page')
  console.log('SMOKE_A_AFTER_HIDE_SHOW', JSON.stringify({
    taskId, tabId: tab.id, webContentsId: wc.id, url: wc.getURL(),
    sentinel: await wc.executeJavaScript('window.__impl4SmokeSentinel', true),
    pageCount: runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length
  }))
  console.log('VISUAL_CHECK_REEXPOSED_3S')
  await sleep(3000)

  runtime.parkTask(taskId)
  assert(!wc.isDestroyed(), 'parkTask destroyed WebContents')
  console.log('VISUAL_CHECK_PARKED_2S')
  await sleep(2000)

  runtime.showTask(taskId, win, bounds)
  assert(runtime.getWebContents(tab.id) === wc, 'park/show replaced WebContents')
  assert(wc.id === before.webContentsId, 'park/show changed webContents.id')
  assert(wc.getURL() === before.url, 'park/show changed URL')
  assert(await wc.executeJavaScript('window.__impl4SmokeSentinel', true) === sentinel, 'park/show lost JS sentinel')
  assert(runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length === 1, 'park/show duplicated page')
  console.log('SMOKE_A_AFTER_PARK_SHOW', JSON.stringify({
    taskId, tabId: tab.id, webContentsId: wc.id, url: wc.getURL(),
    sentinel: await wc.executeJavaScript('window.__impl4SmokeSentinel', true),
    pageCount: runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length
  }))
  console.log('VISUAL_CHECK_REEXPOSED_AGAIN_3S')
  await sleep(3000)

  const destroyed = runtime.destroyTask(taskId)
  assert(destroyed === true, 'destroyTask did not return true')
  await sleep(250)

  const destroyEvidence = {
    destroyed: wc.isDestroyed(),
    listed: runtime.listTasks().some(t => t.taskId === taskId),
    ownerTabs: runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length
  }
  assert(destroyEvidence.destroyed, 'destroyTask did not destroy WebContents')
  assert(!destroyEvidence.listed, 'destroyTask left task listed')
  assert(destroyEvidence.ownerTabs === 0, 'destroyTask left task-owned tab')
  console.log('SMOKE_B_DESTROY', JSON.stringify(destroyEvidence))
  console.log('NATIVE_LIVE_AND_DESTROY_PASS')

  await shutdown(win, page.close)
}

async function restart1() {
  const taskId = 'impl4-native-restart-task'
  const page = await startLocalPage()
  const win = new BrowserWindow({ width: 1000, height: 700, show: true, title: 'Hermes Impl4 Restart Phase 1' })
  const bounds = { x: 20, y: 20, width: 920, height: 610 }

  runtime.createTask({ taskId })
  runtime.showTask(taskId, win, bounds)
  const tab = runtime.state().tabs.find(t => t.ownerTaskId === taskId)
  assert(tab, 'restart task tab missing')
  const wc = runtime.getWebContents(tab.id)
  assert(wc, 'restart task WebContents missing')
  await wc.loadURL(page.url)
  await wc.executeJavaScript("window.__typedPassword='typed-password-secret'; true", true)
  runtime.parkTask(taskId)

  const logical = runtime.listTasks().find(t => t.taskId === taskId)
  assert(logical, 'restart task missing before exit')

  const statePath = workstationBrowserTaskStatePath()
  const persisted = fs.readFileSync(statePath, 'utf8')
  assert(!persisted.includes('impl4-native-page-secret'), 'persisted page URL secret')
  assert(!persisted.includes('typed-password-secret'), 'persisted renderer secret')

  fs.writeFileSync(path.join(home, 'phase1.json'), JSON.stringify({ pid: process.pid, taskId }, null, 2))
  console.log('SMOKE_C_PHASE1', JSON.stringify({
    pid: process.pid, taskId, status: logical.status,
    recoveryState: logical.recoveryState, secretIsolation: true
  }))

  await sleep(1000)
  await shutdown(win, page.close)
}

async function restart2() {
  const taskId = 'impl4-native-restart-task'
  const phase1 = JSON.parse(fs.readFileSync(path.join(home, 'phase1.json'), 'utf8'))
  assert(phase1.pid !== process.pid, 'same Electron PID reused across restart phases')

  const restored = runtime.listTasks().find(t => t.taskId === taskId)
  assert(restored, 'logical task did not restore')

  const pageCountBefore = runtime.state().tabs.filter(t => t.ownerTaskId === taskId).length
  assert(pageCountBefore === 0, 'restored task already had live page')
  assert(restored.status === 'parked', 'restored status expected parked, got ' + restored.status)
  assert(restored.recoveryState === 'restored', 'expected restored recoveryState, got ' + restored.recoveryState)

  const win = new BrowserWindow({ width: 1000, height: 700, show: true, title: 'Hermes Impl4 Restart Phase 2' })
  const shown = runtime.showTask(taskId, win, { x: 20, y: 20, width: 920, height: 610 })

  const ownerTabs = runtime.state().tabs.filter(t => t.ownerTaskId === taskId)
  assert(ownerTabs.length === 1, 'lazy recreation page count expected 1, got ' + ownerTabs.length)
  assert(shown.taskId === taskId, 'taskId changed after recreation')
  assert(shown.recoveryState === 'recreated', 'expected recreated recoveryState, got ' + shown.recoveryState)

  console.log('SMOKE_C_PHASE2', JSON.stringify({
    phase1Pid: phase1.pid,
    phase2Pid: process.pid,
    sameLogicalTaskId: shown.taskId === phase1.taskId,
    restoredStatusBefore: restored.status,
    restoredRecoveryBefore: restored.recoveryState,
    pageCountBefore,
    pageCountAfter: ownerTabs.length,
    recoveryStateAfter: shown.recoveryState,
    ownerTaskId: ownerTabs[0]?.ownerTaskId
  }))

  await sleep(1000)
  runtime.destroyTask(taskId)
  await shutdown(win)
  console.log('NATIVE_RESTART_PASS')
}

try {
  if (mode === 'live') await live()
  if (mode === 'restart1') await restart1()
  if (mode === 'restart2') await restart2()
  app.exit(0)
} catch (error) {
  console.error('NATIVE_IMPL4_SMOKE_FAIL', error instanceof Error ? (error.stack || error.message) : String(error))
  try { await runtime.destroy() } catch {}
  app.exit(1)
}
`

fs.writeFileSync(harnessTs, harnessSource, 'utf8')
fs.writeFileSync(packageJsonPath, JSON.stringify({
  name: 'hermes-impl4-native-smoke',
  private: true,
  type: 'module',
  main: 'main.mjs'
}, null, 2), 'utf8')

log('SHA=' + expectedSha)
log('WINDOWS=' + os.release())
log('NODE=' + process.version)
log('ELECTRON_EXE=' + electronExe)
log('ELECTRON_APP_DIR=' + appDir)
log('ESBUILD_CLI=' + esbuildCli)
log('LOG=' + logPath)

try {
  await run(process.execPath, [
    esbuildCli,
    harnessTs,
    '--bundle',
    '--platform=node',
    '--format=esm',
    '--target=node20',
    `--outfile=${bundle}`,
    '--external:electron'
  ], { timeoutMs: 30000 })

  if (!fs.existsSync(bundle) || fs.statSync(bundle).size < 1000) {
    throw new Error('esbuild returned success but native harness bundle is missing/too small')
  }

  const baseEnv = {
    ...process.env,
    HERMES_WORKSTATION_HOME: stateRoot
  }

  log('[impl4-smoke] Electron app directory:', appDir)

  log('[impl4-smoke] === SMOKE A+B: live identity / hide / park / show / destroy ===')
  await run(electronExe, [appDir], {
    timeoutMs: 45000,
    env: { ...baseEnv, IMPL4_SMOKE_MODE: 'live' }
  })

  log('[impl4-smoke] === SMOKE C1: persist in Electron process #1 ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, IMPL4_SMOKE_MODE: 'restart1' }
  })

  log('[impl4-smoke] === SMOKE C2: restore in Electron process #2 ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, IMPL4_SMOKE_MODE: 'restart2' }
  })

  log('FINAL=NATIVE_IMPL4_SMOKE_PASS')
  log('LOG_PATH=' + logPath)
  process.exit(0)
} catch (error) {
  log('FINAL=NATIVE_IMPL4_SMOKE_FAIL')
  log(error instanceof Error ? (error.stack || error.message) : String(error))
  log('LOG_PATH=' + logPath)
  process.exit(1)
}
