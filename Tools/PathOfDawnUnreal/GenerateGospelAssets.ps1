#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [switch]$SkipCompile, [string]$Python)
. "$PSScriptRoot/Common.ps1"
. "$PSScriptRoot/AssetDiagnostics.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$attempt = (New-DawnBuildId) + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$evidence = Join-Path $script:EvidenceRoot "GospelHost/Generate-$attempt"
$gospelTools = Join-Path $PSScriptRoot 'Gospel'
$generator = Join-Path $PSScriptRoot 'generate_gospel_assets.py'
$checker = Join-Path $gospelTools 'check_generated_assets.py'
foreach ($file in @($generator,$checker,(Join-Path $gospelTools 'validate_gospel_font.py'))) { Assert-DawnFile $file }
# Source provenance and content must pass before an Editor is allowed to mutate packages.
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'export_campaign.py'),'--verify-sources-only') (Join-Path $evidence 'source-provenance.log')
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'validate_campaign.py')) (Join-Path $evidence 'content-validation.log')
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'validate_gospel_font.py')) (Join-Path $evidence 'font-validation.log')
& "$PSScriptRoot/CheckEnvironment.ps1" -EngineRoot $resolved | Tee-Object -FilePath (Join-Path $evidence 'environment-check.log') | Write-Host
Copy-Item -LiteralPath (Join-Path $script:EvidenceRoot 'windows-environment.json') -Destination (Join-Path $evidence 'windows-environment.json')
$mutex = [Threading.Mutex]::new($false, 'Local\PathOfDawnUnrealEditorAssets')
$owned = $false
try {
    try { $owned = $mutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] {
        $owned = $true
        throw 'A previous Editor asset operation ended unexpectedly. Inspect saved reports and generated packages before retrying.'
    }
    if (-not $owned) { throw 'Another PathOfDawn asset operation owns the Editor packages.' }
    if (@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object { $_.CommandLine -like '*PathOfDawnUnreal.uproject*' }).Count -gt 0) {
        throw 'Close the PathOfDawnUnreal Editor before Gospel asset generation.'
    }
    if (-not $SkipCompile) { & "$PSScriptRoot/BuildEditor.ps1" -EngineRoot $resolved }
    Assert-DawnFile (Join-Path $script:ProjectRoot 'Binaries/Win64/UnrealEditor-PathOfDawnUnreal.dll')
    $editor = Join-Path $resolved 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    Assert-DawnFile $editor
    $reportDirectory = Join-Path $script:ProjectRoot 'Saved/PathOfDawnGospel'
    $generation = Invoke-DawnAssetEditorPass -Editor $editor -ProjectFile $script:ProjectFile -Generator $generator -ReportPath (Join-Path $reportDirectory 'asset-generation-report.json') -EvidenceDirectory $evidence -Mode generation
    # A separate Editor process reloads the persisted data/map/font references.
    $verification = Invoke-DawnAssetEditorPass -Editor $editor -ProjectFile $script:ProjectFile -Generator $generator -ReportPath (Join-Path $reportDirectory 'asset-verification-report.json') -EvidenceDirectory $evidence -Mode reload-verification
    Invoke-DawnCommand $Python @($checker) (Join-Path $evidence 'generated-package-check.log')
    Write-Host "Gospel assets created and freshly reloaded. Evidence: $evidence"
    Write-Host 'Actual cinematic quality, gameplay, packaged rendering and streaming have not been tested by asset generation.'
} finally {
    if ($owned) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
