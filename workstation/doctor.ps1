$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "Hermes Workstation Doctor" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""

function Show-CommandVersion($Name, $Args) {
  try {
    $out = & $Name $Args 2>&1 | Select-Object -First 1
    Write-Host ("[OK] {0}: {1}" -f $Name, $out) -ForegroundColor Green
  } catch {
    Write-Host ("[MISSING] {0}" -f $Name) -ForegroundColor Yellow
  }
}

Show-CommandVersion "git" "--version"
Show-CommandVersion "python" "--version"
Show-CommandVersion "node" "--version"
Show-CommandVersion "npm" "--version"

try {
  $nodeRaw = (& node -p "process.versions.node" 2>$null).Trim()
  if ($nodeRaw) {
    $nodeVersion = [version]$nodeRaw
    $minimumNode = [version]"22.22.0"
    if ($nodeVersion -lt $minimumNode) {
      Write-Host ("[WARN] Node {0} is below Hermes Desktop minimum {1}. The repo .nvmrc currently selects Node 26." -f $nodeVersion, $minimumNode) -ForegroundColor Yellow
    } else {
      Write-Host ("[OK] Node satisfies Desktop minimum: {0}" -f $nodeVersion) -ForegroundColor Green
    }
  }
} catch {
  Write-Host "[WARN] Could not validate Node minimum version" -ForegroundColor Yellow
}

try {
  python (Join-Path $PSScriptRoot "scripts\apply_core_integration.py") --root $Root --check
} catch {
  Write-Host "[FAIL] Core integration anchors" -ForegroundColor Red
}

try {
  python (Join-Path $PSScriptRoot "scripts\validate_lock.py")
} catch {
  Write-Host "[FAIL] components.lock.json" -ForegroundColor Red
}

try {
  python (Join-Path $PSScriptRoot "scripts\verify_licenses.py")
} catch {
  Write-Host "[FAIL] license policy" -ForegroundColor Red
}

$ProfilePath = Join-Path $env:LOCALAPPDATA "HermesWorkstation\Browser\User Data"
Write-Host ("Browser profile: {0}" -f $ProfilePath)
Write-Host ""
git -C $Root status --short
