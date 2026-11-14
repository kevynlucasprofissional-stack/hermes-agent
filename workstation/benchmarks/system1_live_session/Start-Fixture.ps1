$ErrorActionPreference = 'Stop'
$port = 18791
$health = "http://127.0.0.1:$port/health"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $dir '..\..\..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$fixture = Join-Path $dir 'fixture_server.py'
$runtime = Join-Path $env:LOCALAPPDATA 'HermesWorkstation\qualification\system1-live-fixture'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

function Test-ExpectedFixture {
    try {
        $reply = Invoke-RestMethod -Uri $health -TimeoutSec 2
        return ($reply.ok -eq $true -and $reply.fixture -eq 'hermes-system1-read-only')
    } catch { return $false }
}

if (Test-ExpectedFixture) {
    Write-Output "FIXTURE_READY=already_running"
    Write-Output "FIXTURE_URL=http://127.0.0.1:$port/unique"
    exit 0
}
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) { throw "PORT_OCCUPIED_BY_ANOTHER_SERVER=$port" }
if (-not (Test-Path -LiteralPath $python)) { throw "PYTHON_NOT_FOUND=$python" }
if (-not (Test-Path -LiteralPath $fixture)) { throw "FIXTURE_SCRIPT_NOT_FOUND=$fixture" }

$proc = Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $fixture + '"'), '--port', "$port") -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'stdout.log') -RedirectStandardError (Join-Path $runtime 'stderr.log')
$proc.Id | Set-Content -LiteralPath (Join-Path $runtime 'pid.txt') -Encoding Ascii
for ($i=0; $i -lt 30; $i++) {
    if (Test-ExpectedFixture) {
        Write-Output "FIXTURE_READY=started"
        Write-Output "FIXTURE_PID=$($proc.Id)"
        Write-Output "FIXTURE_URL=http://127.0.0.1:$port/unique"
        exit 0
    }
    Start-Sleep -Milliseconds 150
}
$errFile = Join-Path $runtime 'stderr.log'
if (Test-Path -LiteralPath $errFile) { Get-Content -LiteralPath $errFile -Tail 30 }
throw "FIXTURE_NOT_READY: $health"
