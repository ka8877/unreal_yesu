#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [switch]$SkipCompile)
. "$PSScriptRoot/Common.ps1"
. "$PSScriptRoot/AssetDiagnostics.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
if (@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object { $_.CommandLine -like '*PathOfDawnUnreal.uproject*' }).Count -gt 0) { throw 'Close the PathOfDawnUnreal Editor before asset generation; only one editor may write these packages.' }
if (-not $SkipCompile) { & "$PSScriptRoot/BuildEditor.ps1" -EngineRoot $resolved }
Assert-DawnFile (Join-Path $script:ProjectRoot 'Binaries/Win64/UnrealEditor-PathOfDawnUnreal.dll')
$python = (Get-Command python -ErrorAction Stop).Source
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_content.py'),'--root',$script:RepoRoot,'--require-art') (Join-Path $script:EvidenceRoot 'content-validation.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_visual_sources.py'),'--root',$script:RepoRoot,'--report',(Join-Path $script:EvidenceRoot 'visual-source-validation.json')) (Join-Path $script:EvidenceRoot 'visual-source-validation.log')
$editor = Join-Path $resolved 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$generator = Join-Path $PSScriptRoot 'generate_demo_assets.py'
Assert-DawnFile $generator
$mutex = [Threading.Mutex]::new($false, 'Local\PathOfDawnUnrealEditorAssets')
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); throw 'Another PathOfDawn asset generation is running.' }
try {
    $report = Join-Path $script:ProjectRoot 'Saved/PathOfDawn/asset-generation-report.json'
    $verifyReport = Join-Path $script:ProjectRoot 'Saved/PathOfDawn/asset-verification-report.json'
    # Real Editor Python. No NullRHI: creation reports are not graphical evidence regardless.
    $generation=Invoke-DawnAssetEditorPass -Editor $editor -ProjectFile $script:ProjectFile -Generator $generator -ReportPath $report -EvidenceDirectory $script:EvidenceRoot -Mode generation
    Assert-DawnFile (Join-Path $script:ProjectRoot 'Content/PathOfDawn/Maps/L_Galilee.umap')
    $verification=Invoke-DawnAssetEditorPass -Editor $editor -ProjectFile $script:ProjectFile -Generator $generator -ReportPath $verifyReport -EvidenceDirectory $script:EvidenceRoot -Mode reload-verification
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
