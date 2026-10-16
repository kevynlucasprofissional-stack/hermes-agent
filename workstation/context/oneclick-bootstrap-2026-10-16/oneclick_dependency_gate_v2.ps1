# DRAFT IMPLEMENTATION ASSET — copy to workstation/scripts/oneclick_dependency_gate.ps1
# 2026-10-16 / D-046. NOT DEPLOYED OR NATIVE-WINDOWS-QUALIFIED.
[CmdletBinding()]
param(
  [ValidateSet("Check","Record","CheckPython","CheckNode","RecordPython","RecordNode")]
  [string]$Action = "Check"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$RuntimeRoot = if ($env:HERMES_WORKSTATION_HOME -and $env:HERMES_WORKSTATION_HOME.Trim()) {
  [System.IO.Path]::GetFullPath($env:HERMES_WORKSTATION_HOME.Trim())
} elseif ($env:LOCALAPPDATA) {
  Join-Path $env:LOCALAPPDATA "HermesWorkstation"
} else {
  Join-Path $HOME ".hermes-workstation"
}
$StampDir = Join-Path $RuntimeRoot "Runtime"
$PythonStamp = Join-Path $StampDir "oneclick-python-dependencies.sha256"
$NodeStamp = Join-Path $StampDir "oneclick-node-dependencies.sha256"

function Invoke-Probe {
  param([string]$Command, [string[]]$Arguments)
  # Windows PowerShell 5.1 turns some native stderr messages into ErrorRecords.
  # Do not let a successful uv check ("Checked N packages ...") become a failure.
  $savedPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = @(& $Command @Arguments 2>&1)
    $nativeExit = $LASTEXITCODE  # Capture before any pipeline.
  } finally {
    $ErrorActionPreference = $savedPreference
  }
  return [pscustomobject]@{
    ExitCode = $nativeExit
    Output = (@($output | ForEach-Object { [string]$_ }) -join "`n").Trim()
  }
}

function Get-Fingerprint {
  param([string[]]$Patterns, [string[]]$EnvironmentFacts)
  $parts = New-Object System.Collections.Generic.List[string]
  foreach ($pattern in $Patterns) {
    $matches = @(Get-ChildItem -Path (Join-Path $Root $pattern) -File -ErrorAction SilentlyContinue)
    if ($matches.Count -eq 0) { $parts.Add("MISSING:$pattern") }
    foreach ($file in ($matches | Sort-Object FullName)) {
      $relative = $file.FullName.Substring($Root.Length).TrimStart('\')
      $parts.Add("$relative=$((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash)")
    }
  }
  foreach ($fact in $EnvironmentFacts) { $parts.Add($fact) }
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($parts -join "`n"))
    return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '')
  } finally { $sha.Dispose() }
}

function Get-PythonFingerprint {
  if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) { return $null }
  $versionProbe = Invoke-Probe $VenvPython @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
  if ($versionProbe.ExitCode -ne 0 -or -not $versionProbe.Output) { return $null }
  return Get-Fingerprint @("pyproject.toml","uv.lock",".python-version") @("venv-python=$($versionProbe.Output)")
}

function Get-NodeFingerprint {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return $null }
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { return $null }
  $nodeProbe = Invoke-Probe "node" @("--version")
  $npmProbe = Invoke-Probe "cmd.exe" @("/d", "/c", "npm --version 2>NUL")
  if ($nodeProbe.ExitCode -ne 0 -or $npmProbe.ExitCode -ne 0) { return $null }
  return Get-Fingerprint @(
    "package.json","package-lock.json",".npmrc",".nvmrc",
    "apps/*/package.json","ui-tui/package.json",
    "ui-tui/packages/*/package.json","web/package.json","tests-js/package.json"
  ) @("node=$($nodeProbe.Output)","npm=$($npmProbe.Output)")
}

function Test-PythonHealth {
  if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    Write-Host "[deps:python] Missing virtual environment interpreter."
    return $false
  }
  $probe = Invoke-Probe $VenvPython @(
    "-c",
    "import sys, hermes_cli, httpx, pydantic; from importlib.metadata import version; assert sys.version_info[:2] == (3,14); version('hermes-agent')"
  )
  if ($probe.ExitCode -ne 0) {
    Write-Host "[deps:python] Runtime import/version failed: $($probe.Output)"
    return $false
  }
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    $graph = Invoke-Probe "uv" @("pip","check","--python",$VenvPython)
  } else {
    $graph = Invoke-Probe $VenvPython @("-m","pip","check")
  }
  if ($graph.ExitCode -ne 0) {
    Write-Host "[deps:python] Dependency graph invalid (exit $($graph.ExitCode)): $($graph.Output)"
    return $false
  }
  return $true
}

