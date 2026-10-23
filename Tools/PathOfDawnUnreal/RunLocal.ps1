#requires -Version 7.2
[CmdletBinding()]
param([Parameter(Mandatory)][string]$BuildId, [ValidateSet('720p','1080p')][string]$Resolution='1080p', [ValidateSet(30,60)][int]$FramesPerSecond=60)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$candidate = Get-DawnCandidate $BuildId
$manifest = Get-DawnManifest $candidate
$exe = Join-Path $candidate $manifest.runtimeExecutable
Assert-DawnFile $exe
$size = if ($Resolution -eq '720p') { @(1280,720) } else { @(1920,1080) }
$hostRoot = Get-DawnHostRoot
$process = Start-DawnProcess 'local-game' $exe @('-windowed',"-ResX=$($size[0])","-ResY=$($size[1])",'-ForceRes',"-DawnBuildId=$BuildId","-UserDir=$hostRoot",'-log',"-ExecCmds=t.MaxFPS $FramesPerSecond") (Split-Path -Parent $exe)
Write-Host "Started local game PID $($process.Id). Save root is $hostRoot (not the build directory)."
