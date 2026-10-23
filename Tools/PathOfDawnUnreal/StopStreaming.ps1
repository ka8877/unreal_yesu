#requires -Version 7.2
[CmdletBinding()]
param([switch]$IncludeLocalGame)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
Stop-DawnProcess 'stream-game'
Stop-DawnProcess 'signalling'
if ($IncludeLocalGame) { Stop-DawnProcess 'local-game' }
Write-Host 'Only recorded processes with matching PID, start time and executable path were stopped.'
