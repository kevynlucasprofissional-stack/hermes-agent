[CmdletBinding()]
param(
  [switch]$InstallDependencies,
  [switch]$SkipCorePatch
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "Hermes Workstation — initial install" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not $SkipCorePatch) {
  python (Join-Path $PSScriptRoot "scripts\apply_core_integration.py") --root $Root
}

python (Join-Path $PSScriptRoot "scripts\validate_lock.py")
python (Join-Path $PSScriptRoot "scripts\verify_licenses.py")

if ($InstallDependencies) {
  Push-Location $Root
  try {
    Write-Host "Installing Python package in editable mode..."
    python -m pip install -e .
    Write-Host "Installing Node workspaces..."
    npm ci
  }
  finally {
    Pop-Location
  }
}
else {
  Write-Host ""
  Write-Host "Source integration is ready." -ForegroundColor Green
  Write-Host "Dependency installation was skipped."
  Write-Host "Run again with -InstallDependencies when you want to build Desktop."
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  .\workstation\doctor.ps1"
Write-Host "  .\workstation\start.ps1"
