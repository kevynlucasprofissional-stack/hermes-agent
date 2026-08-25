[CmdletBinding()]
param(
  [switch]$InstallDependencies,
  [switch]$SkipCorePatch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-NativeChecked {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [object[]]$Arguments = @()
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE: $Command $($Arguments -join ' ')"
  }
}

function Test-PythonCandidate {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [string[]]$Prefix = @()
  )

  try {
    $probeArgs = @()
    $probeArgs += $Prefix
    $probeArgs += @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    $out = & $Command @probeArgs 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return [pscustomobject]@{
      Command = $Command
      Prefix = $Prefix
      Version = [version]($out | Select-Object -Last 1)
    }
  }
  catch {
    return $null
  }
}

function Resolve-Python {
  if ($env:HERMES_PYTHON) {
    $candidate = Test-PythonCandidate -Command $env:HERMES_PYTHON
    if ($candidate) { return $candidate }
    throw "HERMES_PYTHON is set but could not be executed: $env:HERMES_PYTHON"
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($selector in @("-3.13", "-3.12", "-3.11")) {
      $candidate = Test-PythonCandidate -Command "py" -Prefix @($selector)
      if ($candidate) { return $candidate }
    }
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    $candidate = Test-PythonCandidate -Command "python"
    if ($candidate) { return $candidate }
  }

  throw "Python was not found. Hermes requires Python >=3.11,<3.14 for dependency installation. Install Python 3.13, 3.12, or 3.11 and retry."
}

$Python = Resolve-Python

function Invoke-HermesPython {
  param([object[]]$Arguments = @())

  $pythonArgs = @()
  $pythonArgs += $Python.Prefix
  $pythonArgs += $Arguments
  & $Python.Command @pythonArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed with exit code $LASTEXITCODE: $($Python.Command) $($pythonArgs -join ' ')"
  }
}

Write-Host "Hermes Workstation - initial install" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ("Python: {0} {1} ({2})" -f $Python.Command, ($Python.Prefix -join ' '), $Python.Version)
Write-Host ""

if (-not (Test-Path (Join-Path $Root ".git"))) {
  Write-Host "[WARN] .git was not found at the Hermes repository root. Base-version verification will be limited." -ForegroundColor Yellow
}

$IntegrationScript = Join-Path $PSScriptRoot "scripts\apply_core_integration.py"
$LockScript = Join-Path $PSScriptRoot "scripts\validate_lock.py"
$LicenseScript = Join-Path $PSScriptRoot "scripts\verify_licenses.py"

# Validate everything we can before mutating Hermes core. The previous bootstrap
# applied immediately; if a later anchor failed, the working tree could be left
# partially patched.
if (-not $SkipCorePatch) {
  Write-Host "[1/4] Validating Hermes integration anchors..." -ForegroundColor Cyan
  Invoke-HermesPython @($IntegrationScript, "--root", $Root, "--check")
} else {
  Write-Host "[1/4] Core patch skipped by request." -ForegroundColor Yellow
}

Write-Host "[2/4] Validating Workstation component lock..." -ForegroundColor Cyan
Invoke-HermesPython @($LockScript)

Write-Host "[3/4] Validating third-party license policy..." -ForegroundColor Cyan
Invoke-HermesPython @($LicenseScript)

if (-not $SkipCorePatch) {
  Write-Host "[4/4] Applying Hermes Workstation core integration..." -ForegroundColor Cyan
  Invoke-HermesPython @($IntegrationScript, "--root", $Root)
} else {
  Write-Host "[4/4] Core integration not modified." -ForegroundColor Yellow
}

if ($InstallDependencies) {
  if ($Python.Version -lt [version]"3.11.0" -or $Python.Version -ge [version]"3.14.0") {
    throw "Hermes dependency installation requires Python >=3.11,<3.14, but selected Python is $($Python.Version). Install/select Python 3.13, 3.12, or 3.11."
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
    Write-Host "Installing Python package in editable mode..." -ForegroundColor Cyan
    Invoke-HermesPython @("-m", "pip", "install", "-e", ".")

    Write-Host "Installing Node workspaces..." -ForegroundColor Cyan
    Invoke-NativeChecked -Command "npm" -Arguments @("ci")
  }
  finally {
    Pop-Location
  }
}
else {
  Write-Host ""
  Write-Host "Source integration is ready." -ForegroundColor Green
  Write-Host "Dependency installation was skipped."
  Write-Host "Run workstation\install.cmd -InstallDependencies when you want to build Desktop."
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  workstation\doctor.cmd"
Write-Host "  workstation\start.cmd"
