# Narrates every step with the Windows speech engine (offline), one voice per line.
#   powershell -File tts.ps1 <items.json> <sample rate> <speed -10..10>
# items.json: [{"text": "...", "out": "...wav", "voice": "Microsoft David Desktop"}, ...]
param([string]$Items, [int]$Rate = 24000, [int]$Speed = 0)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo($Rate, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$list = Get-Content -Raw -Encoding UTF8 $Items | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = $Speed
$n = 0
foreach ($item in $list) {
  $s.SelectVoice($item.voice)
  $s.SetOutputToWaveFile($item.out, $format)
  $s.Speak($item.text)
  $s.SetOutputToNull()
  $n++
}
$s.Dispose()
"narrated $n lines"
