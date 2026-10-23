#requires -Version 5.1
# Only called for the explicitly selected browser-test workflow. No system install,
# administrator rights, persistent PATH change or firewall change is performed.
[CmdletBinding()]
param([string]$ToolsRoot='C:\PathOfDawn\tools')

$ErrorActionPreference='Stop'

function Get-DawnBrowserToolPins {
    return @(
        [pscustomobject]@{
            name='Node'; folder='node-v22.14.0-win-x64'; archive='node-v22.14.0-win-x64.zip'
            url='https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip'
            sha256='55b639295920b219bb2acbcfa00f90393a2789095b7323f79475c9f34795f217'
            checksumSource='https://nodejs.org/dist/v22.14.0/SHASUMS256.txt'
            topDirectory='node-v22.14.0-win-x64'; required=@('node.exe','npm.cmd','node_modules/npm/bin/npm-cli.js')
        },
        [pscustomobject]@{
            name='MinGit'; folder='mingit-2.56.0.3-x64'; archive='MinGit-2.56.0.3-64-bit.zip'
            url='https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.3/MinGit-2.56.0.3-64-bit.zip'
            sha256='2e5619966e588fde5f8122c5557cad50c0fbafcaed736689f40ec1dfb1d78ea7'
            checksumSource='https://api.github.com/repos/git-for-windows/git/releases/tags/v2.56.0.windows.3'
            topDirectory=''; required=@('cmd/git.exe')
        }
    )
}

