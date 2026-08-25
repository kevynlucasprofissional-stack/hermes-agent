[CmdletBinding()]
param(
  # Kept for backwards compatibility. Dependency installation is now the normal path.
  [switch]$InstallDependencies,
  [switch]$SkipDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvRoot = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

function Invoke-NativeChecked {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [object[]]$Arguments = @()
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
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

  throw "Python was not found. Hermes requires Python >=3.11,<3.14. Install Python 3.13, 3.12, or 3.11 and retry."
}

$Python = Resolve-Python

function Invoke-HermesPython {
  param([object[]]$Arguments = @())

  $pythonArgs = @()
  $pythonArgs += $Python.Prefix
  $pythonArgs += $Arguments
  & $Python.Command @pythonArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed with exit code ${LASTEXITCODE}: $($Python.Command) $($pythonArgs -join ' ')"
  }
}

function Ensure-WorkstationVenv {
  if (Test-Path $VenvPython) {
    & $VenvPython -c "import sys; assert (3, 11) <= sys.version_info[:2] < (3, 14); print(sys.version.split()[0])" | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Existing Workstation venv is invalid or unsupported: $VenvRoot. Remove .venv and rerun install.cmd."
    }
    Write-Host "Using existing isolated Python environment: $VenvRoot" -ForegroundColor Green
    return
  }

  if ($Python.Version -lt [version]"3.11.0" -or $Python.Version -ge [version]"3.14.0") {
    throw "Hermes dependency installation requires Python >=3.11,<3.14, but selected Python is $($Python.Version)."
  }

  Write-Host "Creating isolated Python environment: $VenvRoot" -ForegroundColor Cyan
  Invoke-HermesPython -Arguments @("-m", "venv", $VenvRoot)
  if (-not (Test-Path $VenvPython)) {
    throw "Python venv creation completed without producing $VenvPython"
  }
}

function Get-CheckoutStatus {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return $null }
  $inside = (& git -C $Root rev-parse --is-inside-work-tree 2>$null | Select-Object -Last 1)
  if ($LASTEXITCODE -ne 0 -or $inside -ne "true") { return $null }
  $status = & git -C $Root status --porcelain=v1 --untracked-files=all 2>$null
  if ($LASTEXITCODE -ne 0) { throw "Could not read Git checkout status." }
  return @($status) -join "`n"
}

function Assert-CheckoutUnchanged {
  param([AllowNull()][string]$Before)
  if ($null -eq $Before) { return }
  $after = Get-CheckoutStatus
  if ($null -eq $after) { throw "Git checkout became unavailable during installation." }
  if ($after -ne $Before) {
    Write-Host "Checkout changed during install:" -ForegroundColor Red
    & git -C $Root status --short --untracked-files=all
    throw "Hermes Workstation install must not modify repository source or create unignored checkout artifacts."
  }
}

function Assert-NodeToolchain {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Hermes Desktop requires Node >=22.22.0; .nvmrc selects Node 26."
  }
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install a compatible Node.js distribution and retry."
  }

  $nodeRaw = (& node -p "process.versions.node" 2>$null).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $nodeRaw) { throw "Could not determine the Node.js version." }
  $nodeVersion = [version]$nodeRaw
  $minimumNode = [version]"22.22.0"
  if ($nodeVersion -lt $minimumNode) {
    throw "Node $nodeVersion is below the Hermes Desktop minimum $minimumNode."
  }
  if ($nodeVersion.Major -ne 26) {
    Write-Host ("[WARN] Node {0} satisfies the minimum, but .nvmrc selects Node 26. CI validates on Node 26." -f $nodeVersion) -ForegroundColor Yellow
  }
}

function Prepare-RuntimeDirectories {
  if ($env:HERMES_WORKSTATION_HOME -and $env:HERMES_WORKSTATION_HOME.Trim()) {
    $RuntimeHome = [System.IO.Path]::GetFullPath($env:HERMES_WORKSTATION_HOME.Trim())
  } elseif ($env:LOCALAPPDATA) {
    $RuntimeHome = Join-Path $env:LOCALAPPDATA "HermesWorkstation"
  } else {
    $RuntimeHome = Join-Path $HOME ".hermes-workstation"
  }
  New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeHome "Runtime") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeHome "Browser") | Out-Null
  Write-Host "Runtime home: $RuntimeHome"
}

Write-Host "Hermes Workstation - install" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ("Bootstrap Python: {0} {1} ({2})" -f $Python.Command, ($Python.Prefix -join ' '), $Python.Version)
Write-Host ""

$CheckoutBefore = Get-CheckoutStatus
if ($null -eq $CheckoutBefore) {
  Write-Host "[WARN] Git checkout could not be validated; source-cleanliness assertion is unavailable." -ForegroundColor Yellow
} else {
  Write-Host "[1/6] Git checkout detected; source state captured." -ForegroundColor Green
}

$IntegrationScript = Join-Path $PSScriptRoot "scripts\apply_core_integration.py"
$LockScript = Join-Path $PSScriptRoot "scripts\validate_lock.py"
$LicenseScript = Join-Path $PSScriptRoot "scripts\verify_licenses.py"

Write-Host "[2/6] Validating committed Workstation integration..." -ForegroundColor Cyan
Invoke-HermesPython -Arguments @($IntegrationScript, "--root", $Root, "--check")

Write-Host "[3/6] Validating Workstation component lock..." -ForegroundColor Cyan
Invoke-HermesPython -Arguments @($LockScript)

Write-Host "[4/6] Validating third-party license policy..." -ForegroundColor Cyan
Invoke-HermesPython -Arguments @($LicenseScript)

Assert-NodeToolchain

if (-not $SkipDependencies) {
  Write-Host "[5/6] Preparing isolated dependencies..." -ForegroundColor Cyan
  Ensure-WorkstationVenv
  Push-Location $Root
  try {
    Write-Host "Installing Hermes into .venv (editable mode)..." -ForegroundColor Cyan
    & $VenvPython -m pip install -e "."
    if ($LASTEXITCODE -ne 0) { throw "Hermes Python installation failed with exit code ${LASTEXITCODE}." }

    Write-Host "Installing Node workspaces from package-lock.json..." -ForegroundColor Cyan
    Invoke-NativeChecked -Command "npm" -Arguments @("ci")
  }
  finally {
    Pop-Location
  }
} else {
  Write-Host "[5/6] Dependency installation skipped by explicit request." -ForegroundColor Yellow
}

Write-Host "[6/6] Preparing runtime and running health checks..." -ForegroundColor Cyan
Prepare-RuntimeDirectories
if (-not $SkipDependencies) {
  & $VenvPython -c "import hermes_cli; print('OK: hermes_cli import')"
  if ($LASTEXITCODE -ne 0) { throw "Installed .venv cannot import hermes_cli." }
}
Assert-CheckoutUnchanged -Before $CheckoutBefore

Write-Host ""
Write-Host "Hermes Workstation install is healthy; committed source was not modified." -ForegroundColor Green
Write-Host "Next:"
Write-Host "  workstation\doctor.cmd"
Write-Host "  workstation\start.cmd"
