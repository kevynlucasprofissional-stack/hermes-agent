// Dedicated Desktop/Backend/BrowserTask profile. Never mutate the active profile.
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')
const crypto = require('node:crypto')
const repo = path.resolve(__dirname, '../../..')
const app = path.join(repo, 'apps', 'desktop')
const electron = path.join(app, 'node_modules', 'electron', 'dist', 'electron.exe')
const fixture = 'http://127.0.0.1:18791/health'
const root = path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'),
  'HermesWorkstation', 'qualification', 'system1-desktop-e2e')
function fail(reason) { throw Error(reason) }
function assertFile(file) { if (!fs.existsSync(file)) fail('missing prerequisite: ' + file) }
async function run() {
  assertFile(electron)
  assertFile(path.join(app, 'dist', 'electron-main.mjs'))
  assertFile(path.join(repo, 'workstation', 'system1', 'browser_read_fastpath.py'))
  const response = await fetch(fixture, {signal:AbortSignal.timeout(3500)})
  if (!response.ok || (await response.json()).fixture !== 'hermes-system1-read-only') fail('fixture not ready')
  const manifest = path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'),
    'HermesWorkstation', 'qualification', 'system1-laya-project', 'active.json')
  assertFile(manifest)
  const state = JSON.parse(fs.readFileSync(manifest, 'utf8'))
  const python = path.join(path.dirname(manifest), state.generation, 'venv', 'Scripts', 'python.exe')
  assertFile(python)
  const id = 'e2e-' + new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0,14) + '-' +
    crypto.randomBytes(3).toString('hex')
  const sandbox = path.join(root, id)
  fs.mkdirSync(sandbox, {recursive:true})
  const output = path.join(sandbox, 'electron-stdout.log')
  const error = path.join(sandbox, 'electron-stderr.log')
  const fdout = fs.openSync(output, 'a'), fderr = fs.openSync(error, 'a')
  const env = {
    ...process.env,
    HERMES_HOME:path.join(sandbox,'hermes-home'),
    HERMES_RUNTIME_DIR:path.join(sandbox,'runtime'),
    HERMES_WORKSTATION_HOME:path.join(sandbox,'workstation'),
    HERMES_DESKTOP_USER_DATA_DIR:path.join(sandbox,'userdata'),
    HERMES_DESKTOP_ISOLATED_BACKEND:'1',
    HERMES_DESKTOP_HERMES_ROOT:repo,
    HERMES_DESKTOP_CWD:repo,
    HERMES_DESKTOP_PYTHON:python,
    HERMES_PYTHON:python,
    HERMES_DESKTOP_DEV_SERVER:'http://127.0.0.1:5174',
    HERMES_DESKTOP_CDP_PORT:'off',
    HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED:'1',
    HERMES_AI_CONTROL_FILE:path.join(sandbox,'userdata','ai-control-bridge.json'),
    HF_HUB_OFFLINE:'1',
    TRANSFORMERS_OFFLINE:'1',
    OMP_NUM_THREADS:'4',
  }
  delete env.ELECTRON_RUN_AS_NODE
  const child = spawn(electron, ['.', '--user-data-dir='+env.HERMES_DESKTOP_USER_DATA_DIR],
    { cwd:app, env, windowsHide:false, detached:true, stdio:['ignore',fdout,fderr] })
  child.on('error', err => {fs.appendFileSync(error, String(err))})
  const record = { id, createdAt:new Date().toISOString(), ownerPid:child.pid,
    sandbox, userData:env.HERMES_DESKTOP_USER_DATA_DIR, hermesHome:env.HERMES_HOME,
    workstationHome:env.HERMES_WORKSTATION_HOME,
    aiControlFile:env.HERMES_AI_CONTROL_FILE, isolatedBackend:true,
    fastpath:env.HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED,
    layaPython:python, fixture:'http://127.0.0.1:18791/unique', stdout:output, stderr:error }
  fs.writeFileSync(path.join(sandbox,'launch.json'),JSON.stringify(record,null,2))
  console.log('SYSTEM1_ISOLATED_LAUNCH='+JSON.stringify(record))
  child.unref()
  fs.closeSync(fdout);fs.closeSync(fderr)
}
run().catch(err => {console.error('SYSTEM1_ISOLATED_START_ERROR='+String(err.stack || err));process.exitCode=2})
