$ErrorActionPreference = 'Continue'
$logDir = Join-Path $env:LOCALAPPDATA 'HermesWorkstation\logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    Write-Host "LOG_DIR_NOT_FOUND: $logDir"
    exit 1
}
$logs = Get-ChildItem -LiteralPath $logDir -Filter 'desktop*.log' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 3
if (-not $logs) {
    Write-Host "NO_DESKTOP_LOGS_FOUND in $logDir"
    Get-ChildItem -LiteralPath $logDir -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $($_.Name) ($($_.Length) bytes, $($_.LastWriteTime))" }
    exit 1
}
foreach ($log in $logs) {
    Write-Host "=== $($log.Name) ($($log.LastWriteTime), $($log.Length) bytes) ==="
    $matches = Select-String -LiteralPath $log.FullName -Pattern '\[boot-perf\]' -SimpleMatch -ErrorAction SilentlyContinue
    if ($matches) {
        $matches | ForEach-Object { Write-Host $_.Line }
    } else {
        Write-Host "(no [boot-perf] markers found)"
        # Show last 20 lines for context
        Write-Host "--- Last 20 lines ---"
        Get-Content -LiteralPath $log.FullName -Tail 20 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }
    }
    Write-Host ""
}