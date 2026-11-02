#requires -Version 5.1
# Standalone, small authoring tool. No project downloads, builds or asset saves.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$Revision,
    [string]$SampleRoot='C:\PathOfDawn\Samples\GameAnimationSample',
    [string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8',
    [string]$OutputRoot='C:\PathOfDawn\Reports\GameAnimationSample',
    [ValidateRange(10,1800)][int]$TimeoutSeconds=600
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ExpectedPythonSha256='dd3b98b03416d90e248620e22babfbf5bb625f4c70f3e41b7b8107fc84cd80aa'
$process=$null; $probe=$null; $probeHash=$null; $exitCode=1
$previousReport=[Environment]::GetEnvironmentVariable('WORD_JOURNEY_SAMPLE_REPORT','Process')
function Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Join-NativeArguments([string[]]$Values) {
    (@(foreach ($value in $Values) {
        $escaped=[regex]::Replace($value,'(\\*)"','$1$1\"')
        $escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
        '"'+$escaped+'"'
    }) -join ' ')
}
function Find-SampleProject([string]$Root) {
    if (Test-Path -LiteralPath $Root -PathType Leaf) {
        if ([IO.Path]::GetExtension($Root) -ne '.uproject') { throw 'SampleRoot must name the sample folder or its .uproject file.' }
        return (Resolve-Path -LiteralPath $Root).Path
    }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "Sample folder not found: $Root" }
    $queue=New-Object 'Collections.Generic.Queue[object]'
    $queue.Enqueue(@([IO.Path]::GetFullPath($Root),0))
    $found=@()
    while ($queue.Count) {
        $entry=$queue.Dequeue(); $directory=$entry[0]; $depth=$entry[1]
        foreach ($file in @(Get-ChildItem -LiteralPath $directory -Filter '*.uproject' -File)) {
            if ($file.Name -notlike 'WJInspect_*.uproject') { $found+=$file.FullName }
        }
        if ($depth -lt 3) {
            foreach ($child in @(Get-ChildItem -LiteralPath $directory -Directory)) {
                if ($child.Name -notin @('Content','Config','Plugins','Saved','Binaries','Intermediate','DerivedDataCache','.git') -and -not ($child.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                    $queue.Enqueue(@($child.FullName,($depth+1)))
                }
            }
        }
    }
    if ($found.Count -ne 1) { throw "Expected one sample .uproject, found $($found.Count). Pass its exact path with -SampleRoot." }
    return $found[0]
}
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'This launcher requires the Windows PC with Unreal installed.' }
    $project=Find-SampleProject $SampleRoot
    $projectDirectory=Split-Path -Parent $project
    $beforeHash=Sha256 $project
    $descriptor=Get-Content -LiteralPath $project -Raw -Encoding UTF8 | ConvertFrom-Json
    $engineFile=Join-Path $EngineRoot 'Engine/Build/Build.version'
    $editor=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    if (-not (Test-Path -LiteralPath $editor -PathType Leaf) -or -not (Test-Path -LiteralPath $engineFile -PathType Leaf)) { throw 'Unreal Editor/Build.version not found at EngineRoot.' }
    $version=Get-Content -LiteralPath $engineFile -Raw | ConvertFrom-Json
    if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8 -or $version.BranchName -match 'Preview|ue5-main') { throw 'This inspector targets the installed stable UE5.8 engine.' }
    $association=$descriptor.PSObject.Properties['EngineAssociation']
    if ($association -and $association.Value -match '^\d+\.\d+' -and $association.Value -notmatch '^5\.8(?:\.\d+)?$') {
        throw 'The sample is associated with a different engine version. Download its UE5.8 version; the original project will not be upgraded.'
    }
    $modules=$descriptor.PSObject.Properties['Modules']
    if ($modules) {
        foreach ($module in @($modules.Value)) {
            if (-not (Test-Path -LiteralPath (Join-Path $projectDirectory "Binaries/Win64/UnrealEditor-$($module.Name).dll"))) {
                throw 'This sample contains an unbuilt C++ module. Open/build that sample with its matching engine first; the inspector does not rebuild it.'
            }
        }
    }
    # Never change the original descriptor to enable Python. A short-lived
    # sibling descriptor uses the same Content/Plugins but no level is loaded.
    $plugins=@()
    if ($descriptor.PSObject.Properties['Plugins']) { $plugins=@($descriptor.Plugins) }
    foreach ($name in @('PythonScriptPlugin','EditorScriptingUtilities')) {
        $existing=@($plugins | Where-Object { $_.Name -eq $name })
        if ($existing.Count) { $existing[0] | Add-Member -NotePropertyName Enabled -NotePropertyValue $true -Force }
        else { $plugins+=[pscustomobject]@{Name=$name;Enabled=$true} }
    }
    $descriptor | Add-Member -NotePropertyName Plugins -NotePropertyValue $plugins -Force
    $OutputRoot=[IO.Path]::GetFullPath($OutputRoot)
    $run=Join-Path $OutputRoot ((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8))
    [void][IO.Directory]::CreateDirectory($run)
    $report=Join-Path $run 'sample-inventory.json'
    $stdout=Join-Path $run 'editor-stdout.log'; $stderr=Join-Path $run 'editor-stderr.log'
    $engineLog=Join-Path $run 'editor-engine.log'
    $python=Join-Path $PSScriptRoot 'inspect_sample.py'
    if (-not (Test-Path -LiteralPath $python)) {
        $cache=Join-Path ([IO.Path]::GetTempPath()) ('WordJourney-Inspector-'+$Revision.ToLowerInvariant())
        [void][IO.Directory]::CreateDirectory($cache)
        $python=Join-Path $cache 'inspect_sample.py'
        if (-not (Test-Path -LiteralPath $python)) {
            $temporary=Join-Path $cache ([guid]::NewGuid().ToString('N')+'.tmp')
            try {
                [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
                $url='https://raw.githubusercontent.com/ka8877/unreal_yesu/'+$Revision+'/Tools/PathOfDawnUnreal/Rebuild/inspect_sample.py'
                Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temporary -TimeoutSec 60
                if ((Get-Item -LiteralPath $temporary).Length -gt 262144 -or (Sha256 $temporary) -ne $ExpectedPythonSha256) { throw 'Inspector Python download hash did not match. Nothing was run.' }
                [IO.File]::Move($temporary,$python)
            } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
        }
    }
    if ((Sha256 $python) -ne $ExpectedPythonSha256) { throw 'Inspector Python differs from the pinned code. Preserved without running or overwriting.' }
    $probe=Join-Path $projectDirectory ('WJInspect_'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.uproject')
    $stream=[IO.File]::Open($probe,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes(($descriptor | ConvertTo-Json -Depth 64))
        $stream.Write($bytes,0,$bytes.Length)
    } finally { $stream.Dispose() }
    $probeHash=Sha256 $probe
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_SAMPLE_REPORT',$report,'Process')
    $arguments=@($probe,'-run=pythonscript',"-script=$python",'-Unattended','-NoSplash','-NullRHI','-UTF8Output','-stdout',"-ABSLOG=$engineLog",("-UserDir="+(Join-Path $run 'Host')))
    Write-Host 'Inspecting sample assets with Unreal. Metadata only; no graphics or gameplay test.'
    Write-Host "Full log: $engineLog"
    $process=Start-Process -FilePath $editor -ArgumentList (Join-NativeArguments $arguments) -WorkingDirectory $EngineRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    # Windows PowerShell 5.1 otherwise loses ExitCode after a manual wait.
    # Hold the native handle before waiting; do not use -Wait, which can wait
    # indefinitely for persistent Editor descendants such as ZenServer.
    $nativeHandle=$process.Handle
    $deadline=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds); $nextUpdate=[DateTime]::UtcNow.AddSeconds(15)
    while (-not $process.WaitForExit(1000)) {
        if ([DateTime]::UtcNow -ge $deadline) { $process.Kill(); throw 'Sample inspection timed out. Only this inspector Editor process was stopped.' }
        if ([DateTime]::UtcNow -ge $nextUpdate) { Write-Host 'Unreal is still scanning/loading the selected assets...'; $nextUpdate=[DateTime]::UtcNow.AddSeconds(15) }
    }
    if ((Sha256 $project) -ne $beforeHash) { throw 'The original descriptor changed during inspection. It was preserved; review concurrent edits.' }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) {
        if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Tail 16 | ForEach-Object { Write-Host $_ } }
        if (Test-Path -LiteralPath $engineLog) { Get-Content -LiteralPath $engineLog -Tail 20 | ForEach-Object { Write-Host $_ } }
        throw "Editor did not complete inspection (exit $($process.ExitCode)). See $run"
    }
    $result=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($result.schemaVersion -ne 1 -or $result.status -notin @('SAMPLE_ASSETS_INSPECTED','PARTIAL_INVENTORY')) {
        $detail=if ($result.PSObject.Properties['error']) { ': '+$result.error } else { '' }
        throw "Inspector reported $($result.status)$detail. See $report"
    }
    if ($result.graphicsVerified -ne $false -or $result.sourceAssetsSaved -ne $false) { throw 'Unexpected inspection report scope; no graphics or asset-save approval is accepted.' }
    Write-Host "Status: $($result.status)"
    Write-Host "Loaded meshes: $(@($result.loadedMeshes).Count); animation candidates: $(@($result.loadedAnimations).Count)"
    Write-Host "Report to share in this chat: $report"
    Write-Host 'The report/logs stay on this PC. Nothing was uploaded; no game files were rebuilt or migrated.'
    $exitCode=if ($result.status -eq 'SAMPLE_ASSETS_INSPECTED') {0} else {2}
} catch {
    Write-Host "Inspection stopped: $($_.Exception.Message)"
} finally {
    if ($process -and -not $process.HasExited) { $process.Kill(); [void]$process.WaitForExit(5000) }
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_SAMPLE_REPORT',$previousReport,'Process')
    if ($probe -and (Test-Path -LiteralPath $probe)) {
        if ($probeHash -and (Sha256 $probe) -eq $probeHash) { Remove-Item -LiteralPath $probe }
        else { Write-Host "Temporary descriptor was edited; preserved: $probe" }
    }
}
exit $exitCode
