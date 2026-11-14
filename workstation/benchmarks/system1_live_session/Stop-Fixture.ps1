$ErrorActionPreference = 'Stop'
$runtime = Join-Path $env:LOCALAPPDATA 'HermesWorkstation\qualification\system1-live-fixture'
$pidFile = Join-Path $runtime 'pid.txt'
$fixture = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'fixture_server.py'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output "FIXTURE_STOP=not_owned"; exit 0 }
$ownedPid = [int](Get-Content -LiteralPath $pidFile -TotalCount 1)
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ownedPid" -ErrorAction SilentlyContinue
if (-not $proc) { Remove-Item -LiteralPath $pidFile; Write-Output "FIXTURE_STOP=already_exited"; exit 0 }
if (-not $proc.CommandLine -or -not $proc.CommandLine.Contains($fixture)) {
    throw "REFUSING_TO_KILL_UNRELATED_PID=$ownedPid"
}
Stop-Process -Id $ownedPid -Force
Remove-Item -LiteralPath $pidFile
Write-Output "FIXTURE_STOP=owned_process_only"
