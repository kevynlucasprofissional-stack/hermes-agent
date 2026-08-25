[CmdletBinding()]
param(
  [ValidateSet("edge", "stable")]
  [string]$Channel = "edge",
  [switch]$Merge
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Push-Location $Root
try {
  $remotes = git remote
  if ($remotes -notcontains "upstream") {
    git remote add upstream https://github.com/NousResearch/hermes-agent.git
  }

  git fetch upstream

  $Lock = Get-Content (Join-Path $Root "workstation\channels.json") -Raw | ConvertFrom-Json
  $Ref = $Lock.$Channel.hermes_ref
  Write-Host "Workstation $Channel currently pins Hermes $Ref"
  Write-Host "Upstream main: $(git rev-parse upstream/main)"

  if ($Merge) {
    if ($Channel -ne "edge") {
      throw "Direct upstream merges are allowed only through the edge channel."
    }
    git merge --no-ff upstream/main
    Write-Host "Run Workstation CI/E2E before promoting edge to stable." -ForegroundColor Yellow
  }
}
finally {
  Pop-Location
}
