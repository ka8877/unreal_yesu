#requires -Version 7.2
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$script:ProjectRoot = Join-Path $script:RepoRoot 'Games/PathOfDawnUnreal'
$script:ProjectFile = Join-Path $script:ProjectRoot 'PathOfDawnUnreal.uproject'
$script:BuildRoot = Join-Path $script:RepoRoot 'Builds/PathOfDawnUnreal'
$script:StreamRoot = Join-Path $script:RepoRoot 'Streaming/PathOfDawnUnreal'
$script:EvidenceRoot = Join-Path $script:RepoRoot 'Docs/PathOfDawnUnreal/Evidence'

function Assert-WindowsHost {
    if (-not $IsWindows) { throw 'Windows 64-bit with installed stable UE 5.8, MSVC and Windows SDK is required. This script does not cross-compile Win64 from Linux.' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit Windows host is required.' }
}
function Resolve-DawnEngine([string]$EngineRoot) {
    if (-not $EngineRoot) { $EngineRoot = $env:UE_ROOT }
    $settingsFile = Join-Path $PSScriptRoot 'local.settings.json'
    if (-not $EngineRoot -and (Test-Path -LiteralPath $settingsFile)) {
        $settings = Get-Content -Raw -LiteralPath $settingsFile | ConvertFrom-Json
        $EngineRoot = $settings.EngineRoot
    }
    if (-not $EngineRoot) { throw 'Supply -EngineRoot "C:\Program Files\Epic Games\UE_5.8" or UE_ROOT. Engine installation/login/EULA must be completed on the Windows host.' }
    $EngineRoot = (Resolve-Path -LiteralPath $EngineRoot).Path
    $versionFile = Join-Path $EngineRoot 'Engine/Build/Build.version'
    if (-not (Test-Path -LiteralPath $versionFile)) { throw "Not an Unreal root: $EngineRoot" }
    $version = Get-Content -Raw -LiteralPath $versionFile | ConvertFrom-Json
    if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8) { throw "This source targets stable UE 5.8. Observed $($version.MajorVersion).$($version.MinorVersion). Review compatibility before changing the target." }
    if ($version.BranchName -match 'Preview|ue5-main') { throw 'Preview/main engines are not accepted for the demo.' }
    return $EngineRoot
}
function Assert-DawnFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file missing: $Path" }
}
function New-DawnBuildId {
    return (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
}
function Assert-DawnBuildId([string]$BuildId) {
    if ($BuildId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$') { throw 'BuildId must be 3–80 ASCII letters/digits/dot/dash/underscore; no paths.' }
}
function Write-DawnJson([string]$Path, $Value) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $Path, $true)
}
function Invoke-DawnCommand([string]$File, [string[]]$Arguments, [string]$Log) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $Log) -Force | Out-Null
    Write-Host "Running $(Split-Path -Leaf $File); log: $Log"
    & $File @Arguments 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { [string]$_.Exception.Message }
        else { $_.ToString() }
    } | Tee-Object -FilePath $Log | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "$(Split-Path -Leaf $File) failed with exit code $LASTEXITCODE. See $Log" }
}
function Get-DawnCandidate([string]$BuildId) {
    Assert-DawnBuildId $BuildId
    $candidate = Join-Path $script:BuildRoot "Windows/$BuildId"
    Assert-DawnFile (Join-Path $candidate 'build-manifest.json')
    return $candidate
}
function Get-DawnManifest([string]$Candidate) {
    return Get-Content -Raw -LiteralPath (Join-Path $Candidate 'build-manifest.json') | ConvertFrom-Json
}
function Get-DawnPayloadHash([string]$Candidate) {
    $rows = Get-ChildItem -LiteralPath $Candidate -Recurse -File | Where-Object {
        $_.Name -notin @('build-manifest.json', 'smoke-report.json') -and $_.Extension -notin @('.pdb','.exp','.lib','.pem','.key') -and $_.FullName -notmatch '[\\/]Saved[\\/]'
    } | Sort-Object FullName | ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($Candidate, $_.FullName).Replace('\','/')
        "$relative`t$((Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash)"
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [Convert]::ToHexString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($rows -join "`n")))) }
    finally { $sha.Dispose() }
}
function Assert-DawnSmoke([string]$Candidate, [string]$Report) {
    Assert-DawnFile $Report
    $manifest = Get-DawnManifest $Candidate
    $smoke = Get-Content -Raw -LiteralPath $Report | ConvertFrom-Json
    if ($smoke.buildId -ne $manifest.buildId -or $smoke.payloadSha256 -ne $manifest.payloadSha256) { throw 'Smoke evidence belongs to a different build. Do not switch or package.' }
    if ((Get-DawnPayloadHash $Candidate) -ne $manifest.payloadSha256) { throw 'Build payload changed after manifest creation.' }
    foreach ($key in @('graphicalLaunch','title','movement','dialogue','choice','ending','rewind','saveRestartContinue','koreanGlyphs')) {
        if ($smoke.checks.$key -ne $true) { throw "Graphical smoke check missing/failed: $key. NullRHI/HTTP 200 does not count." }
    }
    if (-not $smoke.tester -or -not $smoke.testedUtc -or $smoke.captures.Count -lt 6) { throw 'Smoke report must name tester/time and at least six actual gameplay captures.' }
    foreach ($capture in $smoke.captures) {
        $path = if ([IO.Path]::IsPathRooted($capture)) { $capture } else { Join-Path (Split-Path -Parent $Report) $capture }
        Assert-DawnFile $path
    }
    return $smoke
}
function Get-DawnHostRoot {
    Assert-WindowsHost
    $root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'PathOfDawnUnreal/Host'
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    return $root
}
function Get-DawnProcessIdentity([Diagnostics.Process]$Process) {
    if ($IsLinux) {
        # .NET converts /proc ticks to wall time with slight sub-ms drift on Linux.
        # The kernel start tick is stable and distinguishes PID reuse exactly.
        $stat = [IO.File]::ReadAllText("/proc/$($Process.Id)/stat")
        return 'linux-start-ticks:' + $stat.Substring($stat.LastIndexOf(')') + 2).Split(' ')[19]
    }
    return 'creation-ticks:' + $Process.StartTime.ToUniversalTime().Ticks.ToString()
}
function Test-DawnProcessRunning([string]$Role) {
    $stateFile = Join-Path $script:StreamRoot "runtime/$Role.process.json"
    if (-not (Test-Path -LiteralPath $stateFile)) { return $false }
    $record = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json
    $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    return $process -and -not $process.HasExited -and (Get-DawnProcessIdentity $process) -eq $record.startIdentity -and $process.Path -eq $record.executable
}
function ConvertTo-DawnNativeArguments([string[]]$Arguments) {
    # Start-Process joins ArgumentList with spaces. Serialize each argument using
    # Windows native argv quoting (no cmd.exe or shell expression is involved).
    return (@(foreach ($argument in $Arguments) {
        $escaped = [regex]::Replace($argument, '(\\*)"', '$1$1\"')
        $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
        '"' + $escaped + '"'
    }) -join ' ')
}
function Start-DawnProcess([string]$Role, [string]$File, [string[]]$Arguments, [string]$WorkingDirectory) {
    $runtime = Join-Path $script:StreamRoot 'runtime'
    New-Item -ItemType Directory -Path $runtime -Force | Out-Null
    $stateFile = Join-Path $runtime "$Role.process.json"
    $sessionMutex = $null
    if ($Role -in @('local-game','stream-game')) {
        $sessionMutex = [Threading.Mutex]::new($false,'Local\PathOfDawnUnrealGameSession')
        if (-not $sessionMutex.WaitOne(0)) { $sessionMutex.Dispose(); throw 'Another game start is in progress.' }
    }
    try {
        if ($sessionMutex) {
            foreach ($gameRole in @('local-game','stream-game')) {
                if (Test-DawnProcessRunning $gameRole) { throw "$gameRole already owns the host save session. Stop it before starting another game." }
            }
        } elseif (Test-DawnProcessRunning $Role) { throw "$Role is already running. Use StopStreaming.ps1." }
        $stdoutLog = $null; $stderrLog = $null
        if ($IsWindows) {
            # On Windows Start-Process supplies native file handles for these
            # redirects. The persistent game/server must not inherit Run-Step's
            # output pipes: that keeps its native pipeline waiting forever and
            # prevents the browser-open step, even after the launcher has exited.
            $logs = Join-Path $runtime 'logs'
            New-Item -ItemType Directory -Path $logs -Force | Out-Null
            $logId = $Role + '-' + [guid]::NewGuid().ToString('N')
            $stdoutLog = Join-Path $logs ($logId + '.stdout.log')
            $stderrLog = Join-Path $logs ($logId + '.stderr.log')
            $parameters = @{
                FilePath=$File; WorkingDirectory=$WorkingDirectory; PassThru=$true
                RedirectStandardOutput=$stdoutLog; RedirectStandardError=$stderrLog
                WindowStyle=$(if ($Role -eq 'local-game') {'Normal'} else {'Hidden'})
            }
            if ($Arguments.Count) { $parameters.ArgumentList=ConvertTo-DawnNativeArguments $Arguments }
            $process = Start-Process @parameters
        } else {
            # Portable unit tests only; the Windows/Unreal launcher never runs on
            # this path. Unix Start-Process uses different redirection semantics.
            $info = [Diagnostics.ProcessStartInfo]::new()
            $info.FileName = $File
            $info.WorkingDirectory = $WorkingDirectory
            $info.UseShellExecute = $false
            foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
            $process = [Diagnostics.Process]::Start($info)
        }
        if (-not $process) { throw "Could not start $Role" }
        try {
            Write-DawnJson $stateFile ([ordered]@{pid=$process.Id; startedUtc=$process.StartTime.ToUniversalTime().ToString('O'); startIdentity=(Get-DawnProcessIdentity $process); executable=$process.Path; role=$Role; stdoutLog=$stdoutLog; stderrLog=$stderrLog})
        } catch {
            if (-not $process.HasExited) { $process.Kill($true); [void]$process.WaitForExit(5000) }
            throw
        }
        return $process
    } finally { if ($sessionMutex) { $sessionMutex.ReleaseMutex(); $sessionMutex.Dispose() } }
}
function Stop-DawnProcess([string]$Role) {
    $stateFile = Join-Path $script:StreamRoot "runtime/$Role.process.json"
    if (-not (Test-Path -LiteralPath $stateFile)) { return }
    $record = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json
    $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if ($process -and -not $process.HasExited) {
        if ((Get-DawnProcessIdentity $process) -ne $record.startIdentity -or $process.Path -ne $record.executable) { throw "PID $($record.pid) was reused or path differs. Refusing to terminate unrelated process." }
        if ($process.CloseMainWindow()) { [void]$process.WaitForExit(5000) }
        if (-not $process.HasExited) { $process.Kill($true); [void]$process.WaitForExit(5000) }
    }
    Remove-Item -LiteralPath $stateFile
}
