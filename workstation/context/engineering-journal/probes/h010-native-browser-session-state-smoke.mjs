#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'

const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim()
const head = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' }).trim()
const expectedHead = process.env.H010_EXPECTED_SHA?.trim() || head

function failPrecondition(message) {
  console.error('H010_PRECONDITION_FAIL ' + message)
  process.exit(2)
}

if (process.platform !== 'win32') failPrecondition('native BrowserSessionState smoke requires Windows')
if (head !== expectedHead) failPrecondition('HEAD ' + head + ' does not match expected exact SHA ' + expectedHead)

const electronCandidates = [
  path.join(repoRoot, 'apps', 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
  path.join(repoRoot, 'node_modules', 'electron', 'dist', 'electron.exe')
]
const esbuildCandidates = [
  path.join(repoRoot, 'apps', 'desktop', 'node_modules', 'esbuild', 'bin', 'esbuild'),
  path.join(repoRoot, 'node_modules', 'esbuild', 'bin', 'esbuild')
]
const electronExe = electronCandidates.find(candidate => fs.existsSync(candidate))
const esbuildCli = esbuildCandidates.find(candidate => fs.existsSync(candidate))
if (!electronExe) failPrecondition('electron.exe not found; checked: ' + electronCandidates.join(', '))
if (!esbuildCli) failPrecondition('esbuild JS CLI not found; checked: ' + esbuildCandidates.join(', '))

const tempRoot = path.join(os.tmpdir(), 'HermesH010BrowserSessionState-' + head.slice(0, 12))
const appDir = path.join(tempRoot, 'electron-app')
const harnessTs = path.join(tempRoot, 'h010-native-harness.ts')
const mainCjs = path.join(appDir, 'main.cjs')
const packageJson = path.join(appDir, 'package.json')
const cleanStateRoot = path.join(tempRoot, 'state-clean')
const faultStateRoot = path.join(tempRoot, 'state-fault')
const abruptStateRoot = path.join(tempRoot, 'state-abrupt')
const runtimePath = path.join(repoRoot, 'apps', 'desktop', 'electron', 'workstation-browser-runtime.ts')
const sessionStateModulePath = path.join(
  repoRoot,
  'apps',
  'desktop',
  'electron',
  'workstation-browser-session-state.ts'
)

fs.rmSync(tempRoot, { recursive: true, force: true })
fs.mkdirSync(appDir, { recursive: true })

function killTree(pid) {
  if (!pid) return
  try {
    execFileSync('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' })
  } catch {
    // Best effort after timeout.
  }
}

function run(command, args, { env = process.env, timeoutMs = 60000, allowedCodes = [0] } = {}) {
  return new Promise((resolve, reject) => {
    console.log('RUN ' + command + ' ' + args.join(' '))
    const child = spawn(command, args, {
      cwd: repoRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: false,
      windowsHide: true
    })

    const timer = setTimeout(() => {
      console.error('H010_EXTERNAL_TIMEOUT ' + JSON.stringify({ pid: child.pid, timeoutMs }))
      killTree(child.pid)
      reject(new Error('timeout after ' + timeoutMs + 'ms'))
    }, timeoutMs)

    child.stdout.on('data', chunk => process.stdout.write(chunk))
    child.stderr.on('data', chunk => process.stderr.write(chunk))
    child.on('error', error => {
      clearTimeout(timer)
      reject(error)
    })
    child.on('exit', (code, signal) => {
      clearTimeout(timer)
      if (allowedCodes.includes(code)) resolve({ code, signal, pid: child.pid })
      else reject(new Error('exit code ' + code + ', signal ' + (signal ?? 'none')))
    })
  })
}

function startLocalPageServer() {
  const server = http.createServer((req, res) => {
    const requestUrl = new URL(req.url || '/', 'http://127.0.0.1')
    const title = requestUrl.pathname.includes('task') ? 'Recovery code 482913' : 'OTP 482913'
    const html =
      '<!doctype html><html><head><meta charset="utf-8"><title>' +
      title +
      '</title></head><body><h1>Hermes H010 BrowserSessionState</h1><p>' +
      requestUrl.pathname +
      '</p></body></html>'
    res.writeHead(200, {
      'content-type': 'text/html; charset=utf-8',
      'content-length': Buffer.byteLength(html),
      'cache-control': 'no-store'
    })
    res.end(html)
  })

  return new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      if (!address || typeof address === 'string') {
        reject(new Error('native test page failed to bind'))
        return
      }
      resolve({
        baseUrl: 'http://127.0.0.1:' + address.port,
        close: () => new Promise(done => server.close(() => done()))
      })
    })
  })
}

