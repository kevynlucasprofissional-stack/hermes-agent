$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvRoot = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

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

    # Capture the native exit code BEFORE piping/selecting output. Windows
    # PowerShell 5.1 can otherwise leave LASTEXITCODE at -1 for a successful
    # native command that participates in a PowerShell pipeline.
    $raw = & $Name @CommandArgs 2>&1
    $exitCode = $LASTEXITCODE
    $out = $raw | Select-Object -First 1

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
    $args = @()
    $args += $Prefix
    $args += @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    $out = & $Command @args 2>$null
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
  Write-Host ("[OK] Bootstrap Python: {0} {1} ({2})" -f $Python.Command, ($Python.Prefix -join ' '), $Python.Version) -ForegroundColor Green
  if ($Python.Version -ge [version]"3.14.0") {
    Write-Host "[WARN] Python 3.14 can run bootstrap scripts, but Hermes dependency installation requires <3.14." -ForegroundColor Yellow
  }
} else {
  Write-Host "[MISSING] Bootstrap Python. Install Python 3.13, 3.12, or 3.11." -ForegroundColor Yellow
}

if (Test-Path $VenvPython) {
  try {
    $venvVersion = (& $VenvPython -c "import sys; print(sys.version.split()[0])" 2>$null | Select-Object -Last 1)
    $importProbe = & $VenvPython -c "import hermes_cli; print('ok')" 2>$null
    if ($LASTEXITCODE -eq 0 -and $importProbe) {
      Write-Host ("[OK] Workstation .venv: {0} ({1})" -f $VenvPython, $venvVersion) -ForegroundColor Green
    } else {
      Write-Host "[FAIL] Workstation .venv exists but cannot import hermes_cli." -ForegroundColor Red
    }
  } catch {
    Write-Host ("[FAIL] Workstation .venv: {0}" -f $_.Exception.Message) -ForegroundColor Red
  }
} else {
  Write-Host "[WARN] Workstation .venv is not installed yet. Run workstation\install.cmd -InstallDependencies." -ForegroundColor Yellow
}

try {
  $nodeRaw = (& node -p "process.versions.node" 2>$null).Trim()
  if ($nodeRaw) {
    $nodeVersion = [version]$nodeRaw
    $minimumNode = [version]"22.22.0"
    if ($nodeVersion -lt $minimumNode) {
      Write-Host ("[WARN] Node {0} is below Hermes Desktop minimum {1}." -f $nodeVersion, $minimumNode) -ForegroundColor Yellow
    } else {
      Write-Host ("[OK] Node satisfies Desktop minimum: {0}" -f $nodeVersion) -ForegroundColor Green
      if ($nodeVersion.Major -ne 26) {
        Write-Host ("[WARN] Repository .nvmrc selects Node 26; current Node is {0}. CI validates on Node 26." -f $nodeVersion) -ForegroundColor Yellow
      }
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