function Get-DawnBrowserToolsRoot([string]$Path) {
    if (-not $Path -or $Path -notmatch '^[A-Za-z]:[\\/]' -or $Path -match '[^\x20-\x7E]' -or $Path -match '[<>|"?*]') {
        throw 'Browser tools need an absolute ASCII Windows folder, for example C:\PathOfDawn\tools.'
    }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd('\','/')
    if ($full -match '^[A-Za-z]:$') { throw 'Use a project tools folder, not the root of a drive.' }
    return $full
}

function Test-DawnNodePair([string]$Node) {
    if (-not $Node -or -not (Test-Path -LiteralPath $Node -PathType Leaf)) { return $false }
    $npm=Join-Path (Split-Path -Parent $Node) 'npm.cmd'
    if (-not (Test-Path -LiteralPath $npm -PathType Leaf)) { return $false }
    try {
        $nodeVersion=(& $Node --version 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -ne 0 -or $nodeVersion -ne 'v22.14.0') { return $false }
        $architecture=(& $Node -p 'process.arch' 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -ne 0 -or $architecture -ne 'x64') { return $false }
        $npmVersion=(& $npm --version 2>$null | Select-Object -Last 1)
        return ($LASTEXITCODE -eq 0 -and $npmVersion -eq '10.9.2')
    } catch { return $false }
}

function Test-DawnGitExecutable([string]$Git) {
    if (-not $Git -or -not (Test-Path -LiteralPath $Git -PathType Leaf)) { return $false }
    try {
        $version=(& $Git --version 2>$null | Select-Object -Last 1)
        return ($LASTEXITCODE -eq 0 -and $version -match '^git version \d+\.\d+\.')
    } catch { return $false }
}

function Get-DawnZipDestination([string]$Root,[string]$EntryName) {
    $name=$EntryName.Replace('\','/')
    if (-not $name -or $name.StartsWith('/') -or $name.Contains(':') -or $name.Contains([char]0) -or $name.Split('/') -contains '..') {
        throw "Unsafe ZIP entry: $EntryName"
    }
    $prefix=[IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar
    $destination=[IO.Path]::GetFullPath((Join-Path $Root $name))
    if (-not $destination.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw "ZIP entry escapes its destination: $EntryName" }
    return $destination
}

function Expand-DawnBrowserArchive([string]$Archive,[string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        if ($zip.Entries.Count -lt 1 -or $zip.Entries.Count -gt 40000) { throw 'Unexpected browser-tool archive entry count.' }
        $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        [long]$total=0
        # Validate every entry before writing any of them.
        foreach ($entry in $zip.Entries) {
            $target=Get-DawnZipDestination $Destination $entry.FullName
            if (-not $seen.Add($target.TrimEnd('\','/'))) { throw "Duplicate ZIP entry: $($entry.FullName)" }
            if ((($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'Symbolic links are not accepted in tool archives.' }
            $total+=$entry.Length
            if ($entry.Length -gt 268435456 -or $total -gt 2147483648) { throw 'Browser-tool archive exceeds its extraction size limit.' }
        }
        foreach ($entry in $zip.Entries) {
            $target=Get-DawnZipDestination $Destination $entry.FullName
            if ($entry.FullName.EndsWith('/') -or $entry.FullName.EndsWith('\')) {
                New-Item -ItemType Directory -Path $target -Force | Out-Null
            } else {
                New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)
            }
        }
    } finally { $zip.Dispose() }
}

function Get-DawnPortableFileRows([string]$Directory) {
    $prefix=[IO.Path]::GetFullPath($Directory).TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
    return @(Get-ChildItem -LiteralPath $Directory -File -Recurse | Where-Object {$_.Name -ne '.pathofdawn-tool.json'} | Sort-Object FullName | ForEach-Object {
        [pscustomobject]@{path=$_.FullName.Substring($prefix.Length).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    })
}

function Assert-DawnPortableTool([string]$Directory,$Pin) {
    $marker=Join-Path $Directory '.pathofdawn-tool.json'
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) { throw "Existing tool folder has no project ownership record; it was preserved: $Directory" }
    $record=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($record.schema -ne 1 -or $record.archiveSha256 -ne $Pin.sha256 -or @($record.files).Count -lt 1) { throw "Tool ownership record does not match the pinned archive: $Directory" }
    $actual=@(Get-DawnPortableFileRows $Directory)
    if ($actual.Count -ne @($record.files).Count) { throw "Tool files changed; the folder was preserved: $Directory. Move it aside and retry to obtain a clean copy." }
    $expected=@{}
    foreach ($file in $record.files) { $expected[$file.path]=$file.sha256 }
    foreach ($file in $actual) {
        if (-not $expected.ContainsKey($file.path) -or $expected[$file.path] -ne $file.sha256) { throw "Tool file changed; it was preserved: $(Join-Path $Directory $file.path). Move the tool folder aside and retry." }
    }
    foreach ($relative in $Pin.required) { if (-not (Test-Path -LiteralPath (Join-Path $Directory $relative) -PathType Leaf)) { throw "Missing tool file: $relative" } }
}

function Install-DawnPortableTool([string]$Root,$Pin) {
    $target=Join-Path $Root $Pin.folder
    if (Test-Path -LiteralPath $target) {
        Assert-DawnPortableTool $target $Pin
        return $target
    }
    $cache=Join-Path $Root 'downloads'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $archive=Join-Path $cache $Pin.archive
    if (Test-Path -LiteralPath $archive) {
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $Pin.sha256) {
            # Preserve a corrupt/edited cache file rather than silently overwriting it.
            [IO.File]::Move($archive,($archive+'.unverified-'+[guid]::NewGuid().ToString('N')))
        }
    }
    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Host "Preparing portable $($Pin.name) from its official release (no system installation)..."
        $partial=$archive+'.'+[guid]::NewGuid().ToString('N')+'.partial'
        $oldProgress=$ProgressPreference
        try {
            $ProgressPreference='SilentlyContinue'
            [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -UseBasicParsing -Uri $Pin.url -OutFile $partial -TimeoutSec 600 -UserAgent 'PathOfDawnBrowserTools/1.0'
            if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $Pin.sha256) { throw "$($Pin.name) archive checksum mismatch. No downloaded program was executed." }
            [IO.File]::Move($partial,$archive)
        } finally {
            $ProgressPreference=$oldProgress
            if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
        }
    }
    # Cached archives also require a checksum check before extraction.
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $Pin.sha256) { throw 'Tool cache checksum mismatch.' }
    $staging=Join-Path $Root ('.staging-'+[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    try {
        Expand-DawnBrowserArchive $archive $staging
        $payload=if ($Pin.topDirectory) { Join-Path $staging $Pin.topDirectory } else { $staging }
        foreach ($relative in $Pin.required) { if (-not (Test-Path -LiteralPath (Join-Path $payload $relative) -PathType Leaf)) { throw "Official archive is missing $relative" } }
        $record=[ordered]@{schema=1;name=$Pin.name;sourceUrl=$Pin.url;checksumSource=$Pin.checksumSource;archiveSha256=$Pin.sha256;preparedUtc=[DateTime]::UtcNow.ToString('O');files=@(Get-DawnPortableFileRows $payload)}
        [IO.File]::WriteAllText((Join-Path $payload '.pathofdawn-tool.json'),($record | ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
        [IO.Directory]::Move($payload,$target)
    } finally {
        if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
    }
    Assert-DawnPortableTool $target $Pin
    return $target
}

function Invoke-DawnBrowserToolsPreparation([string]$ToolsRoot) {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitOperatingSystem) { throw 'Portable browser tools are for 64-bit Windows only.' }
    $root=Get-DawnBrowserToolsRoot $ToolsRoot
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    $mutex=New-Object Threading.Mutex($false,'Local\PathOfDawnUnrealBrowserTools')
    if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); throw 'Another browser-tool preparation is running.' }
    try {
        $pins=@(Get-DawnBrowserToolPins)
        $node=$null
        $git=$null
        $programFiles=[Environment]::GetFolderPath('ProgramFiles')
        $nodeCandidates=@(Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
        $nodeCandidates+=Join-Path $programFiles 'nodejs/node.exe'
        foreach ($candidate in ($nodeCandidates | Select-Object -Unique)) { if (Test-DawnNodePair $candidate) { $node=$candidate; break } }
        if (-not $node) { $node=Join-Path (Install-DawnPortableTool $root $pins[0]) 'node.exe' }
        $nodeFolder=Split-Path -Parent $node
        # Keep npm's subprocess Node resolution aligned with the selected version.
        $env:PATH=$nodeFolder+[IO.Path]::PathSeparator+$env:PATH
        if (-not (Test-DawnNodePair $node)) { throw 'The prepared Node/npm pair did not report v22.14.0 / 10.9.2.' }
        $gitCandidates=@(Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
        $gitCandidates+=Join-Path $programFiles 'Git/cmd/git.exe'
        foreach ($candidate in ($gitCandidates | Select-Object -Unique)) { if (Test-DawnGitExecutable $candidate) { $git=$candidate; break } }
        if (-not $git) { $git=Join-Path (Install-DawnPortableTool $root $pins[1]) 'cmd/git.exe' }
        if (-not (Test-DawnGitExecutable $git)) { throw 'The prepared Git executable did not start successfully.' }
        $env:PATH=(Split-Path -Parent $git)+[IO.Path]::PathSeparator+$env:PATH
        Write-Host 'Browser tools ready. Only this process PATH was changed; no administrator or firewall changes were made.'
        return [pscustomobject]@{node=$node;npm=(Join-Path $nodeFolder 'npm.cmd');git=$git;toolsRoot=$root}
    } finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
}

# Dot-source is used by portable archive tests; executing this file performs setup.
if ($MyInvocation.InvocationName -ne '.') { Invoke-DawnBrowserToolsPreparation -ToolsRoot $ToolsRoot }
