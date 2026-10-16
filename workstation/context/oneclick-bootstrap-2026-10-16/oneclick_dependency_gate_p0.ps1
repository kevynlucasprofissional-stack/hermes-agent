[CmdletBinding()]
param(
  [ValidateSet("Check", "Record")]
  [string]$Action = "Check"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$RuntimeRoot = if ($env:HERMES_WORKSTATION_HOME) {
  [System.IO.Path]::GetFullPath($env:HERMES_WORKSTATION_HOME)
} else {
  Join-Path $env:LOCALAPPDATA "HermesWorkstation"
}
$StampFile = Join-Path $RuntimeRoot "Runtime\oneclick-dependencies.sha256"

function Get-InstallFingerprint {
  $patterns = @(
    "package.json", "package-lock.json", ".npmrc", ".nvmrc",
    "pyproject.toml", "uv.lock",
    "apps/*/package.json", "ui-tui/package.json",
    "ui-tui/packages/*/package.json", "web/package.json",
    "tests-js/package.json"
  )
  $parts = New-Object System.Collections.Generic.List[string]
  foreach ($pattern in $patterns) {
    $matches = @(Get-ChildItem -Path (Join-Path $Root $pattern) -File -ErrorAction SilentlyContinue)
    if ($matches.Count -eq 0) {
      $parts.Add("MISSING:$pattern")
    }
    foreach ($file in ($matches | Sort-Object FullName)) {
      $relative = $file.FullName.Substring($Root.Length).TrimStart('\')
      $digest = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
      $parts.Add("$relative=$digest")
    }
  }
  if (-not (Get-Command node -ErrorAction SilentlyContinue) -or
      -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    return $null
  }
  # Capture native exit statuses before any PowerShell pipeline; Windows
  # PowerShell 5.1 can report -1 after piping a successful native command.
  $nodeOutput = & node --version 2>$null
  $nodeExit = $LASTEXITCODE
  if ($nodeExit -ne 0 -or -not $nodeOutput) { return $null }
  $nodeVersion = $nodeOutput | Select-Object -Last 1
  $npmOutput = & cmd.exe /d /c "npm --version 2>NUL"
  $npmExit = $LASTEXITCODE
  if ($npmExit -ne 0 -or -not $npmOutput) { return $null }
  $npmVersion = $npmOutput | Select-Object -Last 1
  $parts.Add("node=$nodeVersion")
  $parts.Add("npm=$npmVersion")
  $text = $parts -join "`n"
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '') }
  finally { $sha.Dispose() }
}

try {
  $fingerprint = Get-InstallFingerprint
  if (-not $fingerprint) { Write-Host "[deps] Toolchain unavailable."; exit 1 }
  $requiredPaths = @(
    $VenvPython,
    (Join-Path $Root "node_modules\.bin\vite.cmd"),
    (Join-Path $Root "node_modules\.bin\tsc.cmd"),
    (Join-Path $Root "node_modules\.bin\concurrently.cmd")
  )
  foreach ($path in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      Write-Host "[deps] Missing: $path"
      exit 1
    }
  }
  # npm workspaces may hoist Electron to root or keep it locally. Either
  # layout is valid, but the actual downloaded Windows executable is needed.
  $electronRoots = @(
    (Join-Path $Root "node_modules\electron"),
    (Join-Path $Root "apps\desktop\node_modules\electron")
  )
  $electronReady = $false
  foreach ($electronRoot in $electronRoots) {
    $binary = Join-Path $electronRoot "dist\electron.exe"
    if (Test-Path -LiteralPath $binary -PathType Leaf) {
      $electronReady = $true
      break
    }
  }
  if (-not $electronReady) {
    Write-Host "[deps] Electron executable is missing; npm workspace install needs repair."
    exit 1
  }
  # Importing hermes_cli from the checkout is insufficient: it succeeds even
  # when its editable distribution or transitive libraries are not installed.
  & $VenvPython -c "import sys, hermes_cli, httpx, pydantic; from importlib.metadata import version; assert sys.version_info[:2] == (3,14); version('hermes-agent')" 2>$null
  if ($LASTEXITCODE -ne 0) { Write-Host "[deps] Workstation Python environment needs repair."; exit 1 }
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    # Windows PowerShell 5.1 can promote uv's informational stderr to a
    # terminating NativeCommandError under ErrorActionPreference=Stop.
    $savedPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = "Continue"
      $uvOutput = @(& uv pip check --python $VenvPython 2>&1)
      $uvExit = $LASTEXITCODE  # Read immediately after the native process.
    } finally {
      $ErrorActionPreference = $savedPreference
    }
    if ($uvExit -ne 0) {
      Write-Host "[deps] Python dependency graph is incomplete or incompatible; repairing."
      foreach ($line in $uvOutput) { Write-Host "  $line" }
      exit 1
    }
  }
  if ($Action -eq "Record") {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StampFile) | Out-Null
    [System.IO.File]::WriteAllText($StampFile, $fingerprint)
    Write-Host "[deps] Successful dependency install fingerprint recorded."
    exit 0
  }
  if ((Test-Path -LiteralPath $StampFile) -and
      ([System.IO.File]::ReadAllText($StampFile).Trim() -eq $fingerprint)) {
    Write-Host "[deps] Verified cached dependencies; install not required."
    exit 0
  }
  Write-Host "[deps] Dependency inputs changed (or no successful-install record); full install required."
  exit 1
} catch {
  Write-Host "[deps] Could not validate cached install: $($_.Exception.Message)"
  exit 1
}
