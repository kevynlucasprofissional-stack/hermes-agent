[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$bootstrapStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SetupScript = Join-Path $Root "setup-hermes.ps1"
$DependencyGate = Join-Path $PSScriptRoot "oneclick_dependency_gate.ps1"
$InstallScript = Join-Path $Root "workstation\install.ps1"
$DoctorScript = Join-Path $Root "workstation\doctor.ps1"
$StartScript = Join-Path $Root "workstation\start.ps1"

$RuntimeRoot = if ($env:HERMES_WORKSTATION_HOME -and $env:HERMES_WORKSTATION_HOME.Trim()) {
  [System.IO.Path]::GetFullPath($env:HERMES_WORKSTATION_HOME.Trim())
} elseif ($env:LOCALAPPDATA) {
  Join-Path $env:LOCALAPPDATA "HermesWorkstation"
} else {
  Join-Path $HOME ".hermes-workstation"
}
$UpstreamStamp = Join-Path $RuntimeRoot "Runtime\oneclick-upstream-inputs.sha256"

function Get-UpstreamFingerprint {
  # The upstream PM owns its tools and Python dependency graph.
  $inputs = @(
    "pm\lock.json", "pyproject.toml", "uv.lock", ".python-version",
    ".nvmrc", "setup-hermes.ps1", "pm\cli.py", "pm\environments.py",
    "workstation\scripts\oneclick_bootstrap.ps1"
  )
  $parts = New-Object System.Collections.Generic.List[string]
  foreach ($relative in $inputs) {
    $file = Join-Path $Root $relative
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
      throw "Required upstream bootstrap input is missing: $relative"
    }
    $parts.Add("$relative=$((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash)")
  }
  $bytes = [Text.Encoding]::UTF8.GetBytes(($parts -join [char]10))
  $sha = [Security.Cryptography.SHA256]::Create()
  try { return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace("-", "") }
  finally { $sha.Dispose() }
}

function Test-Python314 {
  param([string]$Path)
  if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
  try {
    $output = & $Path -I -c "import sys; print('ok' if sys.version_info[:2] == (3,14) else 'bad')" 2>$null
    return ($LASTEXITCODE -eq 0 -and ($output | Select-Object -Last 1) -eq "ok")
  } catch { return $false }
}

function Find-PmPython {
  # A committed PM interpreter takes precedence over a global Python alias.
  foreach ($candidate in @(
    (Join-Path $Root "venv\Scripts\python.exe"),
    (Join-Path $Root ".venv\Scripts\python.exe")
  )) {
    if (Test-Python314 $candidate) { return $candidate }
  }

  # The upstream setup stages SHA-pinned uv and a managed Python.
  $lock = Get-Content -LiteralPath (Join-Path $Root "pm\lock.json") -Raw | ConvertFrom-Json
  $nativeArch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
  $arch = if ($nativeArch -eq "ARM64") { "arm64" } else { "x64" }
  $target = "win32-$arch"
  $store = if ($env:HERMES_RUNTIME_DIR) { $env:HERMES_RUNTIME_DIR } else { Join-Path $HOME ".hermes\tools" }
  $uv = Join-Path $store "uv-$($lock.packages.uv.version)-$target\uv.exe"
  if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) { return $null }
  $pyVersion = [string]$lock.packages.python.version
  $pyMinor = ($pyVersion -split "\+")[0] -replace "^(\d+\.\d+).*", '$1'
  $triple = if ($arch -eq "arm64") { "aarch64" } else { "x86_64" }
  try {
    $resolved = & $uv python find --managed-python "cpython-$pyMinor-windows-$triple-none" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $path = ([string]($resolved | Select-Object -Last 1)).Trim()
    if (Test-Python314 $path) { return $path }
  } catch { }
  return $null
}

function Import-PmEnvironment {
  param([string]$Python)
  # Do not hide the underlying error when the PM environment cannot be loaded.
  $output = & $Python -m pm.environments 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0 -or -not $output) {
    Write-Host "[bootstrap] PM environment export failed (exit $exitCode)." -ForegroundColor Yellow
    foreach ($line in @($output | Select-Object -Last 6)) {
      Write-Host "  $line" -ForegroundColor Yellow
    }
    return $false
  }
  try {
    $composed = ($output -join [char]10) | ConvertFrom-Json
    foreach ($property in $composed.PSObject.Properties) {
      if ($null -ne $property.Value) {
        [Environment]::SetEnvironmentVariable($property.Name, [string]$property.Value, "Process")
      }
    }
  } catch {
    Write-Host "[bootstrap] Invalid PM environment export: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
  return $true
}

