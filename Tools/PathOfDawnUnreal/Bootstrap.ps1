#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$InstallRoot = 'C:\PathOfDawn',
    [string]$CommitSha,
    [string]$EngineRoot,
    [switch]$Streaming,
    [switch]$DownloadOnly
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$repo = 'ka8877/unreal_yesu'
$headers = @{ 'User-Agent' = 'PathOfDawn-Updater'; 'Accept' = 'application/vnd.github+json' }
$temporary = $null
try {
    $InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
    if ($InstallRoot -match '[^\x20-\x7E]' -or $InstallRoot -match '[\r\n%&!^]') {
        throw 'Use a local ASCII path such as C:\PathOfDawn (not the OneDrive Desktop).'
    }
    if (-not $CommitSha) {
        Write-Host 'Checking the latest published Path of Dawn source...'
        $head = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/commits/main" -Headers $headers -TimeoutSec 60
        $CommitSha = $head.sha
    }
    if ($CommitSha -notmatch '^[0-9a-fA-F]{40}$') { throw 'GitHub did not return a valid commit ID.' }
    $CommitSha = $CommitSha.ToLowerInvariant()
    $cache = Join-Path $InstallRoot 'cache'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $temporary = Join-Path $cache ('sync-' + [guid]::NewGuid().ToString('N') + '.ps1')
    $relative = 'Tools/PathOfDawnUnreal/SyncAndPlay.ps1'
    # Fetch the script from the SAME immutable commit as the source archive.
    $downloadUri = "https://raw.githubusercontent.com/$repo/$CommitSha/$relative"
    Invoke-WebRequest -UseBasicParsing -Uri $downloadUri -Headers $headers -OutFile $temporary -TimeoutSec 60
    # Git's blob digest verifies the raw download against GitHub's commit tree.
    $blob = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/contents/${relative}?ref=$CommitSha" -Headers $headers -TimeoutSec 60
    $bytes = [IO.File]::ReadAllBytes($temporary)
    if ($bytes.Length -lt 100 -or $bytes.Length -gt 524288 -or $blob.type -ne 'file') { throw 'Unexpected updater response.' }
    $prefix = [Text.Encoding]::UTF8.GetBytes("blob $($bytes.Length)`0")
    $hashInput = New-Object byte[] ($prefix.Length + $bytes.Length)
    [Array]::Copy($prefix, 0, $hashInput, 0, $prefix.Length)
    [Array]::Copy($bytes, 0, $hashInput, $prefix.Length, $bytes.Length)
    $sha1 = [Security.Cryptography.SHA1]::Create()
    try { $actual = ([BitConverter]::ToString($sha1.ComputeHash($hashInput))).Replace('-', '').ToLowerInvariant() }
    finally { $sha1.Dispose() }
    if ($actual -ne $blob.sha) { throw 'Updater download does not match the published commit. Nothing was executed.' }
    $parseTokens = $null; $parseErrors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($temporary, [ref]$parseTokens, [ref]$parseErrors)
    if ($parseErrors.Count -gt 0) { throw 'Downloaded updater is not a valid PowerShell script.' }
    $arguments = @{ InstallRoot=$InstallRoot; CommitSha=$CommitSha }
    if ($EngineRoot) { $arguments.EngineRoot=$EngineRoot }
    if ($Streaming) { $arguments.Streaming=$true }
    if ($DownloadOnly) { $arguments.DownloadOnly=$true }
    & $temporary @arguments
    if (-not $?) { throw 'The source updater failed. The previous source folder is preserved.' }
} catch {
    Write-Host ('Update stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($temporary -and (Test-Path -LiteralPath $temporary)) { Remove-Item -LiteralPath $temporary -Force }
}
