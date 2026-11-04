#requires -Version 7.2
[CmdletBinding()]
param([switch]$SourceOnly, [switch]$Sanitize, [switch]$CheckExportParity, [string]$DotNet='dotnet', [string]$Python)
. "$PSScriptRoot/Common.ps1"
if (-not $Python) {
    $command = if ($IsWindows) { 'python' } else { 'python3' }
    $Python = (Get-Command $command -ErrorAction Stop).Source
}
$attempt = (New-DawnBuildId) + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$evidence = Join-Path $script:EvidenceRoot "GospelHost/Portable-$attempt"
$gospelTools = Join-Path $PSScriptRoot 'Gospel'
$tests = Join-Path $PSScriptRoot 'tests'
foreach ($file in @('test_gospel_content.py','test_gospel_core.py','test_gospel_import.py','test_gospel_asset_guard.py','test_gospel_release.py')) {
    Assert-DawnFile (Join-Path $tests $file)
}
Assert-DawnFile (Join-Path $gospelTools 'validate_gospel_font.py')
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'export_campaign.py'),'--verify-sources-only') (Join-Path $evidence 'source-provenance.log')
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'validate_campaign.py')) (Join-Path $evidence 'content-validation.log')
Invoke-DawnCommand $Python @((Join-Path $gospelTools 'validate_gospel_font.py')) (Join-Path $evidence 'font-validation.log')
Invoke-DawnCommand $Python @('-m','unittest','discover','-s',$tests,'-p','test_gospel_*.py','-v') (Join-Path $evidence 'gospel-contract-tests.log')
# This test runner has a real C++ executable, not unittest TestCase discovery.
$coreArguments = @((Join-Path $tests 'test_gospel_core.py'))
if ($Sanitize) { $coreArguments += '--sanitize' }
Invoke-DawnCommand $Python $coreArguments (Join-Path $evidence 'gospel-core-tests.log')
if ($CheckExportParity) {
    Invoke-DawnCommand $Python @((Join-Path $gospelTools 'export_campaign.py'),'--dotnet',$DotNet,'--check') (Join-Path $evidence 'unity-export-parity.log')
}
Write-Host "Portable Gospel content/core/importer checks passed. Evidence: $evidence"
Write-Host 'Unreal compilation, Editor import/reload, Cook, gameplay rendering, USaveGame and streaming remain separate host checks.'