function Enter-UpstreamEnvironment {
  $python = Find-PmPython
  if (-not $python) {
    Write-Host "[bootstrap] Pinned Python 3.14 could not be located after setup." -ForegroundColor Yellow
    return $false
  }
  try {
    # Use upstream's own PATH composer; do not write global PATH or registry.
    if (-not (Import-PmEnvironment -Python $python)) { return $false }
    $env:HERMES_PYTHON = $python
    # -I would discard the composed PYTHONPATH and falsely reject healthy PM
    # generations. Probe real pinned runtime dependencies, not just sources.
    $pyCheck = & $python -c "import hermes_cli, httpx, pydantic; from importlib.metadata import version; version('hermes-agent'); print('ok')" 2>&1
    $pyExitCode = $LASTEXITCODE
    if ($pyExitCode -ne 0 -or ($pyCheck | Select-Object -Last 1) -ne "ok") {
      Write-Host "[bootstrap] PM Python runtime import check failed (exit $pyExitCode)." -ForegroundColor Yellow
      foreach ($line in @($pyCheck | Select-Object -Last 6)) {
        Write-Host "  $line" -ForegroundColor Yellow
      }
      return $false
    }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
      Write-Host "[bootstrap] Node.js is missing from the PM PATH." -ForegroundColor Yellow
      return $false
    }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
      Write-Host "[bootstrap] npm is missing from the PM PATH." -ForegroundColor Yellow
      return $false
    }
    $nodeOut = & node -p "process.versions.node" 2>$null
    $nodeExitCode = $LASTEXITCODE
    if ($nodeExitCode -ne 0 -or -not $nodeOut) {
      Write-Host "[bootstrap] Node.js version check failed (exit $nodeExitCode)." -ForegroundColor Yellow
      return $false
    }
    $nodeVersion = [version]([string]($nodeOut | Select-Object -Last 1))
    if ($nodeVersion -lt [version]"22.22.0") {
      Write-Host "[bootstrap] Node $nodeVersion is older than required 22.22.0." -ForegroundColor Yellow
      return $false
    }
    $npmOut = & cmd.exe /d /c "npm --version 2>NUL"
    $npmExitCode = $LASTEXITCODE
    if ($npmExitCode -ne 0 -or -not $npmOut) {
      Write-Host "[bootstrap] npm version check failed (exit $npmExitCode)." -ForegroundColor Yellow
      return $false
    }

    # Upstream deliberately treats Git as optional: a default PM install does
    # not provision it. On a fresh Windows machine GitHub Desktop's embedded
    # Git is usually not on PATH, while Workstation's strict doctor requires it.
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCommand) {
      Write-Host "[bootstrap] Git is missing; installing the pinned PortableGit via Hermes PM..." -ForegroundColor Cyan
      & $python -m pm.cli install git
      $gitInstallExitCode = $LASTEXITCODE
      if ($gitInstallExitCode -ne 0) {
        Write-Host "[bootstrap] Pinned Git installation failed (exit $gitInstallExitCode)." -ForegroundColor Yellow
        return $false
      }
      # Newly installed tool directories are not inherited by the parent
      # PowerShell automatically. Re-compose PATH from PM's recorded facts.
      if (-not (Import-PmEnvironment -Python $python)) { return $false }
      $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    }
    if (-not $gitCommand) {
      Write-Host "[bootstrap] Git remains unavailable after PM activation." -ForegroundColor Yellow
      return $false
    }
    $gitOut = & git --version 2>$null
    $gitExitCode = $LASTEXITCODE
    if ($gitExitCode -ne 0 -or -not $gitOut) {
      Write-Host "[bootstrap] Git version check failed (exit $gitExitCode)." -ForegroundColor Yellow
      return $false
    }

    Write-Host "[bootstrap] Python 3.14, Node $nodeVersion, npm and Git ready." -ForegroundColor Green
    return $true
  } catch {
    Write-Host "[bootstrap] Existing upstream environment not usable: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
}

function Invoke-WithWorkstationInstallLock {
  param([scriptblock]$ActionBlock)
  $lockDir = Join-Path $RuntimeRoot "Runtime"
  New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
  $lockFile = Join-Path $lockDir "oneclick-install.lock"
  $timeoutSeconds = 300
  $startTime = [DateTime]::UtcNow
  $lockStream = $null
  while ($true) {
    try {
      $lockStream = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
      break
    } catch [System.IO.IOException] {
      if (([DateTime]::UtcNow - $startTime).TotalSeconds -ge $timeoutSeconds) {
        throw "Timed out waiting for concurrent Hermes Work install/repair lock to be released ($lockFile)."
      }
      Write-Host "[bootstrap] Another instance is currently modifying dependencies; waiting for lock..." -ForegroundColor Yellow
      Start-Sleep -Seconds 2
    }
  }
  try {
    & $ActionBlock
  } finally {
    if ($lockStream) {
      $lockStream.Dispose()
    }
  }
}

function Invoke-Step {
  param([string]$Name, [string]$Script, [string[]]$Arguments = @())
  Write-Host ""
  Write-Host $Name -ForegroundColor Cyan
  # Child PowerShell isolates exit/terminating errors and forwards the exact
  # exit status without losing the parent's PM-composed process environment.
  & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $Script @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Name failed (exit code $LASTEXITCODE)." }
}