const harnessSource = String.raw`
import fs from 'node:fs'
import path from 'node:path'
import { app, BrowserWindow } from 'electron'

const mode = process.env.H010_MODE
const home = process.env.HERMES_WORKSTATION_HOME
const baseUrl = process.env.H010_BASE_URL
if (!mode || !home || !baseUrl) {
  console.error('H010_HARNESS_CONFIG_FAIL', JSON.stringify({ mode, hasHome: !!home, hasBaseUrl: !!baseUrl }))
  process.exit(2)
}

fs.mkdirSync(home, { recursive: true })
const hostUserData = path.join(home, 'ElectronHostUserData-' + mode)
fs.mkdirSync(hostUserData, { recursive: true })
app.setPath('userData', hostUserData)

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message)
}
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

console.log('H010_BOOT', JSON.stringify({ pid: process.pid, mode, electron: process.versions.electron }))
const timer = setTimeout(() => {
  console.error('H010_INTERNAL_TIMEOUT', JSON.stringify({ pid: process.pid, mode }))
  app.exit(9)
}, 35000)

app.whenReady().then(async () => {
  const runtimeModule = await import(${JSON.stringify(runtimePath)})
  const sessionModule = await import(${JSON.stringify(sessionStateModulePath)})
  const {
    WorkstationBrowserRuntime,
    getWorkstationBrowserRuntime,
    workstationBrowserSessionStatePath,
    workstationBrowserTaskStatePath
  } = runtimeModule
  const { BrowserSessionStateFilePersistence } = sessionModule

  let failNextRename = false
  let runtime
  if (mode === 'fault') {
    const io = {
      ...fs,
      renameSync: (...args: Parameters<typeof fs.renameSync>) => {
        if (failNextRename) {
          failNextRename = false
          throw new Error('H010 simulated native rename failure')
        }
        fs.renameSync(...args)
      }
    }
    const persistence = new BrowserSessionStateFilePersistence(
      workstationBrowserSessionStatePath(),
      workstationBrowserTaskStatePath(),
      io
    )
    runtime = new WorkstationBrowserRuntime(persistence)
  } else {
    runtime = getWorkstationBrowserRuntime()
  }

  await sleep(100)

  function composite() {
    return JSON.parse(fs.readFileSync(workstationBrowserSessionStatePath(), 'utf8'))
  }
  function serializedComposite() {
    return fs.readFileSync(workstationBrowserSessionStatePath(), 'utf8')
  }
  function makeWindow(title: string) {
    return new BrowserWindow({ width: 1000, height: 700, show: false, title })
  }
  async function shutdown(win?: BrowserWindow) {
    try { await runtime.destroy() } catch {}
    if (win && !win.isDestroyed()) win.destroy()
  }

  async function phaseA() {
    const taskId = 'h010-task'
    const state = runtime.ensure()
    const ordinaryA = state.tabs[0]
    assert(ordinaryA, 'phaseA initial ordinary tab missing')
    const ordinaryAContents = runtime.getWebContents(ordinaryA.id)
    assert(ordinaryAContents, 'phaseA ordinary A WebContents missing')
    await ordinaryAContents.loadURL(baseUrl + '/customers/482913?access_token=h010-query-secret')

    const win = makeWindow('H010 phase A')
    runtime.createTask({ taskId, sessionHost: 'h010-hermes-session' })
    runtime.showTask(taskId, win, { x: 0, y: 0, width: 900, height: 600 })
    const taskTab = runtime.state().tabs.find(tab => tab.ownerTaskId === taskId)
    assert(taskTab, 'phaseA task tab missing')
    const taskContents = runtime.getWebContents(taskTab.id)
    assert(taskContents, 'phaseA task WebContents missing')
    await taskContents.loadURL(baseUrl + '/task#access_token=h010-fragment-secret')

    const afterB = runtime.createTab(baseUrl + '/path/%3Ftoken%3D12345', false)
    const ordinaryB = afterB.tabs.at(-1)
    assert(ordinaryB && !ordinaryB.ownerTaskId, 'phaseA ordinary B missing')
    runtime.activateTab(taskTab.id)

    await runtime.getSession().cookies.set({
      url: baseUrl + '/',
      name: 'h010_profile_cookie',
      value: 'h010-profile-synthetic-value',
      // A cookie without expirationDate is a session cookie and is not
      // required to survive Chromium process shutdown. H010 is proving the
      // dedicated persistent profile boundary, so use a persistent cookie.
      expirationDate: Math.floor(Date.now() / 1000) + 4 * 60 * 60
    })
    const phaseACookies = await runtime.getSession().cookies.get({ name: 'h010_profile_cookie' })
    assert(
      phaseACookies.some(cookie => cookie.value === 'h010-profile-synthetic-value'),
      'phaseA persistent Chromium profile cookie missing before shutdown'
    )
    if (typeof runtime.getSession().flushStorageData === 'function') {
      await runtime.getSession().flushStorageData()
    }
    await sleep(150)

    const saved = composite()
    assert(saved.tabs.length === 3, 'phaseA expected three logical tabs')
    assert(saved.tabs[0].id === ordinaryA.id, 'phaseA ordinary A order mismatch')
    assert(saved.tabs[1].id === taskTab.id, 'phaseA task order mismatch')
    assert(saved.tabs[2].id === ordinaryB.id, 'phaseA ordinary B order mismatch')
    assert(saved.activeTabId === taskTab.id, 'phaseA task should be logical active')
    assert(saved.tabs[0].safeUrl === baseUrl + '/customers/482913', 'phaseA ordinary A safe URL mismatch')
    assert(saved.tabs[1].safeUrl === baseUrl + '/task', 'phaseA task safe URL mismatch')
    assert(saved.tabs[2].safeUrl === null, 'phaseA encoded pseudo-query must fail closed')
    assert(saved.tabs.every((tab: { safeTitle: unknown }) => tab.safeTitle === null), 'phaseA durable title leaked')

    const raw = serializedComposite()
    for (const forbidden of [
      'h010-query-secret',
      'h010-fragment-secret',
      'token=12345',
      'Recovery code 482913',
      'OTP 482913',
      'h010-profile-synthetic-value',
      'WebContents',
      'processId'
    ]) {
      assert(!raw.includes(forbidden), 'phaseA durable composite leaked ' + forbidden)
    }

    const evidence = {
      pid: process.pid,
      ordinaryAId: ordinaryA.id,
      taskTabId: taskTab.id,
      ordinaryBId: ordinaryB.id,
      taskId
    }
    fs.writeFileSync(path.join(home, 'h010-phase-a.json'), JSON.stringify(evidence, null, 2), 'utf8')
    console.log('H010_PHASE_A_PASS', JSON.stringify(evidence))
    await shutdown(win)
  }

  async function phaseB() {
    const evidencePath = path.join(home, 'h010-phase-a.json')
    assert(fs.existsSync(evidencePath), 'phaseB missing phase A evidence')
    const previous = JSON.parse(fs.readFileSync(evidencePath, 'utf8'))
    assert(previous.pid !== process.pid, 'phaseB reused phase A OS PID')

    const state = runtime.ensure()
    assert(state.tabs.length === 2, 'phaseB task page must remain lazy')
    assert(state.tabs[0].id === previous.ordinaryAId, 'phaseB ordinary A id/order mismatch')
    assert(state.tabs[1].id === previous.ordinaryBId, 'phaseB ordinary B id/order mismatch')
    assert(state.tabs[0].url === baseUrl + '/customers/482913', 'phaseB ordinary A URL restore mismatch')
    assert(state.tabs[1].url === 'about:blank', 'phaseB unsafe ordinary B should restore about:blank')

    const task = runtime.listTasks().find(candidate => candidate.taskId === previous.taskId)
    assert(task, 'phaseB logical BrowserTask missing')
    assert(task.status === 'parked', 'phaseB restored task not parked')
    assert(task.recoveryState === 'restored', 'phaseB restored task recovery state mismatch')
    assert(state.tabs.filter(tab => tab.ownerTaskId === previous.taskId).length === 0, 'phaseB task page eager')

    const beforeShow = composite()
    assert(beforeShow.tabs.map((tab: { id: string }) => tab.id).join('|') === [previous.ordinaryAId, previous.taskTabId, previous.ordinaryBId].join('|'), 'phaseB structural order mismatch')
    assert(beforeShow.activeTabId === previous.taskTabId, 'phaseB logical task active selection lost')

    const cookies = await runtime.getSession().cookies.get({ name: 'h010_profile_cookie' })
    assert(cookies.some(cookie => cookie.value === 'h010-profile-synthetic-value'), 'phaseB Chromium profile cookie missing')
    assert(!serializedComposite().includes('h010-profile-synthetic-value'), 'phaseB profile data leaked into structural JSON')

    const win = makeWindow('H010 phase B')
    runtime.showTask(previous.taskId, win, { x: 0, y: 0, width: 900, height: 600 })
    let owned = runtime.state().tabs.filter(tab => tab.ownerTaskId === previous.taskId)
    assert(owned.length === 1, 'phaseB first show expected one task page')
    assert(owned[0].id === previous.taskTabId, 'phaseB task logical tab id changed')
    assert(runtime.state().tabs.map(tab => tab.id).join('|') === [previous.ordinaryAId, previous.taskTabId, previous.ordinaryBId].join('|'), 'phaseB live order mismatch')
    assert(runtime.state().activeTabId === previous.taskTabId, 'phaseB task did not become physical active')

    runtime.showTask(previous.taskId, win, { x: 0, y: 0, width: 900, height: 600 })
    owned = runtime.state().tabs.filter(tab => tab.ownerTaskId === previous.taskId)
    assert(owned.length === 1, 'phaseB second show duplicated task page')
    assert(owned[0].id === previous.taskTabId, 'phaseB second show changed task tab id')

    console.log('H010_PHASE_B_PASS', JSON.stringify({
      phaseAPid: previous.pid,
      phaseBPid: process.pid,
      ownerPageCountBefore: 0,
      ownerPageCountAfterFirstShow: 1,
      ownerPageCountAfterSecondShow: 1,
      profileStateSeparated: true
    }))
    await shutdown(win)
  }

  async function faultMode() {
    const taskId = 'h010-fault-task'
    const state = runtime.ensure()
    const ordinary = state.tabs[0]
    assert(ordinary, 'fault mode ordinary tab missing')
    const ordinaryContents = runtime.getWebContents(ordinary.id)
    assert(ordinaryContents, 'fault mode ordinary WebContents missing')

    const win = makeWindow('H010 fault mode')
    runtime.createTask({ taskId })
    runtime.showTask(taskId, win, { x: 0, y: 0, width: 900, height: 600 })
    assert(composite().browserTasks.tasks.find((task: { taskId: string }) => task.taskId === taskId)?.status === 'visible', 'fault mode seed state not durable')

    failNextRename = true
    let observedFailure = false
    try {
      runtime.parkTask(taskId)
    } catch (error) {
      observedFailure = String(error).includes('H010 simulated native rename failure')
    }
    assert(observedFailure, 'fault mode did not observe injected rename failure')
    assert(runtime.listTasks().find(task => task.taskId === taskId)?.status === 'parked', 'fault mode in-process task intent did not advance')
    assert(composite().browserTasks.tasks.find((task: { taskId: string }) => task.taskId === taskId)?.status === 'visible', 'fault mode failed rename changed durable file')

    await ordinaryContents.loadURL(baseUrl + '/after-failure')
    await sleep(100)
    const converged = composite()
    assert(converged.browserTasks.tasks.find((task: { taskId: string }) => task.taskId === taskId)?.status === 'parked', 'fault mode later session save regressed BrowserTask intent')
    assert(converged.tabs.find((tab: { id: string }) => tab.id === ordinary.id)?.safeUrl === baseUrl + '/after-failure', 'fault mode later session projection missing')

    console.log('H010_NATIVE_FAULT_CONVERGENCE_PASS', JSON.stringify({ pid: process.pid, taskId }))

    const destroyTaskId = 'h010-destroy-fault-task'
    runtime.createTask({ taskId: destroyTaskId })
    runtime.showTask(destroyTaskId, win, { x: 0, y: 0, width: 900, height: 600 })
    const destroyTab = runtime.state().tabs.find(tab => tab.ownerTaskId === destroyTaskId)
    assert(destroyTab, 'destroy fault mode task tab missing')
    const destroyContents = runtime.getWebContents(destroyTab.id)
    assert(destroyContents, 'destroy fault mode WebContents missing')
    await destroyContents.loadURL(baseUrl + '/task-destroy-stale')
    assert(composite().browserTasks.tasks.some((task: { taskId: string }) => task.taskId === destroyTaskId), 'destroy fault mode seed task not durable')

    failNextRename = true
    let observedDestroyFailure = false
    try {
      runtime.destroyTask(destroyTaskId)
    } catch (error) {
      observedDestroyFailure = String(error).includes('H010 simulated native rename failure')
    }
    assert(observedDestroyFailure, 'destroy fault mode did not observe injected rename failure')
    assert(!runtime.listTasks().some(task => task.taskId === destroyTaskId), 'destroy fault mode logical task survived in process')
    assert(destroyContents.isDestroyed(), 'destroy fault mode prior WebContents survived')
    assert(composite().browserTasks.tasks.some((task: { taskId: string }) => task.taskId === destroyTaskId), 'destroy fault mode failed rename changed durable file')

    await ordinaryContents.loadURL(baseUrl + '/after-destroy-failure')
    await sleep(100)
    const destroyConverged = composite()
    assert(!destroyConverged.browserTasks.tasks.some((task: { taskId: string }) => task.taskId === destroyTaskId), 'destroy fault mode later session save resurrected deleted task')

    runtime.createTask({ taskId: destroyTaskId })
    const recreated = runtime.state().tabs.filter(tab => tab.ownerTaskId === destroyTaskId)
    assert(recreated.length === 1, 'destroy fault mode recreation expected one task page')
    assert(recreated[0].id !== destroyTab.id, 'destroy fault mode recreation reused destroyed tab id')
    assert(recreated[0].url === 'about:blank', 'destroy fault mode recreation inherited stale destroyed URL')
    console.log('H010_NATIVE_DESTROY_FAILURE_CLEANUP_PASS', JSON.stringify({
      pid: process.pid,
      taskId: destroyTaskId,
      destroyedTabId: destroyTab.id,
      recreatedTabId: recreated[0].id
    }))
    runtime.destroyTask(destroyTaskId)

    await shutdown(win)
  }

  async function abrupt1() {
    const taskId = 'h010-abrupt-task'
    const state = runtime.ensure()
    const ordinary = state.tabs[0]
    const ordinaryContents = runtime.getWebContents(ordinary.id)
    assert(ordinaryContents, 'abrupt1 ordinary WebContents missing')
    await ordinaryContents.loadURL(baseUrl + '/abrupt')
    runtime.createTask({ taskId })
    const saved = composite()
    assert(saved.browserTasks.tasks.some((task: { taskId: string }) => task.taskId === taskId), 'abrupt1 task not durable before termination')
    fs.writeFileSync(path.join(home, 'h010-abrupt1.json'), JSON.stringify({ pid: process.pid, taskId, ordinaryId: ordinary.id }, null, 2), 'utf8')
    console.log('H010_ABRUPT_PHASE1_DURABLE', JSON.stringify({ pid: process.pid, taskId }))
    clearTimeout(timer)
    process.exit(17)
  }

  async function abrupt2() {
    const evidence = JSON.parse(fs.readFileSync(path.join(home, 'h010-abrupt1.json'), 'utf8'))
    assert(evidence.pid !== process.pid, 'abrupt2 reused prior PID')
    const state = runtime.ensure()
    assert(state.tabs.some(tab => tab.id === evidence.ordinaryId), 'abrupt2 ordinary logical tab missing')
    const task = runtime.listTasks().find(candidate => candidate.taskId === evidence.taskId)
    assert(task, 'abrupt2 logical task missing')
    assert(state.tabs.filter(tab => tab.ownerTaskId === evidence.taskId).length === 0, 'abrupt2 task page eager')
    const win = makeWindow('H010 abrupt phase B')
    runtime.showTask(evidence.taskId, win, { x: 0, y: 0, width: 900, height: 600 })
    assert(runtime.state().tabs.filter(tab => tab.ownerTaskId === evidence.taskId).length === 1, 'abrupt2 task page count mismatch')
    console.log('H010_ABRUPT_RESTART_PASS', JSON.stringify({ phase1Pid: evidence.pid, phase2Pid: process.pid }))
    await shutdown(win)
  }

  try {
    if (mode === 'phaseA') await phaseA()
    else if (mode === 'phaseB') await phaseB()
    else if (mode === 'fault') await faultMode()
    else if (mode === 'abrupt1') await abrupt1()
    else if (mode === 'abrupt2') await abrupt2()
    else throw new Error('unknown H010_MODE ' + mode)
    clearTimeout(timer)
    console.log('H010_MODE_PASS ' + mode)
    app.exit(0)
  } catch (error) {
    clearTimeout(timer)
    console.error('H010_PRODUCT_PATH_FAIL', JSON.stringify({
      pid: process.pid,
      mode,
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : null
    }))
    try { await runtime.destroy() } catch {}
    app.exit(1)
  }
}).catch(error => {
  clearTimeout(timer)
  console.error('H010_READY_OR_IMPORT_FAIL', error instanceof Error ? error.stack || error.message : String(error))
  app.exit(1)
})
`

