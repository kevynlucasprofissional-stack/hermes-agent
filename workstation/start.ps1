[CmdletBinding()]
param(
  [switch]$SkipPatch
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $SkipPatch) {
  python (Join-Path $PSScriptRoot "scripts\apply_core_integration.py") --root $Root
}

Push-Location $Root
try {
  Write-Host "Starting Hermes Desktop with Workstation Browser..." -ForegroundColor Cyan
  npm run dev --workspace apps/desktop
}
finally {
  Pop-Location
}