try {
  Push-Location -LiteralPath $Root
  try {
    Write-Host "============================================================"
    Write-Host " HERMES WORK - ONE-CLICK BOOTSTRAP"
    Write-Host "============================================================"
    $fingerprint = Get-UpstreamFingerprint
    $stampMatches = $false
    if (Test-Path -LiteralPath $UpstreamStamp -PathType Leaf) {
      try { $stampMatches = ([IO.File]::ReadAllText($UpstreamStamp).Trim() -eq $fingerprint) }
      catch { Write-Host "[bootstrap] Previous install record unreadable; repairing." -ForegroundColor Yellow }
    }
    if (-not $stampMatches -or -not (Enter-UpstreamEnvironment)) {
      Invoke-WithWorkstationInstallLock {
        $recheckStampMatches = $false
        if (Test-Path -LiteralPath $UpstreamStamp -PathType Leaf) {
          try { $recheckStampMatches = ([IO.File]::ReadAllText($UpstreamStamp).Trim() -eq $fingerprint) } catch {}
        }
        if (-not $recheckStampMatches -or -not (Enter-UpstreamEnvironment)) {
          Write-Host "[0/4] Installing or repairing pinned upstream tools and Python dependencies..." -ForegroundColor Cyan
          Write-Host "      First run requires internet to fetch SHA256-verified archives."
          # Official upstream package-management path, including optional defaults.
          # setup-hermes.ps1 explicitly calls exit 0 under -RuntimeOnly. Running
          # it in-process would terminate THIS launcher before Electron starts.
          & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $SetupScript -RuntimeOnly
          if ($LASTEXITCODE -ne 0) { throw "Upstream package manager failed (exit code $LASTEXITCODE)." }
          if (-not (Enter-UpstreamEnvironment)) {
            throw "Upstream setup returned without a usable Python 3.14 / Node / npm / Git environment."
          }
          New-Item -ItemType Directory -Force -Path (Split-Path -Parent $UpstreamStamp) | Out-Null
          [IO.File]::WriteAllText($UpstreamStamp, $fingerprint)
          Write-Host "[bootstrap] Upstream installation fingerprint recorded." -ForegroundColor Green
        } else {
          Write-Host "[0/4] Upstream tools repaired by concurrent launch; skipping install." -ForegroundColor Green
        }
      }
    } else {
      Write-Host "[0/4] Upstream dependencies unchanged and healthy; skipping install." -ForegroundColor Green
    }

    # Keep PM's pinned tools on PATH, but never combine its selected Python
    # site-packages with Workstation's independent editable .venv. The latter
    # must resolve its own dependency graph; the checkout remains importable.
    $env:PYTHONPATH = $Root
    Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue

    Write-Host ""
    Write-Host "[1/4] Checking independent Workstation dependency fingerprints..." -ForegroundColor Cyan
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $DependencyGate -Action CheckPython
    $needsPythonInstall = ($LASTEXITCODE -ne 0)
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $DependencyGate -Action CheckNode
    $needsNodeInstall = ($LASTEXITCODE -ne 0)

    if ($needsPythonInstall -or $needsNodeInstall) {
      Invoke-WithWorkstationInstallLock {
        # Double-check inside the lock: another concurrent launch may have completed the repair
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $DependencyGate -Action CheckPython
        $needsPython = ($LASTEXITCODE -ne 0)
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $DependencyGate -Action CheckNode
        $needsNode = ($LASTEXITCODE -ne 0)

        if ($needsPython -or $needsNode) {
          $installArgs = @()
          if (-not $needsPython) { $installArgs += "-SkipPythonDependencies" }
          if (-not $needsNode) { $installArgs += "-SkipNodeDependencies" }
          Invoke-Step -Name "[2/4] Repairing only the unhealthy Workstation components..." -Script $InstallScript -Arguments $installArgs
          if ($needsPython) {
            Invoke-Step -Name "[deps:python] Recording successful install..." -Script $DependencyGate -Arguments @("-Action","RecordPython")
          }
          if ($needsNode) {
            Invoke-Step -Name "[deps:node] Recording successful install..." -Script $DependencyGate -Arguments @("-Action","RecordNode")
          }
        } else {
          Write-Host "[2/4] Dependencies already repaired by concurrent launch; proceeding." -ForegroundColor Green
        }
      }
    } else {
      Invoke-Step -Name "[2/4] Validating existing Workstation install..." -Script $InstallScript -Arguments @("-SkipDependencies")
    }
    Invoke-Step -Name "[3/4] Running strict Workstation doctor..." -Script $DoctorScript -Arguments @("-Strict")

    # [boot-perf] PowerShell bootstrap milestones: wall-clock timing from script
    # entry to Desktop launch. These are diagnostic logs only; the upstream
    # fingerprint includes this file so the first run after this change will
    # trigger an expected repair cycle (documented in commit message).
    Write-Host "[boot-perf] phase=bootstrap.pre_launch bootstrap_elapsed_ms=$($bootstrapStopwatch.ElapsedMilliseconds)"

    Invoke-Step -Name "[4/4] Starting Hermes Work..." -Script $StartScript -Arguments @("-SkipInstall")
    exit 0
  } finally {
    Pop-Location
  }
} catch {
  Write-Host ""
  Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "The existing environment was preserved. Review the error above and retry."
  exit 1
}
