#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
Assert-DawnFile $script:ProjectFile
$build = Join-Path $resolved 'Engine/Build/BatchFiles/Build.bat'
Assert-DawnFile $build
Invoke-DawnCommand $build @('PathOfDawnUnrealEditor','Win64','Development',"-Project=$script:ProjectFile",'-WaitMutex','-NoHotReloadFromIDE','-UTF8Output') (Join-Path $script:EvidenceRoot 'BuildEditor.log')
Write-DawnJson (Join-Path $script:EvidenceRoot 'editor-build.json') @{completedUtc=[DateTime]::UtcNow.ToString('O'); engineVersion=(Get-Content -Raw -LiteralPath (Join-Path $resolved 'Engine/Build/Build.version') | ConvertFrom-Json); target='PathOfDawnUnrealEditor'; configuration='Development'; compilationSucceeded=$true}
