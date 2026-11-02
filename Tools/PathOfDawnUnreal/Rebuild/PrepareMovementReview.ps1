#requires -Version 5.1
# Local authoring/review only. Keeps the installed game, service and sample originals.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$Revision,
    [string]$SampleRoot='C:\PathOfDawn\Samples\GameAnimationSample',
    [string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8',
    [string]$OutputRoot='C:\PathOfDawn\Reports\MovementReview',
    [string]$LocalToolsRoot='C:\PathOfDawn\Tools\MovementReview',
    [ValidateRange(10,1800)][int]$TimeoutSeconds=600,
    [switch]$PrepareOnly,
    [switch]$RunOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$previousModulePath=[Environment]::GetEnvironmentVariable('PSModulePath','Process')
if ($PSVersionTable.PSVersion.Major -lt 6) {
    # A .cmd launched from pwsh can inherit only PowerShell 7 module paths.
    # Prefer this Windows PowerShell's own modules for Get-FileHash et al.
    [Environment]::SetEnvironmentVariable('PSModulePath',([IO.Path]::Combine($PSHOME,'Modules')+';'+$previousModulePath),'Process')
}
$pins=@{
    'movement_review.py'='1d7189654c83f2ed34d956d249979e7c97e43d62f5124ee0e34b8be8a7a95e01'
    'inspect_sample.py'='11c04dbc94ab5803bf912961ed1a2856aae8b225f77ec9ef670bd053c0a00fd7'
    'WindowsProcessLauncher.cs'='068e9628308f39cd50f74c35c6b8f253794852fe3644266142aae18bd8482b35'
}
$worker=$null; $probe=$null; $probeHash=$null; $exitCode=1; $mutex=$null; $ownsMutex=$false
$previous=@{}
$variables=@('WORD_JOURNEY_REVIEW_REPORT','WORD_JOURNEY_REVIEW_PROJECT','WORD_JOURNEY_REVIEW_STATE','WORD_JOURNEY_REVIEW_PHASE')
foreach ($name in $variables) { $previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
function Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Native-Arguments([string[]]$Values) {
    (@(foreach ($value in $Values) {
        $escaped=[regex]::Replace($value,'(\\*)"','$1$1\"')
        $escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
        '"'+$escaped+'"'
    }) -join ' ')
}
function Find-Sample([string]$Root) {
    if (Test-Path -LiteralPath $Root -PathType Leaf) {
        if ([IO.Path]::GetExtension($Root) -ne '.uproject') { throw 'SampleRoot must name the sample directory or its .uproject.' }
        return (Resolve-Path -LiteralPath $Root).Path
    }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "Sample not found: $Root" }
    $queue=New-Object 'Collections.Generic.Queue[object]'; $queue.Enqueue(@([IO.Path]::GetFullPath($Root),0)); $found=@()
    while ($queue.Count) {
        $entry=$queue.Dequeue()
        foreach ($file in @(Get-ChildItem -LiteralPath $entry[0] -Filter '*.uproject' -File)) {
            if ($file.Name -notlike 'WJInspect_*.uproject') { $found+=$file.FullName }
        }
        if ($entry[1] -lt 3) {
            foreach ($child in @(Get-ChildItem -LiteralPath $entry[0] -Directory)) {
                if ($child.Name -notin @('Content','Config','Plugins','Saved','Binaries','Intermediate','DerivedDataCache','.git') -and -not ($child.Attributes -band [IO.FileAttributes]::ReparsePoint)) { $queue.Enqueue(@($child.FullName,($entry[1]+1))) }
            }
        }
    }
    if ($found.Count -ne 1) { throw "Expected one original sample project, found $($found.Count). Use -SampleRoot with its exact .uproject path." }
    return $found[0]
}
function Pinned-File([string]$Name,[string]$RepositoryPath) {
    $path=Join-Path $cache $Name
    if (-not (Test-Path -LiteralPath $path)) {
        $source=Join-Path $PSScriptRoot $Name
        if ($Name -eq 'WindowsProcessLauncher.cs') { $source=Join-Path $PSScriptRoot '../WindowsProcessLauncher.cs' }
        $temporary=Join-Path $cache ([guid]::NewGuid().ToString('N')+'.tmp')
        try {
            if (Test-Path -LiteralPath $source) { [IO.File]::Copy($source,$temporary,$false) }
            else {
                [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -UseBasicParsing -Uri ('https://raw.githubusercontent.com/ka8877/unreal_yesu/'+$Revision+'/'+$RepositoryPath) -OutFile $temporary -TimeoutSec 60
            }
            if ((Get-Item -LiteralPath $temporary).Length -gt 262144 -or (Sha256 $temporary) -ne $pins[$Name]) { throw "Tool hash mismatch: $Name. Nothing from this file was run." }
            [IO.File]::Move($temporary,$path)
        } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
    }
    if ((Sha256 $path) -ne $pins[$Name]) { throw "Changed local tool preserved: $path" }
    return $path
}
function Save-Json([string]$Path,$Value) {
    $temporary=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    [IO.File]::WriteAllText($temporary,($Value | ConvertTo-Json -Depth 32),(New-Object Text.UTF8Encoding($false)))
    try {
        if (Test-Path -LiteralPath $Path) {
            # Windows PowerShell 5.1 binds a null backup path as an invalid
            # empty string. An explicit unique backup works in both shells.
            $backup=$Path+'.'+[guid]::NewGuid().ToString('N')+'.backup'
            [IO.File]::Replace($temporary,$Path,$backup)
            [IO.File]::Delete($backup)
        } else { [IO.File]::Move($temporary,$Path) }
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
}
function Invoke-EditorPhase([string]$Phase) {
    $report=Join-Path $run $(if ($Phase -eq 'verify') {'movement-review.json'} else {'prepare.json'})
    $engineLog=Join-Path $run ($Phase+'-engine.log')
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REVIEW_PHASE',$Phase,'Process')
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REVIEW_REPORT',$report,'Process')
    $values=@($editor,$probe,'-run=pythonscript',"-script=$python",'-Unattended','-NoSplash','-NullRHI','-UTF8Output','-stdout',"-ABSLOG=$engineLog",("-UserDir="+(Join-Path $run 'EditorHost')))
    Write-Host "$Phase with Unreal. Metadata/setup only, not a graphics test. Log: $engineLog"
    $script:worker=[PathOfDawn.Tools.WindowsProcessLauncher]::Start($editor,(Native-Arguments $values),$EngineRoot,(Join-Path $run ($Phase+'-stdout.log')),(Join-Path $run ($Phase+'-stderr.log')),$true)
    $deadline=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds); $next=[DateTime]::UtcNow.AddSeconds(15)
    while (-not $script:worker.WaitForExit(1000)) {
        if ([DateTime]::UtcNow -ge $deadline) { $script:worker.Kill(); throw 'Movement preparation timed out. Only its own worker was stopped.' }
        if ([DateTime]::UtcNow -ge $next) { Write-Host 'Unreal is still loading/checking the character and motion assets...'; $next=[DateTime]::UtcNow.AddSeconds(15) }
    }
    if (Test-Path -LiteralPath $report) {
        $value=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($value.status -eq 'FAILED') { throw "Unreal: $($value.error). Report: $report" }
    } else { throw "Unreal did not write $report (exit $($script:worker.ExitCode)). Full log: $engineLog" }
    $expected=if ($Phase -eq 'verify') {'MOTION_REVIEW_ASSETS_RELOADED'} else {'MOTION_REVIEW_ASSETS_SAVED'}
    if ($script:worker.ExitCode -ne 0 -or $value.schemaVersion -ne 1 -or $value.status -ne $expected) { throw "Unreal phase $Phase failed (exit $($script:worker.ExitCode), status $($value.status)). Report: $report" }
    if ($value.graphicsVerified -ne $false -or $value.sourceSampleAssetsModified -ne $false -or $value.narrativeDemoComplete -ne $false) { throw 'Unexpected report scope; preparation cannot approve graphics or replace the demo.' }
    if ($Phase -eq 'verify' -and @($value.created).Count) { throw 'Reload unexpectedly created assets; graphical launch was blocked.' }
    return $value
}
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Run this on the Windows Unreal PC.' }
    if ($RunOnly -and $PrepareOnly) { throw 'RunOnly and PrepareOnly cannot be combined.' }
    $project=Find-Sample $SampleRoot; $projectDirectory=Split-Path -Parent $project
    $hasher=[Security.Cryptography.SHA256]::Create()
    try { $key=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($projectDirectory.ToLowerInvariant())))).Replace('-','').Substring(0,24) }
    finally { $hasher.Dispose() }
    $mutex=New-Object Threading.Mutex($false,('Local\WordJourney-MovementReview-'+$key))
    try { $ownsMutex=$mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $ownsMutex=$true }
    if (-not $ownsMutex) { throw 'Another movement preparation is modifying this sample. Wait for that tool to finish.' }
    $projectHash=Sha256 $project
    $config=Join-Path $projectDirectory 'Config/DefaultEngine.ini'; $configHash=Sha256 $config
    $version=Get-Content -LiteralPath (Join-Path $EngineRoot 'Engine/Build/Build.version') -Raw | ConvertFrom-Json
    if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8 -or $version.BranchName -match 'Preview|ue5-main') { throw 'Use the installed stable UE5.8 engine.' }
    $descriptor=Get-Content -LiteralPath $project -Raw -Encoding UTF8 | ConvertFrom-Json
    $association=$descriptor.PSObject.Properties['EngineAssociation']
    if ($association -and $association.Value -match '^\d+\.\d+' -and $association.Value -notmatch '^5\.8(?:\.\d+)?$') { throw 'Sample engine association differs from UE5.8. Original preserved, no upgrade attempted.' }
    $modules=$descriptor.PSObject.Properties['Modules']
    if ($modules -and $null -ne $modules.Value) {
        foreach ($module in @($modules.Value)) {
            if (-not (Test-Path -LiteralPath (Join-Path $projectDirectory "Binaries/Win64/UnrealEditor-$($module.Name).dll"))) { throw 'Sample contains an unbuilt native module. Open/build the matching sample first; source files were preserved.' }
        }
    }
    $editor=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $gameEditor=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
    if (-not (Test-Path -LiteralPath $editor) -or -not (Test-Path -LiteralPath $gameEditor)) { throw 'Unreal Editor executables not found at EngineRoot.' }
    $OutputRoot=[IO.Path]::GetFullPath($OutputRoot); [void][IO.Directory]::CreateDirectory($OutputRoot)
    $sessionFile=Join-Path $OutputRoot 'session.json'
    if (Test-Path -LiteralPath $sessionFile) {
        $session=Get-Content -LiteralPath $sessionFile -Raw | ConvertFrom-Json
        $existing=Get-Process -Id $session.pid -ErrorAction SilentlyContinue
        if ($existing -and $existing.StartTime.ToUniversalTime().ToString('O') -eq $session.startedUtc -and $existing.Path -eq $session.executable) {
            Write-Host 'The previous movement review is still running. Close its game window before preparing/starting another one.'
            $exitCode=0; exit $exitCode
        }
    }
    $cache=Join-Path ([IO.Path]::GetFullPath($LocalToolsRoot)) $Revision.ToLowerInvariant(); [void][IO.Directory]::CreateDirectory($cache)
    $python=Pinned-File 'movement_review.py' 'Tools/PathOfDawnUnreal/Rebuild/movement_review.py'
    $null=Pinned-File 'inspect_sample.py' 'Tools/PathOfDawnUnreal/Rebuild/inspect_sample.py'
    $native=Pinned-File 'WindowsProcessLauncher.cs' 'Tools/PathOfDawnUnreal/WindowsProcessLauncher.cs'
    if (-not ('PathOfDawn.Tools.WindowsProcessLauncher' -as [type])) { Add-Type -Path $native }
    $cachedLauncher=Join-Path $cache 'PrepareMovementReview.ps1'
    if (-not (Test-Path -LiteralPath $cachedLauncher)) { [IO.File]::Copy($PSCommandPath,$cachedLauncher,$false) }
    if ((Sha256 $cachedLauncher) -ne (Sha256 $PSCommandPath)) { throw 'Changed cached launcher preserved; choose a clean tool revision.' }
    $run=Join-Path $OutputRoot ((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)); [void][IO.Directory]::CreateDirectory($run)
    $state=Join-Path $OutputRoot 'State'; [void][IO.Directory]::CreateDirectory($state)
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REVIEW_PROJECT',$projectDirectory,'Process')
    [Environment]::SetEnvironmentVariable('WORD_JOURNEY_REVIEW_STATE',$state,'Process')
    $plugins=@(); if ($descriptor.PSObject.Properties['Plugins']) { $plugins=@($descriptor.Plugins) }
    foreach ($name in @('PythonScriptPlugin','EditorScriptingUtilities')) {
        $plugin=@($plugins | Where-Object {$_.Name -eq $name})
        if ($plugin.Count) { $plugin[0] | Add-Member -NotePropertyName Enabled -NotePropertyValue $true -Force }
        else { $plugins+=[pscustomobject]@{Name=$name;Enabled=$true} }
    }
    $descriptor | Add-Member -NotePropertyName Plugins -NotePropertyValue $plugins -Force
    $probe=Join-Path $projectDirectory ('WJInspect_'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.uproject')
    $stream=[IO.File]::Open($probe,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $bytes=[Text.Encoding]::UTF8.GetBytes(($descriptor | ConvertTo-Json -Depth 64)); $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
    $probeHash=Sha256 $probe
    if (-not $RunOnly) { $prepared=Invoke-EditorPhase 'prepare' }
    $verified=Invoke-EditorPhase 'verify'
    if ((Sha256 $project) -ne $projectHash -or (Sha256 $config) -ne $configHash) { throw 'Original project/config changed concurrently. Preserved; review before launching.' }
    if (-not $RunOnly -and ($prepared.launch.gameModeClass -ne $verified.launch.gameModeClass -or $prepared.launch.sourcePawn -ne $verified.launch.sourcePawn)) { throw 'Fresh-process references differ from preparation. Launch blocked.' }
    if ($verified.launch.map -notmatch '^/Game/[A-Za-z0-9_/]+$' -or $verified.launch.gameModeClass -notmatch '^/Game/WordJourneyDev/MovementReview/r_[0-9a-f]{16}/BP_MovementReview\.BP_MovementReview_C$') { throw 'Invalid review launch paths.' }
    $wrapper=Join-Path $OutputRoot 'Run-MovementReview.cmd'; $wrapperIndex=Join-Path $OutputRoot 'wrapper-owner.json'
    if (Test-Path -LiteralPath $wrapper) {
        if (-not (Test-Path -LiteralPath $wrapperIndex)) { throw 'Existing unowned review shortcut preserved.' }
        $owner=Get-Content -LiteralPath $wrapperIndex -Raw | ConvertFrom-Json
        if ((Sha256 $wrapper) -ne $owner.sha256) { throw 'User-edited review shortcut preserved.' }
    }
    $cmdArgs=@($cachedLauncher,'-Revision',$Revision,'-SampleRoot',$project,'-EngineRoot',$EngineRoot,'-OutputRoot',$OutputRoot,'-LocalToolsRoot',$LocalToolsRoot,'-RunOnly')
    $cmdValues=@(foreach ($value in $cmdArgs) {'"'+$value.Replace('%','%%')+'"'}) -join ' '
    $cmd="@echo off`r`nchcp 65001 >nul`r`nsetlocal DisableDelayedExpansion`r`npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $cmdValues`r`nset `"WJ_REVIEW_EXIT=%ERRORLEVEL%`"`r`nif not `"%WJ_REVIEW_EXIT%`"==`"0`" pause`r`nexit /b %WJ_REVIEW_EXIT%`r`n"
    [IO.File]::WriteAllText($wrapper,$cmd,(New-Object Text.UTF8Encoding($false)))
    Save-Json $wrapperIndex ([ordered]@{sha256=(Sha256 $wrapper);generator='word-journey-review-shortcut-v1'})
    Write-Host "Assets saved and reloaded in a fresh Editor. Report: $(Join-Path $run 'movement-review.json')"
    Write-Host "Next launch, no downloads: $wrapper"
    if (-not $PrepareOnly) {
        $values=@($gameEditor,$project,($verified.launch.map+'?game='+$verified.launch.gameModeClass),'-game','-windowed','-ResX=1280','-ResY=720','-UTF8Output',("-UserDir="+(Join-Path $OutputRoot 'GameHost')),("-ABSLOG="+(Join-Path $run 'game-engine.log')))
        $game=[PathOfDawn.Tools.WindowsProcessLauncher]::Start($gameEditor,(Native-Arguments $values),$EngineRoot,(Join-Path $run 'game-stdout.log'),(Join-Path $run 'game-stderr.log'),$false)
        try {
            if ($game.WaitForExit(2000)) { throw "Rendered review exited during startup (exit $($game.ExitCode)). See $(Join-Path $run 'game-engine.log')" }
            Save-Json $sessionFile ([ordered]@{pid=$game.Id;startedUtc=$game.StartTime.ToUniversalTime().ToString('O');executable=$gameEditor;renderingRequested=$true;graphicsVerified=$false;report=(Join-Path $run 'movement-review.json')})
        } catch { if (-not $game.HasExited) { $game.Kill(); [void]$game.WaitForExit(5000) }; throw }
        Write-Host 'Rendered sample movement review requested. Check the actual game window and WASD/mouse input. This is not the rebuilt narrative demo.'
    }
    $exitCode=0
} catch { Write-Host "Movement review stopped: $($_.Exception.Message)" }
finally {
    if ($worker -and -not $worker.HasExited) { $worker.Kill(); [void]$worker.WaitForExit(5000) }
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
    [Environment]::SetEnvironmentVariable('PSModulePath',$previousModulePath,'Process')
    if ($probe -and (Test-Path -LiteralPath $probe)) {
        if ($probeHash -and (Sha256 $probe) -eq $probeHash) { Remove-Item -LiteralPath $probe }
        else { Write-Host "Edited temporary descriptor preserved: $probe" }
    }
    if ($mutex) { if ($ownsMutex) { $mutex.ReleaseMutex() }; $mutex.Dispose() }
}
exit $exitCode
