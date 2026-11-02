#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot,[string]$Bindings,[switch]$ImportSourcesOnly,[switch]$ImportJournalData,[switch]$GenerateBenchmark)
. (Join-Path $PSScriptRoot '../Common.ps1')
if (([int][bool]$ImportSourcesOnly+[int][bool]$ImportJournalData+[int][bool]$GenerateBenchmark) -gt 1) { throw 'Choose source import, journal import or benchmark generation for one Editor pass.' }
$python=(Get-Command $(if ($IsWindows) {'python.exe'} else {'python3'}) -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$evidence=Join-Path $script:EvidenceRoot 'Rebuild'
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
if (-not $Bindings) { $Bindings=Join-Path $PSScriptRoot 'asset-bindings.example.json' }
if (-not (Test-Path -LiteralPath $Bindings -PathType Leaf)) { throw "Bindings file missing: $Bindings" }
$Bindings=[IO.Path]::GetFullPath($Bindings)
# Verify genuine downloaded sources without requesting a new download or altering them.
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'fetch_environment.py'),'--verify-only') (Join-Path $evidence 'environment-validation.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_journey.py')) (Join-Path $evidence 'narrative-validation.log')
$readiness=Join-Path $evidence 'readiness.json'
& $python (Join-Path $PSScriptRoot 'validate_readiness.py') --root $script:RepoRoot --bindings $Bindings --report $readiness
$readinessCode=$LASTEXITCODE
if ($readinessCode -notin @(0,2)) { throw "Readiness validation failed: $readinessCode" }
if (-not ($ImportSourcesOnly -or $ImportJournalData -or $GenerateBenchmark)) {
    Write-Host "Readiness report: $readiness"
    Write-Host 'No map/config/build/session was replaced. BLOCKED means required assets or visual evidence are missing.'
    exit $readinessCode
}
if ($GenerateBenchmark -and $readinessCode -ne 0) { throw "Benchmark blocked before launching Editor. See $readiness" }
Assert-WindowsHost
$resolved=Resolve-DawnEngine $EngineRoot
if (@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object { $_.CommandLine -like '*PathOfDawnUnreal.uproject*' }).Count -gt 0) { throw 'Close this project Editor before asset import. No other Unreal process will be stopped.' }
& (Join-Path $PSScriptRoot '../BuildEditor.ps1') -EngineRoot $resolved
$editor=Join-Path $resolved 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$generator=Join-Path $PSScriptRoot 'editor_benchmark.py'
$report=Join-Path $evidence ('editor-'+(New-DawnBuildId)+'.json')
$arguments=@($script:ProjectFile,"-ExecutePythonScript=$generator","-JourneyBindings=$Bindings","-JourneyReport=$report",'-Unattended','-NoSplash','-UTF8Output','-JourneyImportSources')
if ($ImportSourcesOnly) { $arguments+='-JourneySourcesOnly' }
if ($ImportJournalData) {
    $generator=Join-Path $PSScriptRoot 'import_journey.py'
    $arguments=@($script:ProjectFile,"-ExecutePythonScript=$generator","-JourneyDataReport=$report",'-Unattended','-NoSplash','-UTF8Output')
}
$mutex=[Threading.Mutex]::new($false,'Local\PathOfDawnUnrealEditorAssets')
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); throw 'Another project asset import is running.' }
$previousBindings=[Environment]::GetEnvironmentVariable('WORD_JOURNEY_BINDINGS','Process')
$previousReport=[Environment]::GetEnvironmentVariable('WORD_JOURNEY_REPORT','Process')
try {
    # A process-local transport avoids Windows command-line quoting ambiguity
    # for user project/license paths with spaces. CLI arguments remain usable.
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_BINDINGS',$Bindings,'Process')
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REPORT',$report,'Process')
    Invoke-DawnCommand $editor $arguments (Join-Path $evidence 'editor-import.log')
    Assert-DawnFile $report
    $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    $allowed=if ($ImportJournalData) { @('CREATED','PRESERVED') } elseif ($ImportSourcesOnly) { @('SOURCE_IMPORT_COMPLETE') } else { @('BENCHMARK_PREPARED_UNREVIEWED') }
    if ($result.status -notin $allowed) { throw "Editor reported $($result.status). See $report" }
    Write-Host "Editor report: $report. Actual visual approval is a separate graphics gate."
} finally {
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_BINDINGS',$previousBindings,'Process')
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REPORT',$previousReport,'Process')
    $mutex.ReleaseMutex(); $mutex.Dispose()
}
