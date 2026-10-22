$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot '..\start.ps1'
$errors = $null
$tokens = $null
[System.Management.Automation.Language.Parser]::ParseFile($target, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count -gt 0) {
    foreach ($e in $errors) { Write-Host "ERROR: $($e.Message) at line $($e.Extent.StartLineNumber)" }
    exit 1
}
Write-Host "OK: start.ps1 syntax valid"