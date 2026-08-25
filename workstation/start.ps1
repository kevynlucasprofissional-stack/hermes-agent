[CmdletBinding()]
param(
  [switch]$SkipPatch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallScript = Join-Path $PSScriptRoot "install.ps1"

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

Push-Location $Root
try {
  Write-Host "Starting Hermes Desktop with Workstation Browser..." -ForegroundColor Cyan
  & npm run dev --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) {
    throw "Hermes Desktop exited with code $LASTEXITCODE."
  }
}
finally {
  Pop-Location
}