fs.writeFileSync(harnessTs, harnessSource, 'utf8')
fs.writeFileSync(
  packageJson,
  JSON.stringify({ name: 'hermes-h010-native-browser-session-state', private: true, main: 'main.cjs' }, null, 2),
  'utf8'
)

console.log(
  'H010_PROBE_CONTEXT',
  JSON.stringify({
    head,
    expectedHead,
    electronExe,
    esbuildCli,
    platform: process.platform,
    osRelease: os.release(),
    node: process.version
  })
)

const pageServer = await startLocalPageServer()
try {
  console.log('\n=== H010_BUILD ===')
  await run(
    process.execPath,
    [
      esbuildCli,
      harnessTs,
      '--bundle',
      '--platform=node',
      '--format=cjs',
      '--target=node20',
      '--outfile=' + mainCjs,
      '--external:electron'
    ],
    { timeoutMs: 30000 }
  )

  if (!fs.existsSync(mainCjs) || fs.statSync(mainCjs).size < 1000) {
    throw new Error('H010 build returned success but main.cjs is missing or unexpectedly small')
  }

  const baseEnv = { ...process.env, H010_BASE_URL: pageServer.baseUrl }

  console.log('\n=== H010_CLEAN_RESTART_PHASE_A ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, H010_MODE: 'phaseA', HERMES_WORKSTATION_HOME: cleanStateRoot }
  })

  console.log('\n=== H010_CLEAN_RESTART_PHASE_B ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, H010_MODE: 'phaseB', HERMES_WORKSTATION_HOME: cleanStateRoot }
  })

  console.log('\n=== H010_NATIVE_FAILED_WRITE_CONVERGENCE ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, H010_MODE: 'fault', HERMES_WORKSTATION_HOME: faultStateRoot }
  })

  console.log('\n=== H010_ABRUPT_PHASE_A ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    allowedCodes: [17],
    env: { ...baseEnv, H010_MODE: 'abrupt1', HERMES_WORKSTATION_HOME: abruptStateRoot }
  })

  console.log('\n=== H010_ABRUPT_PHASE_B ===')
  await run(electronExe, [appDir], {
    timeoutMs: 30000,
    env: { ...baseEnv, H010_MODE: 'abrupt2', HERMES_WORKSTATION_HOME: abruptStateRoot }
  })

  console.log('\nH010_CLASSIFICATION=VALIDATED')
  console.log(
    'H010_CONCLUSION=Exact-SHA Windows/Electron BrowserSessionState passed two-process restart, lazy task ownership, durable title/URL boundaries, Chromium profile separation, native failed-write convergence, explicit-destroy failure cleanup, and abrupt restart recovery.'
  )
  process.exitCode = 0
} catch (error) {
  console.error('\nH010_CLASSIFICATION=FAILED_OR_REFORMULATE')
  console.error('H010_CONCLUSION=' + (error instanceof Error ? error.stack || error.message : String(error)))
  console.error('H010_TEMP_ROOT=' + tempRoot)
  process.exitCode = 1
} finally {
  await pageServer.close()
}
