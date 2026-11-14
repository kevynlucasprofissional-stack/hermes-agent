param(
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][string]$TextFile
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $TextFile -PathType Leaf)) { throw 'SAPI_TEXT_FILE_MISSING' }
$sentence = [System.IO.File]::ReadAllText($TextFile, [System.Text.Encoding]::UTF8)
if ([string]::IsNullOrWhiteSpace($sentence) -or $sentence.Length -gt 300) { throw 'SAPI_TEXT_INVALID' }
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $candidate = $voice.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1
  if (-not $candidate) { throw 'SAPI_PTBR_VOICE_NOT_INSTALLED' }
  $voice.SelectVoice($candidate.VoiceInfo.Name)
  $voice.SetOutputToWaveFile($OutputPath)
  $voice.Speak($sentence)
  $voice.SetOutputToNull()
  if ((Get-Item -LiteralPath $OutputPath).Length -lt 44) { throw 'SAPI_EMPTY_WAV' }
  Write-Output 'SAPI_PTBR_OK'
} finally {
  $voice.Dispose()
}
