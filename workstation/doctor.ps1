$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "Hermes Workstation Doctor" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""

function Show-CommandVersion {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string[]]$CommandArgs = @()
  )
  try {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
      Write-Host ("[MISSING] {0}" -f $Name) -ForegroundColor Yellow
      return
    }
    $out = & $Name @CommandArgs 2>&1 | Select-Object -First 1
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
      Write-Host ("[OK] {0}: {1}" -f $Name, $out) -ForegroundColor Green
    } else {
      Write-Host ("[FAIL] {0}: exit {1}" -f $Name, $exitCode) -ForegroundColor Red
    }
  } catch {
    Write-Host ("[FAIL] {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
  }
}

function Test-PythonCandidate($Command, $Prefix) {
  try {
    $probeArgs = @()
    $probeArgs += $Prefix
    $probeArgs += @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    $out = & $Command @probeArgs 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return [pscustomobject]@{
      Command = $Command
      Prefix = @($Prefix)
      Version = [version]($out | Select-Object -Last 1)
    }
  } catch {
    return $null
  }
}

function Resolve-Python {
  if ($env:HERMES_PYTHON) {
    $candidate = Test-PythonCandidate $env:HERMES_PYTHON @()
    if ($candidate) { return $candidate }
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($selector in @("-3.13", "-3.12", "-3.11")) {
      $candidate = Test-PythonCandidate "py" @($selector)
      if ($candidate) { return $candidate }
    }
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return Test-PythonCandidate "python" @()
  }
  return $null
}

function Invoke-PythonCheck($Python, $Script, $Arguments) {
  if (-not $Python) {
    Write-Host ("[FAIL] {0}: Python unavailable" -f (Split-Path $Script -Leaf)) -ForegroundColor Red
    return
  }
  $pythonArgs = @()
  $pythonArgs += $Python.Prefix
  $pythonArgs += $Script
  $pythonArgs += $Arguments
  & $Python.Command @pythonArgs
  if ($LASTEXITCODE -ne 0) {
    Write-Host ("[FAIL] {0}: exit {1}" -f (Split-Path $Script -Leaf), $LASTEXITCODE) -ForegroundColor Red
  }
}

Show-CommandVersion -Name "git" -CommandArgs @("--version")
Show-CommandVersion -Name "node" -CommandArgs @("--version")
Show-CommandVersion -Name "npm" -CommandArgs @("--version")

$Python = Resolve-Python
if ($Python) {
  Write-Host ("[OK] Python: {0} {1} ({2})" -f $Python.Command, ($Python.Prefix -join ' '), $Python.Version) -ForegroundColor Green
  if ($Python.Version -ge [version]"3.14.0") {
    Write-Host "[WARN] Python 3.14 can run Workstation bootstrap scripts, but Hermes dependency installation currently requires <3.14." -ForegroundColor Yellow
  }
} else {
  Write-Host "[MISSING] Python. Install Python 3.13, 3.12, or 3.11." -ForegroundColor Yellow
}

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

Invoke-PythonCheck $Python (Join-Path $PSScriptRoot "scripts\apply_core_integration.py") @("--root", $Root, "--check")
Invoke-PythonCheck $Python (Join-Path $PSScriptRoot "scripts\validate_lock.py") @()
Invoke-PythonCheck $Python (Join-Path $PSScriptRoot "scripts\verify_licenses.py") @()

if ($env:LOCALAPPDATA) {
  $ProfilePath = Join-Path $env:LOCALAPPDATA "HermesWorkstation\Browser\User Data"
  Write-Host ("Browser profile: {0}" -f $ProfilePath)
}

Write-Host ""
try {
  git -C $Root status --short
} catch {
  Write-Host "[WARN] Could not read git status." -ForegroundColor Yellow
}
