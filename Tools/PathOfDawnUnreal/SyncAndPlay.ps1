#requires -Version 5.1
# Immutable GitHub source snapshots; no Git installation or manual ZIP extraction.
[CmdletBinding()]
param(
    [string]$InstallRoot='C:\PathOfDawn',
    [string]$CommitSha,
    [string]$EngineRoot,
    [switch]$Streaming,
    [switch]$DownloadOnly
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2

function Write-SyncJson([string]$Path, $Value) {
    $temporary="$Path.$([guid]::NewGuid().ToString('N')).tmp"
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding($false)))
    if (Test-Path -LiteralPath $Path) {
        $backup="$Path.$([guid]::NewGuid().ToString('N')).old"
        [IO.File]::Replace($temporary,$Path,$backup)
        [IO.File]::Delete($backup)
    }
    else { [IO.File]::Move($temporary,$Path) }
}
function Assert-SyncRoot([string]$Path) {
    if (-not [IO.Path]::IsPathRooted($Path)) { throw 'InstallRoot must be an absolute path.' }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar)
    if ($full -match '[^\x20-\x7E]' -or $full -match '(^|[\\/])OneDrive([^\\/]*)([\\/]|$)') {
        throw 'Use an ASCII path outside OneDrive, for example C:\PathOfDawn. This avoids the previous Unreal compiler path failure.'
    }
    if ($full.Length -gt 80 -or $full.Length -lt 4) { throw 'Choose a short dedicated installation folder, for example C:\PathOfDawn.' }
    if ($full -match '["%&!|<>^`;$]') { throw 'InstallRoot contains characters unsafe for the Windows launcher. Use C:\PathOfDawn.' }
    return $full
}
function Expand-SyncArchive([string]$ArchivePath,[string]$Destination,[string]$ExpectedCommit) {
    if ($ExpectedCommit -cnotmatch '^[a-f0-9]{40}$') { throw 'A full lowercase commit SHA is required.' }
    if (Test-Path -LiteralPath $Destination) { throw 'Extraction destination must be new; existing files are never overwritten.' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ArchivePath)
    $prefix="unreal_yesu-$ExpectedCommit/"
    $seen=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    $entries=@(); $total=[long]0
    try {
        if ($zip.Entries.Count -lt 5 -or $zip.Entries.Count -gt 50000) { throw 'Unexpected source archive entry count.' }
        foreach ($entry in $zip.Entries) {
            if (-not $entry.FullName.StartsWith($prefix,[StringComparison]::Ordinal)) { throw 'Archive belongs to a different repository or commit.' }
            $relative=$entry.FullName.Substring($prefix.Length)
            if (-not $relative) { continue }
            $isDirectory=$relative.EndsWith('/')
            $relative=$relative.TrimEnd('/')
            $parts=$relative.Split('/')
            if ($relative -match '[\\:\x00-\x1F<>"|?*]' -or @($parts | Where-Object { $_ -eq '' -or $_ -eq '.' -or $_ -eq '..' -or $_ -match '[ .]$' -or $_ -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)' }).Count) {
                throw "Unsafe archive path: $relative"
            }
            if (-not $seen.Add($relative)) { throw "Duplicate archive path: $relative" }
            if ((($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000) { throw "Symbolic links are not accepted: $relative" }
            $total += $entry.Length
            if ($entry.Length -gt 536870912 -or $total -gt 2147483648) { throw 'Source archive exceeds the expected size limit.' }
            $entries += [pscustomobject]@{entry=$entry;relative=$relative;directory=$isDirectory}
        }
        foreach ($required in @('Start-PathOfDawn.cmd','Tools/PathOfDawnUnreal/StartHere.ps1','Tools/PathOfDawnUnreal/SyncAndPlay.ps1','Tools/PathOfDawnUnreal/Bootstrap.ps1','Tools/PathOfDawnUnreal/StopManagedSession.ps1','Games/PathOfDawnUnreal/PathOfDawnUnreal.uproject','SourceArt/PathOfDawnUnreal/Narrative/episode.json','SourceArt/PathOfDawnUnreal/VisualV8/Illustrations/IL_Title_Dawn.png')) {
            if (-not $seen.Contains($required)) { throw "Required source file is missing: $required" }
        }
        [void][IO.Directory]::CreateDirectory($Destination)
        $hashes=@()
        foreach ($item in $entries) {
            $target=Join-Path $Destination $item.relative
            if ($item.directory) { [void][IO.Directory]::CreateDirectory($target); continue }
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            $inputStream=$item.entry.Open(); $outputStream=$null
            try { $outputStream=[IO.File]::Open($target,[IO.FileMode]::CreateNew); $inputStream.CopyTo($outputStream) }
            finally { if ($outputStream) {$outputStream.Dispose()}; $inputStream.Dispose() }
            # Generated evidence is intentionally mutable. Code/config/source art are not.
            if ($item.relative -notmatch '^(Docs/PathOfDawnUnreal/Evidence/|Builds/)') {
                $hashes += [ordered]@{path=$item.relative;sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()}
            }
            if ($item.relative -match '^SourceArt/.*\.(png|fbx|otf|wav|blend)$' -and $item.entry.Length -lt 1024) {
                if (([IO.File]::ReadAllText($target)) -match '^version https://git-lfs.github.com/spec/v1') { throw "Git LFS pointer found instead of the real asset: $($item.relative)" }
            }
        }
        Write-SyncJson (Join-Path $Destination '.dawn-source.json') ([ordered]@{schema=1;repository='ka8877/unreal_yesu';commit=$ExpectedCommit;downloadedUtc=[DateTime]::UtcNow.ToString('O');files=$hashes})
    } finally { $zip.Dispose() }
}
function Assert-SyncSource([string]$Root,[string]$ExpectedCommit) {
    $receipt=Join-Path $Root '.dawn-source.json'
    if (-not (Test-Path -LiteralPath $receipt)) { throw "Folder exists without a valid download receipt. It was preserved: $Root" }
    $record=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if ($record.schema -ne 1 -or $record.repository -ne 'ka8877/unreal_yesu' -or $record.commit -ne $ExpectedCommit) { throw 'Source receipt does not match the requested commit.' }
    foreach ($file in $record.files) {
        if ($file.path -match '(^|/)\.\.(/|$)|[\\:]' -or [IO.Path]::IsPathRooted($file.path)) { throw 'Invalid source receipt path.' }
        $path=Join-Path $Root $file.path
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $file.sha256) {
            throw "Local source changes were preserved: $path. Use a different InstallRoot for an unmodified copy."
        }
    }
}
function Get-SyncBuild([string]$Root) {
    $directory=Join-Path $Root 'Builds/PathOfDawnUnreal/Windows'
    if (-not (Test-Path -LiteralPath $directory)) { return $null }
    foreach ($candidate in @(Get-ChildItem -LiteralPath $directory -Directory | Sort-Object LastWriteTimeUtc -Descending)) {
        $path=Join-Path $candidate.FullName 'build-manifest.json'
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $manifest=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        if ($manifest.buildId -ne $candidate.Name -or $manifest.buildId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$') { throw "Invalid build manifest: $path" }
        if ($manifest.runtimeExecutable -match '(^|[\\/])\.\.([\\/]|$)|:' -or [IO.Path]::IsPathRooted($manifest.runtimeExecutable)) { throw 'Invalid runtime executable path.' }
        if (Test-Path -LiteralPath (Join-Path $candidate.FullName $manifest.runtimeExecutable) -PathType Leaf) { return $manifest.buildId }
    }
    return $null
}
function Invoke-SyncChild([string]$Shell,[string]$ScriptPath,[string[]]$Arguments=@()) {
    if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) { throw "Missing child script: $ScriptPath" }
    $prior=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'; $PSNativeCommandUseErrorActionPreference=$false
        $global:LASTEXITCODE=$null
        & $Shell -NoLogo -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments | Out-Host
        $exitCode=$LASTEXITCODE
    } finally { $ErrorActionPreference=$prior }
    if ($null -eq $exitCode -or $exitCode -ne 0) { throw "$(Split-Path -Leaf $ScriptPath) failed (exit $exitCode). The previous source and build folders were preserved." }
}
function Install-SyncLaunchers([string]$Root,[string]$Source) {
    $content=@'
@echo off
setlocal
title Path of Dawn - Update and Play
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Bootstrap.ps1" -InstallRoot "%~dp0." %*
set "DawnExit=%ERRORLEVEL%"
if not "%DawnExit%"=="0" pause
exit /b %DawnExit%
'@
    $browser=@'
@echo off
call "%~dp0Update-PathOfDawn.cmd" -Streaming %*
exit /b %ERRORLEVEL%
'@
    $stop=@'
@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0StopManagedSession.ps1" -InstallRoot "%~dp0."
set "DawnExit=%ERRORLEVEL%"
if not "%DawnExit%"=="0" pause
exit /b %DawnExit%
'@
    $desired=@{
        'Bootstrap.ps1'=[IO.File]::ReadAllBytes((Join-Path $Source 'Tools/PathOfDawnUnreal/Bootstrap.ps1'))
        'StopManagedSession.ps1'=[IO.File]::ReadAllBytes((Join-Path $Source 'Tools/PathOfDawnUnreal/StopManagedSession.ps1'))
        'Update-PathOfDawn.cmd'=[Text.Encoding]::ASCII.GetBytes($content.Replace("`n","`r`n"))
        'Play-in-Browser.cmd'=[Text.Encoding]::ASCII.GetBytes($browser.Replace("`n","`r`n"))
        'Stop-PathOfDawn.cmd'=[Text.Encoding]::ASCII.GetBytes($stop.Replace("`n","`r`n"))
    }
    $receiptPath=Join-Path $Root '.dawn-launchers.json'
    $records=@()
    if (Test-Path -LiteralPath $receiptPath) { $records=@((Get-Content -Raw -LiteralPath $receiptPath | ConvertFrom-Json).files) }
    foreach ($name in $desired.Keys) {
        $target=Join-Path $Root $name
        $temporary="$target.$([guid]::NewGuid().ToString('N')).tmp"
        try {
            [IO.File]::WriteAllBytes($temporary,$desired[$name])
            $desiredHash=(Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash
            if (Test-Path -LiteralPath $target) {
                $currentHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
                $prior=@($records | Where-Object { $_.name -eq $name })
                if ($currentHash -ne $desiredHash -and ($prior.Count -ne 1 -or $prior[0].sha256 -ne $currentHash)) {
                    throw "Local launcher changes were preserved: $target. Move your edited launcher aside before updating."
                }
                if ($currentHash -ne $desiredHash) { [IO.File]::Replace($temporary,$target,"$target.$([guid]::NewGuid().ToString('N')).previous") }
            } else { [IO.File]::Move($temporary,$target) }
            $records=@($records | Where-Object { $_.name -ne $name })+@([ordered]@{name=$name;sha256=$desiredHash})
            Write-SyncJson $receiptPath @{schema=1;files=$records}
        } finally { if (Test-Path -LiteralPath $temporary) { [IO.File]::Delete($temporary) } }
    }
}

function Invoke-SyncLaunch([string]$InstallRoot,[string]$CommitSha,[string]$BuildId,[string]$EngineRoot,[bool]$Streaming,[string]$Shell,[string]$Pwsh) {
    $versions=Join-Path $InstallRoot 'versions'
    $sourceRoot=Join-Path $versions ('source-'+$CommitSha.Substring(0,12))
    $start=Join-Path $sourceRoot 'Tools/PathOfDawnUnreal/StartHere.ps1'
    $launchArgs=@('-BuildId',$BuildId)
    if ($EngineRoot) { $launchArgs += @('-EngineRoot',$EngineRoot) }
    if ($Streaming) { $launchArgs += @('-Streaming','-TestCandidate') }
    $lastFile=Join-Path $InstallRoot 'last-launch.json'; $previous=$null
    if (Test-Path -LiteralPath $lastFile) {
        $previous=Get-Content -Raw -LiteralPath $lastFile | ConvertFrom-Json
        if ($previous.commit -cnotmatch '^[a-f0-9]{40}$' -or $previous.buildId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$') { throw 'Invalid previous launch record.' }
        # Derive paths, never execute an arbitrary path stored in the receipt.
        $previousRoot=Join-Path $versions ('source-'+$previous.commit.Substring(0,12))
        Assert-SyncSource $previousRoot $previous.commit
    }
    $stoppedPrevious=$false; $rollbackAllowed=$true
    try {
        if ($previous) {
            Invoke-SyncChild $pwsh (Join-Path $previousRoot 'Tools/PathOfDawnUnreal/StopStreaming.ps1') @('-IncludeLocalGame')
            $stoppedPrevious=$true
        }
        if (-not $previous -or $previous.commit -ne $CommitSha) { Invoke-SyncChild $pwsh (Join-Path $sourceRoot 'Tools/PathOfDawnUnreal/StopStreaming.ps1') @('-IncludeLocalGame') }
        # A legacy ZIP launch has no managed receipt. Ask the user to close it;
        # never kill unowned processes or let two games share the save slot.
        $otherGames=@(Get-Process -Name 'PathOfDawnUnreal*' -ErrorAction SilentlyContinue)
        if ($otherGames.Count) { $rollbackAllowed=$false; throw 'An older game window is still running. Close that game, then run Update-PathOfDawn.cmd again. No unowned process was stopped.' }
        Invoke-SyncChild $shell $start $launchArgs
        if ($previous) { Write-SyncJson (Join-Path $InstallRoot 'previous-launch.json') $previous }
        Write-SyncJson $lastFile @{commit=$CommitSha;buildId=$buildId;streaming=[bool]$Streaming;engineRoot=$EngineRoot;launchRequestedUtc=[DateTime]::UtcNow.ToString('O');graphicalVerification='Not performed by updater'}
    } catch {
        $launchFailure=$_.Exception.Message
        if ($stoppedPrevious -and $previous -and $rollbackAllowed) {
            Write-Host 'The new launch failed. Attempting to restart the previous version.'
            try {
                Invoke-SyncChild $pwsh (Join-Path $sourceRoot 'Tools/PathOfDawnUnreal/StopStreaming.ps1') @('-IncludeLocalGame')
                $rollbackArgs=@('-BuildId',$previous.buildId)
                if ($previous.engineRoot) { $rollbackArgs += @('-EngineRoot',$previous.engineRoot) }
                if ($previous.streaming) { $rollbackArgs += @('-Streaming','-TestCandidate') }
                Invoke-SyncChild $shell (Join-Path $previousRoot 'Tools/PathOfDawnUnreal/StartHere.ps1') $rollbackArgs
            } catch { Write-Warning "Previous version could not be restarted automatically: $($_.Exception.Message). It remains in $previousRoot" }
        }
        throw $launchFailure
    }
}

$syncExit=1; $lockStream=$null; $work=$null
try {
    if (-not $DownloadOnly -and [Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Playing/building requires Windows. DownloadOnly can be used to inspect source on another OS.' }
    $InstallRoot=Assert-SyncRoot $InstallRoot
    [void][IO.Directory]::CreateDirectory($InstallRoot)
    try { $lockStream=[IO.File]::Open((Join-Path $InstallRoot '.update.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch { throw 'Another update is already running. Wait for its window to finish.' }
    [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    if (-not $CommitSha) {
        $commit=Invoke-RestMethod -Uri 'https://api.github.com/repos/ka8877/unreal_yesu/commits/main' -Headers @{'User-Agent'='PathOfDawn-Updater';'Accept'='application/vnd.github+json'} -TimeoutSec 60
        $CommitSha=$commit.sha
    }
    if ($CommitSha -cnotmatch '^[a-f0-9]{40}$') { throw 'GitHub did not return a full commit SHA.' }
    $versions=Join-Path $InstallRoot 'versions'; [void][IO.Directory]::CreateDirectory($versions)
    $sourceRoot=Join-Path $versions ('source-'+$CommitSha.Substring(0,12))
    if (-not (Test-Path -LiteralPath $sourceRoot)) {
        $work=Join-Path $InstallRoot ('staging-'+[guid]::NewGuid().ToString('N'))
        [void][IO.Directory]::CreateDirectory($work)
        $zipFile=Join-Path $work 'source.zip'; $unpacked=Join-Path $work 'source'
        Write-Host "Downloading source $($CommitSha.Substring(0,12)) from GitHub. Existing source/builds stay in place."
        $progressPreferenceBefore=$ProgressPreference
        try {
            $ProgressPreference='SilentlyContinue'
            Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/ka8877/unreal_yesu/zip/$CommitSha" -OutFile $zipFile -TimeoutSec 600
        } finally { $ProgressPreference=$progressPreferenceBefore }
        Expand-SyncArchive $zipFile $unpacked $CommitSha
        [IO.Directory]::Move($unpacked,$sourceRoot)
    } else { Write-Host "Source $($CommitSha.Substring(0,12)) is already downloaded; checking local files." }
    Assert-SyncSource $sourceRoot $CommitSha
    Install-SyncLaunchers $InstallRoot $sourceRoot
    Write-SyncJson (Join-Path $InstallRoot 'downloaded.json') @{commit=$CommitSha;sourceRoot=$sourceRoot;downloadedUtc=[DateTime]::UtcNow.ToString('O')}
    Write-Host "Source ready: $sourceRoot"
    Write-Host "Next time, double-click: $(Join-Path $InstallRoot 'Update-PathOfDawn.cmd')"
    if ($DownloadOnly) { $syncExit=0 }
    else {
        if ($Streaming) {
            $browserTools=Join-Path $sourceRoot 'Tools/PathOfDawnUnreal/PrepareBrowserTools.ps1'
            if (-not (Test-Path -LiteralPath $browserTools -PathType Leaf)) { throw 'Browser tooling setup script is missing from this source version.' }
            & $browserTools -ToolsRoot (Join-Path $InstallRoot 'tools') | Out-Host
        }
        $shell=(Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
        $start=Join-Path $sourceRoot 'Tools/PathOfDawnUnreal/StartHere.ps1'
        $commonArgs=@(); if ($EngineRoot) { $commonArgs=@('-EngineRoot',$EngineRoot) }
        $buildId=Get-SyncBuild $sourceRoot
        if (-not $buildId) {
            Write-Host 'Compiling, importing assets and packaging the new version. The old running version is kept during the build.'
            Invoke-SyncChild $shell $start (@('-BuildOnly')+$commonArgs)
            $buildId=Get-SyncBuild $sourceRoot
            if (-not $buildId) { throw 'Build returned without a usable package manifest. The previous session is unchanged.' }
        } else { Write-Host "Reusing packaged build $buildId; no new compile/cook is needed for this source commit." }
        $launchArgs=@('-BuildId',$buildId)+$commonArgs
        if ($Streaming) { $launchArgs += @('-Streaming','-TestCandidate') }
        # Check prerequisites before interrupting the previous process. This does
        # not claim actual video/input validation or promote a production release.
        Invoke-SyncChild $shell $start ($launchArgs+@('-CheckOnly'))
        $pwshCommand=Get-Command pwsh.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        $pwsh=if ($pwshCommand) { $pwshCommand.Source } else { Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'PowerShell/7/pwsh.exe' }
        if (-not (Test-Path -LiteralPath $pwsh -PathType Leaf)) { throw 'PowerShell 7 was not found.' }
        Invoke-SyncLaunch $InstallRoot $CommitSha $buildId $EngineRoot ([bool]$Streaming) $shell $pwsh
        if ($Streaming) { Write-Host 'Browser test address: http://127.0.0.1:8080/ (this PC only). The GPU host and its game/signalling processes must stay running.' }
        Write-Host 'Launch requested. Check the actual game window/video; the updater does not certify graphics or gameplay.'
        $syncExit=0
    }
} catch {
    Write-Host "Update stopped: $($_.Exception.Message)"
    Write-Host 'Existing source versions, user saves and previous packages were not deleted.'
} finally {
    if ($work -and (Test-Path -LiteralPath $work)) { Remove-Item -LiteralPath $work -Recurse -Force }
    if ($lockStream) { $lockStream.Dispose() }
}
exit $syncExit
