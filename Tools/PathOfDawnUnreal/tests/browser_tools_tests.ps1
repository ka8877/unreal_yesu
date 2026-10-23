#requires -Version 7.2
[CmdletBinding()]
param([string]$OfficialArchiveDirectory)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/../PrepareBrowserTools.ps1"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$testRoot=Join-Path ([IO.Path]::GetTempPath()) ('dawn-browser-tools-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$script:checks=0
function Assert-BrowserTools($Condition,[string]$Message) { if (-not $Condition) { throw $Message }; $script:checks++ }
function New-TestArchive([string]$Path,[string[]]$Names,[switch]$Symlink) {
    $zip=[IO.Compression.ZipFile]::Open($Path,[IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($name in $Names) {
            $entry=$zip.CreateEntry($name)
            if ($Symlink) { $entry.ExternalAttributes=-1577058304 }
            $stream=$entry.Open()
            try { $bytes=[Text.Encoding]::UTF8.GetBytes('test tool payload'); $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
        }
    } finally { $zip.Dispose() }
}
try {
    $pins=@(Get-DawnBrowserToolPins)
    Assert-BrowserTools ($pins.Count -eq 2 -and $pins[0].sha256.Length -eq 64 -and $pins[1].sha256.Length -eq 64) 'Tool pins missing.'
    Assert-BrowserTools ($pins[0].url.StartsWith('https://nodejs.org/dist/') -and $pins[1].url.StartsWith('https://github.com/git-for-windows/git/releases/download/')) 'Unexpected download source.'
    $cases=@(
        @{name='parent';entries=@('../escape.exe')},
        @{name='backslash-parent';entries=@('safe\..\..\escape.exe')},
        @{name='absolute';entries=@('/escape.exe')},
        @{name='drive';entries=@('C:/escape.exe')},
        @{name='ads';entries=@('file.txt:payload')},
        @{name='duplicate';entries=@('cmd/git.exe','CMD/GIT.EXE')},
        @{name='symlink';entries=@('link.exe');symlink=$true}
    )
    foreach ($case in $cases) {
        $archive=Join-Path $testRoot ($case.name+'.zip')
        New-TestArchive $archive $case.entries -Symlink:([bool]$case.symlink)
        $destination=Join-Path $testRoot ($case.name+'-out')
        $rejected=$false
        try { Expand-DawnBrowserArchive $archive $destination } catch { $rejected=$true }
        Assert-BrowserTools $rejected ("Unsafe archive accepted: "+$case.name)
        Assert-BrowserTools (-not (Test-Path -LiteralPath $destination)) ("Unsafe archive wrote files before validation: "+$case.name)
    }
    $script:testArchiveSource=Join-Path $testRoot 'good.zip'
    New-TestArchive $script:testArchiveSource @('cmd/git.exe','LICENSE.txt')
    $pin=[pscustomobject]@{name='test';folder='test-tool';archive='test.zip';url='https://example.invalid/test.zip';sha256=(Get-FileHash $script:testArchiveSource).Hash.ToLowerInvariant();checksumSource='test fixture';topDirectory='';required=@('cmd/git.exe')}
    $script:downloadCalls=0
    function Invoke-WebRequest {
        param([switch]$UseBasicParsing,[string]$Uri,[string]$OutFile,[int]$TimeoutSec,[string]$UserAgent)
        $script:downloadCalls++
        Copy-Item -LiteralPath $script:testArchiveSource -Destination $OutFile
    }
    $toolRoot=Join-Path $testRoot 'tools with spaces'
    $prepared=Install-DawnPortableTool $toolRoot $pin
    Assert-BrowserTools (Test-Path -LiteralPath (Join-Path $prepared 'cmd/git.exe')) 'Verified archive was not extracted.'
    Assert-BrowserTools ($script:downloadCalls -eq 1) 'Expected one fixture download.'
    $again=Install-DawnPortableTool $toolRoot $pin
    Assert-BrowserTools ($again -eq $prepared -and $script:downloadCalls -eq 1) 'Unchanged tool was downloaded again.'
    [IO.File]::AppendAllText((Join-Path $prepared 'cmd/git.exe'),'user edit')
    $rejected=$false
    try { Install-DawnPortableTool $toolRoot $pin | Out-Null } catch { $rejected=$true }
    Assert-BrowserTools $rejected 'Edited portable executable was silently accepted.'
    Assert-BrowserTools ((Get-Content -LiteralPath (Join-Path $prepared 'cmd/git.exe') -Raw).Contains('user edit')) 'Edited tool was overwritten.'
    $unknownRoot=Join-Path $testRoot 'unknown'
    New-Item -ItemType Directory -Path (Join-Path $unknownRoot 'test-tool') -Force | Out-Null
    $rejected=$false
    try { Install-DawnPortableTool $unknownRoot $pin | Out-Null } catch { $rejected=$true }
    Assert-BrowserTools $rejected 'Unowned directory was overwritten.'
    $badPin=$pin.PSObject.Copy(); $badPin.sha256='0'*64
    $badRoot=Join-Path $testRoot 'bad-digest'
    $rejected=$false
    try { Install-DawnPortableTool $badRoot $badPin | Out-Null } catch { $rejected=$true }
    Assert-BrowserTools ($rejected -and -not (Test-Path -LiteralPath (Join-Path $badRoot 'test-tool'))) 'Mismatching archive digest was extracted.'
    Assert-BrowserTools (@(Get-ChildItem -LiteralPath $badRoot -Recurse -Filter '*.partial').Count -eq 0) 'Failed download left temporary files.'
    if ($OfficialArchiveDirectory) {
        foreach ($official in $pins) {
            $officialZip=Join-Path $OfficialArchiveDirectory $official.archive
            Assert-BrowserTools ((Get-FileHash -LiteralPath $officialZip -Algorithm SHA256).Hash -eq $official.sha256) ('Official checksum mismatch: '+$official.name)
            $extraction=Join-Path $testRoot ('official-'+$official.name)
            Expand-DawnBrowserArchive $officialZip $extraction
            $payload=if ($official.topDirectory) {Join-Path $extraction $official.topDirectory} else {$extraction}
            foreach ($relative in $official.required) { Assert-BrowserTools (Test-Path -LiteralPath (Join-Path $payload $relative)) ('Official archive missing '+$relative) }
            if ($official.name -eq 'Node') {
                $npm=Get-Content -LiteralPath (Join-Path $payload 'node_modules/npm/package.json') -Raw | ConvertFrom-Json
                Assert-BrowserTools ($npm.version -eq '10.9.2') 'Pinned official Node archive npm version mismatch.'
            }
        }
    }
    Write-Host "Browser-tool archive checks passed: $script:checks. Windows executable launch was not tested."
} finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