function Test-NodeHealth {
  $required = @(
    (Join-Path $Root "node_modules\.bin\vite.cmd"),
    (Join-Path $Root "node_modules\.bin\tsc.cmd"),
    (Join-Path $Root "node_modules\.bin\concurrently.cmd"),
    (Join-Path $Root "node_modules\.package-lock.json")
  )
  foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      Write-Host "[deps:node] Missing: $path"
      return $false
    }
  }
  $electronRoots = @(
    (Join-Path $Root "node_modules\electron"),
    (Join-Path $Root "apps\desktop\node_modules\electron")
  )
  $electronReady = $false
  foreach ($dir in $electronRoots) {
    if (Test-Path -LiteralPath (Join-Path $dir "dist\electron.exe") -PathType Leaf) {
      $electronReady = $true
      break
    }
  }
  if (-not $electronReady) {
    Write-Host "[deps:node] Electron executable is missing."
    return $false
  }
  # Key imports required by the desktop dev runtime; not a complete npm audit.
  $probe = Invoke-Probe "node" @(
    "-e",
    "for (const x of ['react','vite','typescript','concurrently']) require.resolve(x, { paths: [process.cwd()] });"
  )
  if ($probe.ExitCode -ne 0) {
    Write-Host "[deps:node] Desktop module resolution failed: $($probe.Output)"
    return $false
  }
  return $true
}

function Test-Stamped {
  param([string]$Stamp, [string]$Fingerprint)
  if (-not $Fingerprint) { return $false }
  if (-not (Test-Path -LiteralPath $Stamp -PathType Leaf)) { return $false }
  return ([System.IO.File]::ReadAllText($Stamp).Trim() -eq $Fingerprint)
}

function Set-Stamp {
  param([string]$Path, [string]$Fingerprint)
  if (-not $Fingerprint) { throw "Cannot record an empty dependency fingerprint." }
  New-Item -ItemType Directory -Force -Path $StampDir | Out-Null
  # Stamp write is only after a passing component health check.
  [System.IO.File]::WriteAllText($Path, $Fingerprint)
}

try {
  # Fingerprint evaluation and health checks are independent per domain.
  $checkPython = $Action -in @("Check","CheckPython")
  $checkNode = $Action -in @("Check","CheckNode")
  $recordPython = $Action -in @("Record","RecordPython")
  $recordNode = $Action -in @("Record","RecordNode")

  if ($checkPython -or $recordPython) {
    $pythonFingerprint = Get-PythonFingerprint
    if (-not $pythonFingerprint -or -not (Test-PythonHealth)) { exit 1 }
    if ($checkPython -and -not (Test-Stamped $PythonStamp $pythonFingerprint)) {
      Write-Host "[deps:python] Fingerprint missing or changed."
      exit 1
    }
  }
  if ($checkNode -or $recordNode) {
    $nodeFingerprint = Get-NodeFingerprint
    if (-not $nodeFingerprint -or -not (Test-NodeHealth)) { exit 1 }
    if ($checkNode -and -not (Test-Stamped $NodeStamp $nodeFingerprint)) {
      Write-Host "[deps:node] Fingerprint missing or changed."
      exit 1
    }
  }
  if ($recordPython) {
    Set-Stamp $PythonStamp $pythonFingerprint
    Write-Host "[deps:python] Healthy install recorded."
  }
  if ($recordNode) {
    Set-Stamp $NodeStamp $nodeFingerprint
    Write-Host "[deps:node] Healthy install recorded."
  }
  if ($Action -eq "Check") { Write-Host "[deps] Cached Python and Node dependencies healthy." }
  if ($Action -eq "CheckPython") { Write-Host "[deps:python] Cached dependencies healthy." }
  if ($Action -eq "CheckNode") { Write-Host "[deps:node] Cached dependencies healthy." }
  exit 0
} catch {
  Write-Host "[deps] Validation error: $($_.Exception.Message)"
  exit 1
}
