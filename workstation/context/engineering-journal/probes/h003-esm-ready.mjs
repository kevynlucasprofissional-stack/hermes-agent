#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const expectedBranch = 'impl4-browser-task-lifecycle'
const codeBearingAncestor = '1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70'
const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim()
const branch = execFileSync('git', ['branch', '--show-current'], { cwd: repoRoot, encoding: 'utf8' }).trim()
const head = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' }).trim()

if (branch !== expectedBranch) {
  console.error(`H003_PRECONDITION_FAIL wrong branch: ${branch}`)
  process.exit(2)
}

try {
  execFileSync('git', ['merge-base', '--is-ancestor', codeBearingAncestor, 'HEAD'], {
    cwd: repoRoot,
    stdio: 'ignore'
  })
} catch {
  console.error(`H003_PRECONDITION_FAIL ${codeBearingAncestor} is not an ancestor of ${head}`)
  process.exit(2)
}

const electronCandidates = [
  path.join(repoRoot, 'apps', 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
  path.join(repoRoot, 'node_modules', 'electron', 'dist', 'electron.exe')
]
const electronExe = electronCandidates.find(candidate => fs.existsSync(candidate))
if (!electronExe) {
  console.error('H003_PRECONDITION_FAIL electron.exe not found')
  for (const candidate of electronCandidates) console.error(`  checked: ${candidate}`)
  process.exit(2)
}

const root = path.join(os.tmpdir(), 'HermesImpl4H003EsmReady')
fs.rmSync(root, { recursive: true, force: true })
fs.mkdirSync(root, { recursive: true })

function writeApp(name, source) {
  const dir = path.join(root, name)
  fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify({
    name: `hermes-impl4-h003-${name}`,
    private: true,
    type: 'module',
    main: 'main.mjs'
  }, null, 2))
  fs.writeFileSync(path.join(dir, 'main.mjs'), source)
  return dir
}

const tlaApp = writeApp('tla', `
import { app, BrowserWindow } from 'electron'

const info = () => ({
  pid: process.pid,
  electron: process.versions.electron,
  node: process.versions.node,
  isReady: app.isReady()
})

console.log('H003_TLA_BOOT', JSON.stringify(info()))
const watchdog = setTimeout(() => {
  console.error('H003_TLA_INTERNAL_TIMEOUT', JSON.stringify(info()))
  process.exit(3)
}, 5000)

await app.whenReady()
clearTimeout(watchdog)
console.log('H003_TLA_READY', JSON.stringify(info()))
const win = new BrowserWindow({ width: 320, height: 180, show: false })
console.log('H003_TLA_WINDOW', JSON.stringify({ destroyed: win.isDestroyed() }))
win.destroy()
console.log('H003_TLA_PASS')
app.exit(0)
`)

const thenApp = writeApp('then', `
import { app, BrowserWindow } from 'electron'

const info = () => ({
  pid: process.pid,
  electron: process.versions.electron,
  node: process.versions.node,
  isReady: app.isReady()
})

console.log('H003_THEN_BOOT', JSON.stringify(info()))
const watchdog = setTimeout(() => {
  console.error('H003_THEN_INTERNAL_TIMEOUT', JSON.stringify(info()))
  process.exit(3)
}, 5000)

app.whenReady().then(() => {
  clearTimeout(watchdog)
  console.log('H003_THEN_READY', JSON.stringify(info()))
  const win = new BrowserWindow({ width: 320, height: 180, show: false })
  console.log('H003_THEN_WINDOW', JSON.stringify({ destroyed: win.isDestroyed() }))
  win.destroy()
  console.log('H003_THEN_PASS')
  app.exit(0)
}).catch(error => {
  clearTimeout(watchdog)
  console.error('H003_THEN_REJECTED', error?.stack || error?.message || String(error))
  process.exit(4)
})
`)

function killTree(pid) {
  if (!pid) return
  try {
    if (process.platform === 'win32') {
      execFileSync('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' })
    } else {
      process.kill(pid, 'SIGKILL')
    }
  } catch {
    // Best effort after a timeout; the result already records the timeout.
  }
}

function runCase(label, appDir) {
  return new Promise(resolve => {
    console.log(`\n=== ${label} ===`)
    console.log(`RUN ${electronExe} ${appDir}`)

    const child = spawn(electronExe, [appDir], {
      cwd: repoRoot,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: false,
      shell: false
    })

    let stdout = ''
    let stderr = ''
    let settled = false

    child.stdout.on('data', chunk => {
      const text = chunk.toString()
      stdout += text
      process.stdout.write(text)
    })
    child.stderr.on('data', chunk => {
      const text = chunk.toString()
      stderr += text
      process.stderr.write(text)
    })

    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      killTree(child.pid)
      console.error(`${label}_PARENT_TIMEOUT`)
      resolve({ label, outcome: 'timeout', code: null, stdout, stderr })
    }, 8000)

    child.on('error', error => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      console.error(`${label}_SPAWN_ERROR`, error.stack || error.message)
      resolve({ label, outcome: 'spawn_error', code: null, stdout, stderr: `${stderr}\n${error.stack || error.message}` })
    })

    child.on('exit', code => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ label, outcome: code === 0 ? 'pass' : 'fail', code, stdout, stderr })
    })
  })
}

console.log('H003_PROBE_CONTEXT', JSON.stringify({
  branch,
  head,
  codeBearingAncestor,
  electronExe,
  platform: process.platform,
  osRelease: os.release(),
  node: process.version,
  inheritedElectronEnv: Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.startsWith('ELECTRON_'))
  )
}))

const tla = await runCase('H003_TLA_CASE', tlaApp)
const thenCase = await runCase('H003_THEN_CASE', thenApp)

console.log('\nH003_RESULT_MATRIX', JSON.stringify({
  tla: { outcome: tla.outcome, code: tla.code },
  then: { outcome: thenCase.outcome, code: thenCase.code }
}))

if (tla.outcome !== 'pass' && thenCase.outcome === 'pass') {
  console.log('H003_CLASSIFICATION=VALIDATED')
  console.log('H003_CONCLUSION=In this exact environment, top-level await of app.whenReady stalls/fails while the non-blocking ESM whenReady callback reaches readiness.')
  process.exit(0)
}

if (tla.outcome === 'pass' && thenCase.outcome === 'pass') {
  console.log('H003_CLASSIFICATION=REFUTED')
  console.log('H003_CONCLUSION=Both ESM readiness forms work; V9 differs in another material way.')
  process.exit(0)
}

if (tla.outcome === 'pass' && thenCase.outcome !== 'pass') {
  console.log('H003_CLASSIFICATION=REFUTED_WITH_ANOMALY')
  console.log('H003_CONCLUSION=Top-level await works but the callback control failed; investigate the control/harness before BrowserTask.')
  process.exit(0)
}

console.log('H003_CLASSIFICATION=INCONCLUSIVE')
console.log('H003_CONCLUSION=Both ESM cases failed; the next hypothesis must target their shared ESM/bootstrap boundary.')
process.exit(0)
