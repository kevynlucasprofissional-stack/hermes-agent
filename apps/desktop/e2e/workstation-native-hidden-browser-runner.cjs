// Native Chromium smoke test with a hidden, nonfocusable Electron window.
// No OS keyboard/mouse automation and no production browser profile.
const {spawn} = require('node:child_process')
const path = require('node:path')

const executable = path.resolve(__dirname, '../node_modules/electron/dist/electron.exe')
const audit = path.join(__dirname, 'workstation-native-hidden-browser-audit.cjs')
const environment = {...process.env}
delete environment.ELECTRON_RUN_AS_NODE

const child = spawn(executable, [audit], {
  windowsHide: true,
  env: environment,
  stdio: ['ignore', 'pipe', 'pipe']
})
let stdout = ''
let stderr = ''
let finished = false
const watchdog = setTimeout(() => {
  if (!finished) {child.kill()}
}, 15000)

child.stdout.on('data', buffer => {stdout += buffer.toString()})
child.stderr.on('data', buffer => {stderr += buffer.toString()})
child.on('error', error => {
  console.error('NATIVE_AUDIT_SPAWN_ERROR=' + error.message)
  process.exitCode = 2
})
child.on('close', code => {
  finished = true
  clearTimeout(watchdog)
  const line = stdout.split(/\r?\n/).find(item => item.startsWith('HERMES_HIDDEN_NATIVE_AUDIT='))
  if (code !== 0 || !line) {
    console.error('NATIVE_AUDIT_FAILURE=' + JSON.stringify({exit:code, stdout:stdout.slice(-500), stderr:stderr.slice(-750)}))
    process.exitCode = 2
    return
  }
  const result = JSON.parse(line.slice('HERMES_HIDDEN_NATIVE_AUDIT='.length))
  if (!result.native || result.windowVisible || result.focusable || result.isFocused ||
      result.clicked !== 1 || result.input !== 'hermes-native-proof' ||
      result.active !== 'i' || !result.enter || result.scrolled <= 0 ||
      !result.profileTemp) {
    console.error('NATIVE_AUDIT_INVARIANT_FAILED=' + JSON.stringify(result))
    process.exitCode = 2
    return
  }
  console.log('NATIVE_HIDDEN_CHROMIUM_PASS=' + JSON.stringify(result))
})
