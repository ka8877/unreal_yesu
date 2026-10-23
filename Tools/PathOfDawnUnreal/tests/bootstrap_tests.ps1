#requires -Version 7.2
# Real Bootstrap.ps1 with mocked HTTPS responses; no Unreal/Windows claim.
$ErrorActionPreference='Stop'
$bootstrap=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../Bootstrap.ps1'))
$scratch=Join-Path ([IO.Path]::GetTempPath()) ('dawn-bootstrap-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($scratch)
try {
    $fixture=Join-Path $scratch 'fixture.ps1'
    [IO.File]::WriteAllText($fixture,@'
param([string]$InstallRoot,[string]$CommitSha,[string]$EngineRoot,[switch]$Streaming,[switch]$DownloadOnly)
@{commit=$CommitSha;streaming=[bool]$Streaming;downloadOnly=[bool]$DownloadOnly;engine=$EngineRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallRoot 'executed.json')
'@)
    $harness=Join-Path $scratch 'harness.ps1'
    [IO.File]::WriteAllText($harness,@'
param($Bootstrap,$Fixture,$Root,$Scenario)
$ErrorActionPreference='Stop'
function Invoke-WebRequest {
    param($UseBasicParsing,$Uri,$Headers,$OutFile,$TimeoutSec)
    if ($Uri -notmatch '/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/Tools/PathOfDawnUnreal/SyncAndPlay.ps1$') { throw 'Unpinned download' }
    Copy-Item -LiteralPath $Fixture -Destination $OutFile
}
function Invoke-RestMethod {
    param($Uri,$Headers,$TimeoutSec)
    if ($Uri -like '*/commits/main') { return @{sha='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'} }
    if ($Uri -notmatch 'ref=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa$') { throw 'Unpinned metadata' }
    $bytes=[IO.File]::ReadAllBytes($Fixture)
    $prefix=[Text.Encoding]::UTF8.GetBytes("blob $($bytes.Length)`0")
    $sha1=[Security.Cryptography.SHA1]::Create()
    try { $hash=([BitConverter]::ToString($sha1.ComputeHash([byte[]]($prefix+$bytes)))).Replace('-','').ToLowerInvariant() } finally {$sha1.Dispose()}
    if ($Scenario -eq 'wrong-hash') { $hash='0000000000000000000000000000000000000000' }
    return @{type='file';sha=$hash}
}
& $Bootstrap -InstallRoot $Root -Streaming -DownloadOnly -EngineRoot 'C:\Engine with spaces'
if (-not $?) { exit 1 }
'@.Replace('param($UseBasicParsing,','param([switch]$UseBasicParsing,'))
    $shell=(Get-Process -Id $PID).Path
    $goodRoot=Join-Path $scratch 'good'
    & $shell -NoLogo -NoProfile -File $harness $bootstrap $fixture $goodRoot good
    if ($LASTEXITCODE -ne 0) { throw 'Valid bootstrap fixture failed.' }
    $record=Get-Content -Raw -LiteralPath (Join-Path $goodRoot 'executed.json') | ConvertFrom-Json
    if ($record.commit -ne ('a'*40) -or -not $record.streaming -or -not $record.downloadOnly -or $record.engine -ne 'C:\Engine with spaces') { throw 'Bootstrap arguments were not preserved.' }
    if (@(Get-ChildItem -LiteralPath (Join-Path $goodRoot 'cache') -Filter '*.ps1').Count -ne 0) { throw 'Temporary updater leaked.' }
    $badRoot=Join-Path $scratch 'bad'
    & $shell -NoLogo -NoProfile -File $harness $bootstrap $fixture $badRoot wrong-hash
    if ($LASTEXITCODE -eq 0 -or (Test-Path -LiteralPath (Join-Path $badRoot 'executed.json'))) { throw 'Hash mismatch was executed.' }
    'PASS: fixed commit, Git blob digest, arguments, temporary cleanup, mismatch rejected before execution.'
} finally { Remove-Item -LiteralPath $scratch -Recurse -Force }
