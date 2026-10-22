[CmdletBinding()]
param(
  [switch]$SkipPatch,
  [switch]$SkipInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallScript = Join-Path $PSScriptRoot "install.ps1"
$VenvRoot = Join-Path $Root ".venv"
$VenvScripts = Join-Path $VenvRoot "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"

if (-not $SkipInstall) {
  if ($SkipPatch) {
    & $InstallScript -SkipCorePatch
  } else {
    & $InstallScript
  }
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

if (-not (Test-Path $VenvPython)) {
  throw "Hermes Workstation Python environment is missing: $VenvPython. Run workstation\install.cmd first."
}

& $VenvPython -c "import hermes_cli, sys; print(sys.executable)" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Hermes Workstation .venv exists but cannot import hermes_cli. Rerun workstation\install.cmd."
}

# Put the repo-local Hermes runtime first so Desktop backend discovery resolves
# this checkout's hermes.exe/python instead of a global Python installation.
$env:VIRTUAL_ENV = $VenvRoot
$env:HERMES_PYTHON = $VenvPython
$env:PATH = "$VenvScripts;$env:PATH"
$env:HERMES_WORKSTATION_BROWSER = "1"

# One-Click always launches the source-tree Vite dev server (npm run dev).
# Restore the desktop renderer's local CDP debugger for DOM inspection and
# console diagnostics. Packaged builds are still gated by electron/dev-cdp.ts.
# Preserve a caller override: 9333 changes ports; 'off' disables CDP.
if (-not $env:HERMES_DESKTOP_CDP_PORT) {
  $env:HERMES_DESKTOP_CDP_PORT = "9222"
  $WorkstationDefaultRendererCdp = $true
} else {
  $WorkstationDefaultRendererCdp = $false
}

if ($env:OS -match "Windows_NT") {
  try {
    $icoPath = Join-Path $Root "Hermes Work.ico"
    if (Test-Path $icoPath) {
      $shell = New-Object -ComObject WScript.Shell
      $shortcutTargets = @(
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'Hermes Work.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes Work.lnk')
      )
      $shortcutUpdated = $false
      foreach ($lnkPath in $shortcutTargets) {
        if (Test-Path $lnkPath) {
          try {
            $sc = $shell.CreateShortcut($lnkPath)
            if ($sc.IconLocation -ne "$icoPath,0") {
              $sc.IconLocation = "$icoPath,0"
              $sc.Save()
              $shortcutUpdated = $true
            }
          } catch {
            # Silently tolerate locked shortcuts
          }
        }
      }
      if ($shortcutUpdated) {
        & ie4uinit.exe -show 2>$null
      }
    }
  } catch {
    # Best-effort
  }
}

Push-Location $Root
try {
  Write-Host "Starting Hermes Desktop with Workstation Browser..." -ForegroundColor Cyan
  Write-Host "Python runtime: $VenvPython"
  Write-Host "Node runtime:   $nodeVersion"
  Write-Host "Dev server:      http://127.0.0.1:5174 (Vite + HMR)"
  if ($WorkstationDefaultRendererCdp) {
    Write-Host "Renderer CDP:    127.0.0.1:9222 (automatic dev/debug mode)"
  } else {
    Write-Host "Renderer CDP:    $env:HERMES_DESKTOP_CDP_PORT (explicit override)"
  }
  Write-Host ""
  Write-Host "Keep this terminal open while Hermes Desktop is running." -ForegroundColor DarkGray
  Write-Host "To stop the dev server later, press Ctrl+C once and answer Y/S if Windows asks to terminate the batch job." -ForegroundColor DarkGray
  Write-Host ""

  # Invoke dev script directly from the desktop workspace directory.
  # Using `npm run dev --workspace apps/desktop` fails when npm hoists
  # concurrently to root without creating bin links in the workspace;
  # running from the workspace directory lets npm resolve hoisted bins
  # via the standard node_modules resolution chain.
  Push-Location (Join-Path $Root "apps\desktop")
  try {
    & npm run dev
    if ($LASTEXITCODE -ne 0) {
      throw "Hermes Desktop exited with code ${LASTEXITCODE}."
    }
  } finally {
    Pop-Location
  }
}
finally {
  Pop-Location
}
