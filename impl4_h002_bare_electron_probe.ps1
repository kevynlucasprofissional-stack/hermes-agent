Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $RepoRoot

$ExpectedBranch = 'impl4-browser-task-lifecycle'
$ExpectedSha = '1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70'

git fetch origin | Out-Null
$branch = (git branch --show-current).Trim()
$head = (git rev-parse HEAD).Trim()
$originHead = (git rev-parse "origin/$ExpectedBranch").Trim()

Write-Host "=== H-002: BARE ELECTRON READY PROBE ==="
Write-Host "Branch: $branch"
Write-Host "HEAD: $head"
Write-Host "Origin: $originHead"

if ($branch -ne $ExpectedBranch -or $head -ne $ExpectedSha -or $originHead -ne $ExpectedSha) {
  throw 'Repository state changed. Stop and report branch/SHA.'
}

Write-Host ""
Write-Host "Inherited ELECTRON_* environment:"
$electronEnv = @(Get-ChildItem Env:ELECTRON* -ErrorAction SilentlyContinue)
if ($electronEnv.Count -eq 0) {
  Write-Host "(none)"
} else {
  $electronEnv | Sort-Object Name | Format-Table -AutoSize
}

$electronCandidates = @(
  (Join-Path $RepoRoot 'apps\desktop\node_modules\electron\dist\electron.exe'),
  (Join-Path $RepoRoot 'node_modules\electron\dist\electron.exe')
)
$electron = $electronCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $electron) {
  throw 'electron.exe not found.'
}

$ProbeRoot = Join-Path $env:TEMP 'HermesBareElectronReadyProbe'
if (Test-Path $ProbeRoot) {
  Remove-Item $ProbeRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ProbeRoot | Out-Null

$packageJson = @'
{
  "name": "hermes-bare-electron-ready-probe",
  "private": true,
  "main": "main.cjs"
}
'@

$main = @'
const { app, BrowserWindow } = require('electron')

const info = () => ({
  pid: process.pid,
  electron: process.versions.electron,
  node: process.versions.node,
  processType: process.type,
  isReady: app.isReady(),
  ELECTRON_RUN_AS_NODE: process.env.ELECTRON_RUN_AS_NODE ?? null,
  ELECTRON_NO_ATTACH_CONSOLE: process.env.ELECTRON_NO_ATTACH_CONSOLE ?? null,
  ELECTRON_ENABLE_LOGGING: process.env.ELECTRON_ENABLE_LOGGING ?? null
})

console.log('BARE_BOOT', JSON.stringify(info()))

app.on('will-finish-launching', () => {
  console.log('BARE_WILL_FINISH_LAUNCHING', JSON.stringify(info()))
})

app.on('ready', () => {
  console.log('BARE_READY_EVENT', JSON.stringify(info()))
})

const timeout = setTimeout(() => {
  console.error('BARE_READY_TIMEOUT', JSON.stringify(info()))
  app.exit(3)
}, 10000)

app.whenReady().then(() => {
  clearTimeout(timeout)
  console.log('BARE_WHEN_READY_RESOLVED', JSON.stringify(info()))

  const win = new BrowserWindow({
    width: 480,
    height: 240,
    show: false
  })

  console.log('BARE_BROWSER_WINDOW_CREATED', JSON.stringify({
    pid: process.pid,
    destroyed: win.isDestroyed()
  }))

  win.destroy()
  console.log('H002_RESULT=BARE_ELECTRON_READY_PASS')
  app.exit(0)
}).catch(error => {
  clearTimeout(timeout)
  console.error('BARE_WHEN_READY_REJECTED', error && (error.stack || error.message) || String(error))
  app.exit(4)
})
'@

Set-Content -Path (Join-Path $ProbeRoot 'package.json') -Value $packageJson -Encoding UTF8
Set-Content -Path (Join-Path $ProbeRoot 'main.cjs') -Value $main -Encoding UTF8

Write-Host ""
Write-Host "Electron: $electron"
Write-Host "Probe: $ProbeRoot"
Write-Host "Launching bare Electron; this must finish in <= 10 seconds..."
Write-Host ""

# Enable Chromium/Electron diagnostics only for this child launch.
$oldLogging = $env:ELECTRON_ENABLE_LOGGING
$env:ELECTRON_ENABLE_LOGGING = '1'

try {
  & $electron $ProbeRoot
  $code = $LASTEXITCODE
}
finally {
  if ($null -eq $oldLogging) {
    Remove-Item Env:ELECTRON_ENABLE_LOGGING -ErrorAction SilentlyContinue
  } else {
    $env:ELECTRON_ENABLE_LOGGING = $oldLogging
  }
}

Write-Host ""
Write-Host "Probe exit code: $code"

if ($code -eq 0) {
  Write-Host "H-002 CLASSIFICATION: REFUTADA"
  Write-Host "Bare Electron reaches ready; the prior stall is specific to the V9 harness/loader path, not general Electron startup."
  exit 0
}

if ($code -eq 3) {
  Write-Host "H-002 CLASSIFICATION: VALIDADA/PARCIAL"
  Write-Host "Bare Electron itself did not reach ready within 10 seconds. Investigate Electron/environment before touching BrowserTask."
  exit 3
}

Write-Host "H-002 CLASSIFICATION: INCONCLUSIVA"
Write-Host "Electron exited abnormally before the readiness question was answered."
exit $code
