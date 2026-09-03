param(
  [string]$RepoRoot = (Get-Location).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExpectedBranch = 'impl4-browser-task-lifecycle'
$ExpectedSha = '1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70'
$RunnerName = 'run_impl4_native_smoke_v9.mjs'

Set-Location $RepoRoot
$RepoRoot = (git rev-parse --show-toplevel).Trim()

git fetch origin | Out-Null

$branch = (git branch --show-current).Trim()
$head = (git rev-parse HEAD).Trim()
$originHead = (git rev-parse "origin/$ExpectedBranch").Trim()

Write-Host "[impl4-smoke] Branch: $branch"
Write-Host "[impl4-smoke] HEAD: $head"
Write-Host "[impl4-smoke] origin/${ExpectedBranch}: $originHead"

if ($branch -ne $ExpectedBranch) {
  throw "Wrong branch. Expected $ExpectedBranch, got $branch"
}
if ($head -ne $ExpectedSha) {
  throw "Wrong local SHA. Expected $ExpectedSha, got $head"
}
if ($originHead -ne $ExpectedSha) {
  throw "Origin moved. Expected $ExpectedSha, got $originHead"
}

$relevantStatus = @(git status --short | Where-Object {
  $_ -notmatch '^\?\?\s+run_impl4_native_smoke(?:_v\d+)?\.(ps1|mjs)$'
})

if ($relevantStatus.Count -gt 0) {
  Write-Host ($relevantStatus -join [Environment]::NewLine)
  throw 'Product checkout is not clean.'
}

$runner = Join-Path $RepoRoot $RunnerName
if (!(Test-Path $runner)) {
  throw "Missing $RunnerName in repo root."
}

$node = (Get-Command node -ErrorAction Stop).Source
Write-Host "[impl4-smoke] Node: $node"
Write-Host "[impl4-smoke] Starting Node-native smoke orchestrator..."

& $node $runner $RepoRoot
$exit = $LASTEXITCODE

Write-Host ""
Write-Host "[impl4-smoke] Final product git status:"
$finalStatus = @(git status --short | Where-Object {
  $_ -notmatch '^\?\?\s+run_impl4_native_smoke(?:_v\d+)?\.(ps1|mjs)$'
})
if ($finalStatus.Count -eq 0) {
  Write-Host "(clean)"
} else {
  Write-Host ($finalStatus -join [Environment]::NewLine)
}

if ($exit -ne 0) {
  throw "Native smoke orchestrator failed with exit code $exit."
}
