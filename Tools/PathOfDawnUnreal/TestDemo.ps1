#requires -Version 7.2
[CmdletBinding()]
param([switch]$SourceOnly, [string]$BuildId, [string]$SmokeReport, [switch]$RequireArt, [switch]$UnrealAutomation, [string]$EngineRoot)
. "$PSScriptRoot/Common.ps1"
$pythonCommand = if ($IsWindows) { 'python' } else { 'python3' }
$python = (Get-Command $pythonCommand -ErrorAction Stop).Source
$arguments = @((Join-Path $PSScriptRoot 'validate_content.py'),'--root',$script:RepoRoot,'--self-test','--report',(Join-Path $script:EvidenceRoot 'content-validation.json'))
if ($RequireArt) { $arguments += '--require-art' }
Invoke-DawnCommand $python $arguments (Join-Path $script:EvidenceRoot 'content-validation.log')
Invoke-DawnCommand $python @('-m','unittest','discover','-s',(Join-Path $PSScriptRoot 'tests'),'-p','test_source_asset_guard.py','-v') (Join-Path $script:EvidenceRoot 'source-asset-guard-tests.log')
Invoke-DawnCommand $python @('-m','unittest','discover','-s',(Join-Path $PSScriptRoot 'tests'),'-p','test_narrative_import.py','-v') (Join-Path $script:EvidenceRoot 'narrative-import-contract-tests.log')
Invoke-DawnCommand $python @('-m','unittest','discover','-s',(Join-Path $PSScriptRoot 'tests'),'-p','test_editor_verification.py','-v') (Join-Path $script:EvidenceRoot 'editor-verification-contract-tests.log')
if ($RequireArt) {
    Invoke-DawnCommand $python @('-m','unittest','discover','-s',(Join-Path $PSScriptRoot 'tests'),'-p','test_visual_source_paths.py','-v') (Join-Path $script:EvidenceRoot 'visual-source-path-tests.log')
    Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_visual_sources.py'),'--root',$script:RepoRoot,'--report',(Join-Path $script:EvidenceRoot 'visual-source-validation.json')) (Join-Path $script:EvidenceRoot 'visual-source-validation.log')
    Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_font.py')) (Join-Path $script:EvidenceRoot 'font-validation.log')
}
$core = Join-Path $script:ProjectRoot 'Source/PathOfDawnUnreal/Core'
$tests = Join-Path $PSScriptRoot 'tests/core_tests.cpp'
Assert-DawnFile $tests
Invoke-DawnCommand (Get-Process -Id $PID).Path @('-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot 'tests/process_launch_tests.ps1')) (Join-Path $script:EvidenceRoot 'process-launch-tests.log')
$outputDirectory = Join-Path ([IO.Path]::GetTempPath()) "PathOfDawn-tests-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $outputDirectory | Out-Null
try {
    if ($IsWindows) {
        $compiler = (Get-Command cl.exe -ErrorAction Stop).Source
        $testExecutable = Join-Path $outputDirectory 'core_tests.exe'
        Push-Location $outputDirectory
        try { Invoke-DawnCommand $compiler @('/nologo','/std:c++17','/EHsc','/W4',"/I$core",$tests,"/Fe:$testExecutable") (Join-Path $script:EvidenceRoot 'core-compile.log') }
        finally { Pop-Location }
    } else {
        $compiler = (Get-Command g++ -ErrorAction Stop).Source
        $testExecutable = Join-Path $outputDirectory 'core_tests'
        Invoke-DawnCommand $compiler @('-std=c++17','-Wall','-Wextra','-pedantic','-I',$core,$tests,'-o',$testExecutable) (Join-Path $script:EvidenceRoot 'core-compile.log')
    }
    Invoke-DawnCommand $testExecutable @() (Join-Path $script:EvidenceRoot 'core-tests.log')
} finally { Remove-Item -LiteralPath $outputDirectory -Recurse -Force }
if ($UnrealAutomation) {
    Assert-WindowsHost
    $resolved = Resolve-DawnEngine $EngineRoot
    $automationReport = Join-Path $script:EvidenceRoot ('UnrealAutomation-' + (New-DawnBuildId))
    $editor = Join-Path $resolved 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    # NullRHI is used only for unit tests. It is explicitly not graphic/media evidence.
    Invoke-DawnCommand $editor @($script:ProjectFile,'-unattended','-nopause','-NullRHI','-nosplash','-ExecCmds=Automation RunTests PathOfDawn','-TestExit=Automation Test Queue Empty',"-ReportExportPath=$automationReport") (Join-Path $script:EvidenceRoot 'UnrealAutomation.log')
    $index = Join-Path $automationReport 'index.json'
    Assert-DawnFile $index
    $result = Get-Content -Raw -LiteralPath $index | ConvertFrom-Json
    if ($result.failed -gt 0 -or $result.succeeded -lt 2) { throw 'Unreal automation failed or did not execute the required tests.' }
    foreach ($required in @('PathOfDawn.Core.BranchesAndRewind','PathOfDawn.SaveGame.MemoryRoundtrip')) {
        if (@($result.tests | Where-Object { $_.fullTestPath -eq $required -and $_.state -eq 'Success' }).Count -ne 1) { throw "Missing successful automation test: $required" }
    }
}
if ($SourceOnly) {
    Write-Host 'Portable C++ core/content checks passed. Unreal compile, cook, graphics, USaveGame integration and streaming have NOT been tested by these checks.'
    return
}
if (-not $BuildId -or -not $SmokeReport) { throw 'Source checks passed. To certify an actual package, supply -BuildId and -SmokeReport containing observed graphical checks and real captures. See smoke-report.template.json.' }
$candidate = Get-DawnCandidate $BuildId
$validatedSmoke = Assert-DawnSmoke $candidate $SmokeReport
$validatedSmoke.captures = @($validatedSmoke.captures | ForEach-Object { if ([IO.Path]::IsPathRooted($_)) { $_ } else { [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $SmokeReport) $_)) } })
$destination = Join-Path $candidate 'smoke-report.json'
Write-DawnJson $destination $validatedSmoke
Write-Host 'Supplied graphical evidence validated and associated with this exact payload. This command did not perform the manual observations.'
