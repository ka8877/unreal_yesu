#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [string]$BuildId, [string]$ExistingBuildId, [string]$SmokeReport, [string]$SmokeCommand, [switch]$StartStreaming)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
$mutex = [Threading.Mutex]::new($false,'Local\PathOfDawnUnrealUpdate')
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); throw 'Another demo update is in progress.' }
try {
    if ($ExistingBuildId) { $BuildId = $ExistingBuildId }
    else {
        if (-not $BuildId) { $BuildId = New-DawnBuildId }
        & "$PSScriptRoot/BuildEditor.ps1" -EngineRoot $resolved
        & "$PSScriptRoot/GenerateDemoAssets.ps1" -EngineRoot $resolved -SkipCompile
        & "$PSScriptRoot/TestDemo.ps1" -SourceOnly -RequireArt
        & "$PSScriptRoot/BuildDemo.ps1" -EngineRoot $resolved -BuildId $BuildId
    }
    $candidate = Get-DawnCandidate $BuildId
    if ($SmokeCommand) {
        Assert-DawnFile $SmokeCommand
        $SmokeReport = Join-Path $candidate 'smoke-report.json'
        # A project-specific real GUI test driver can be provided. No simulated pass is supplied.
        & $SmokeCommand -BuildDirectory $candidate -ReportPath $SmokeReport
        if (-not $?) { throw 'Graphical smoke driver failed.' }
    }
    if (-not $SmokeReport) { throw "Candidate $BuildId is built; old service is still running. Perform graphical checks, then rerun with -ExistingBuildId $BuildId -SmokeReport <report.json>. No media check was inferred." }
    & "$PSScriptRoot/TestDemo.ps1" -BuildId $BuildId -SmokeReport $SmokeReport -RequireArt
    $currentPath = Join-Path $script:StreamRoot 'runtime/current.json'
    $previous = if (Test-Path -LiteralPath $currentPath) { Get-Content -Raw -LiteralPath $currentPath | ConvertFrom-Json } else { $null }
    $wasRunning = Test-Path -LiteralPath (Join-Path $script:StreamRoot 'runtime/signalling.process.json')
    $restart = $StartStreaming -or $wasRunning
    try {
        if ($restart) { & "$PSScriptRoot/StopStreaming.ps1" }
        if ($previous) { Write-DawnJson (Join-Path $script:StreamRoot 'runtime/previous.json') $previous }
        Write-DawnJson $currentPath @{buildId=$BuildId; switchedUtc=[DateTime]::UtcNow.ToString('O'); payloadSha256=(Get-DawnManifest $candidate).payloadSha256}
        if ($restart) { & "$PSScriptRoot/StartStreaming.ps1" -BuildId $BuildId -EngineRoot $resolved }
    } catch {
        $failure = $_
        & "$PSScriptRoot/StopStreaming.ps1"
        if ($previous) {
            Write-DawnJson $currentPath $previous
            if ($restart) { & "$PSScriptRoot/StartStreaming.ps1" -BuildId $previous.buildId -EngineRoot $resolved }
        } elseif (Test-Path -LiteralPath $currentPath) { Remove-Item -LiteralPath $currentPath }
        throw $failure
    }
    Write-Host "Active build $BuildId. Address is unchanged if streaming was started: http://127.0.0.1:8080/. Reconnect and compare the game's visible build ID."
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
