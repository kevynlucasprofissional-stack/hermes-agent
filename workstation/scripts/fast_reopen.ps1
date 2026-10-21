[CmdletBinding()]
param([switch]$Probe)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$Desktop = Join-Path $Root 'apps\desktop'
# npm workspaces may install Electron in the Desktop workspace rather than root.
$Electron = @(
  (Join-Path $Desktop 'node_modules\electron\dist\electron.exe'),
  (Join-Path $Root 'node_modules\electron\dist\electron.exe')
) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
$Bootstrap = Join-Path $Root 'START-HERMES-WORKSTATION.bat'

# The app's existing single-instance lock owns the restore/focus behavior.
# Only detect the main Electron process from THIS checkout (ignore renderers,
# other Electron apps and similarly named executables).
$Running = $false
if ($Electron -and (Test-Path -LiteralPath $Electron -PathType Leaf)) {
  try {
    $Running = @(Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" -ErrorAction Stop |
      Where-Object {
        $_.ExecutablePath -ieq $Electron -and
        $_.CommandLine -notmatch '(?i)(?:^|\s)--type='
      }).Count -gt 0
  } catch {
    # A failed discovery is not proof that Hermes is active: use the normal
    # bootstrap, which retains its own install/repair and startup safeguards.
    $Running = $false
  }
}

if ($Probe) {
  if ($Running) { Write-Output 'HOT: existing Hermes Electron detected' }
  else { Write-Output 'COLD: no existing Hermes Electron detected' }
  exit 0
}

try {
  if ($Running) {
    # A lightweight second-instance launch signals the FIRST Electron process,
    # which restores/focuses its hidden window. No bootstrap, doctor or Vite.
    $env:HERMES_WORKSTATION_BROWSER = '1'
    $env:HERMES_DESKTOP_CDP_PORT = 'off'
    $env:HERMES_DESKTOP_DEV_SERVER = 'http://127.0.0.1:5174'
    Start-Process -FilePath $Electron -ArgumentList '.' -WorkingDirectory $Desktop -ErrorAction Stop | Out-Null
  } else {
    # Cold start retains the old visible CMD, diagnostics and dependency checks.
    if (-not (Test-Path -LiteralPath $Bootstrap -PathType Leaf)) {
      throw "Hermes bootstrap missing: $Bootstrap"
    }
    Start-Process -FilePath $env:ComSpec -ArgumentList ('/d /c ""{0}""' -f $Bootstrap) -WorkingDirectory $Root -ErrorAction Stop | Out-Null
  }
} catch {
  # The shortcut itself is hidden, so surface launcher failures explicitly.
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show(
    "Hermes Work could not be opened: $($_.Exception.Message)",
    'Hermes Work - Launcher Error',
    'OK',
    'Error'
  ) | Out-Null
  exit 1
}
