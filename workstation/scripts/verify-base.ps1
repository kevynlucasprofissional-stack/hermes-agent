$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Expected = "057dcdf236f8a6a26721c10fcc6ccb72726e272a"

Push-Location $Root
try {
  $Head = (git rev-parse HEAD).Trim()
  git merge-base --is-ancestor $Expected $Head
  if ($LASTEXITCODE -ne 0) {
    throw "HEAD $Head is not descended from expected Hermes base $Expected"
  }
  Write-Host "[OK] Hermes base compatible: $Head" -ForegroundColor Green
}
finally {
  Pop-Location
}
