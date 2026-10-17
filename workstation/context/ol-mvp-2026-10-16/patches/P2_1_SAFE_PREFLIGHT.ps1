# P2.1 OL-MVP: read-only local preflight, safe around concurrent agents.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\P2_1_SAFE_PREFLIGHT.ps1 -RepoRoot "C:\Github\hermes-agent"
# Does not checkout, stash, commit, mutate user files, print page content or
# certify artifact authenticity. Git command failures are reported, not hidden.
param([string]$RepoRoot = 'C:\Github\hermes-agent')

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
  throw "Repository directory not found: $RepoRoot"
}
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))) {
  throw "Missing Git metadata in $RepoRoot"
}

Write-Output '=== GIT STATUS (READ ONLY) ==='
& git -C $RepoRoot status --short --branch
Write-Output '=== WORKTREES / CLAIMS MUST BE INSPECTED ==='
& git -C $RepoRoot worktree list --porcelain
Write-Output '=== HEAD / REMOTE REFERENCES ==='
& git -C $RepoRoot log -1 --format='%H %s'
& git -C $RepoRoot branch -a --list '*ol-mvp*'
Write-Output '=== DIFF SUMMARY (NO CONTENT) ==='
& git -C $RepoRoot diff --stat
Write-Output '=== UNTRACKED PATHS (NO CONTENT) ==='
& git -C $RepoRoot ls-files --others --exclude-standard

$testRoot = Join-Path $RepoRoot 'apps\desktop\test-results'
Write-Output '=== LATEST NATIVE E2E RECEIPTS (PATHS ONLY) ==='
if (Test-Path -LiteralPath $testRoot) {
  $files = @(Get-ChildItem -Path $testRoot -Filter 'ol-mvp-p2-native-chat-work-execute-evidence-*.json' -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 3)
  foreach ($f in $files) {
    Write-Output ("RECEIPT_PATH=" + $f.FullName)
    try {
      $doc = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
      # No DOM, card text, credentials or raw tool outputs.
      $keys = @($doc.PSObject.Properties.Name)
      Write-Output ("TOP_LEVEL_KEYS=" + ($keys -join ','))
    } catch {
      Write-Output "INVALID_JSON_OR_INCOMPLETE_RECEIPT"
    }
  }
  if ($files.Count -eq 0) { Write-Output 'NO_LOCAL_P2_EVIDENCE_FOUND' }
} else {
  Write-Output 'NO_TEST_RESULTS_DIR'
}
Write-Output 'P2_1_PREFLIGHT_COMPLETE_NO_FILES_MODIFIED'
