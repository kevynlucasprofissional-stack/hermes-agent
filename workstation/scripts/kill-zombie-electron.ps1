$ErrorActionPreference = 'Continue'
$killed = 0
Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.ExecutablePath -like '*hermes-agent*' } |
  ForEach-Object {
    Write-Host "Killing PID $($_.ProcessId): $($_.CommandLine.Substring(0, [Math]::Min(80, $_.CommandLine.Length)))"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $killed++
  }
Write-Host "Killed $killed electron process(es)"
$remaining = (Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.ExecutablePath -like '*hermes-agent*' }).Count
Write-Host "Remaining hermes electron processes: $remaining"