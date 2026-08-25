[CmdletBinding()]
param(
  [switch]$SkipPatch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallScript = Join-Path $PSScriptRoot "install.ps1"
$VenvRoot = Join-Path $Root ".venv"
$VenvScripts = Join-Path $VenvRoot "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"

if ($SkipPatch) {
  & $InstallScript -SkipCorePatch
} else {
  & $InstallScript
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js was not found. Hermes Desktop requires Node >=22.22.0; the repository .nvmrc selects Node 26."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm was not found. Install a compatible Node.js distribution and retry."
}

$nodeRaw = (& node -p "process.versions.node" 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not $nodeRaw) {
  throw "Could not determine the Node.js version."
}
$nodeVersion = [version]$nodeRaw
$minimumNode = [version]"22.22.0"
if ($nodeVersion -lt $minimumNode) {
  throw "Node $nodeVersion is below the Hermes Desktop minimum $minimumNode. Use the repository .nvmrc (Node 26) and retry."
}

if (-not (Test-Path $VenvPython)) {
  throw "Hermes Workstation Python environment is missing: $VenvPython. Run workstation\install.cmd -InstallDependencies first."
}

& $VenvPython -c "import hermes_cli, sys; print(sys.executable)" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Hermes Workstation .venv exists but cannot import hermes_cli. Rerun workstation\install.cmd -InstallDependencies."
}

# Put the repo-local Hermes runtime first so Desktop backend discovery resolves
# this checkout's hermes.exe/python instead of a global Python installation.
$env:VIRTUAL_ENV = $VenvRoot
$env:HERMES_PYTHON = $VenvPython
$env:PATH = "$VenvScripts;$env:PATH"

Push-Location $Root
try {
  Write-Host "Starting Hermes Desktop with Workstation Browser..." -ForegroundColor Cyan
  Write-Host "Python runtime: $VenvPython"
  Write-Host "Node runtime:   $nodeVersion"
  Write-Host ""
  Write-Host "Keep this terminal open while Hermes Desktop is running." -ForegroundColor DarkGray
  Write-Host "To stop the dev server later, press Ctrl+C once and answer Y/S if Windows asks to terminate the batch job." -ForegroundColor DarkGray
  Write-Host ""

  & npm run dev --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) {
    throw "Hermes Desktop exited with code ${LASTEXITCODE}."
  }
}
finally {
  Pop-Location
}
