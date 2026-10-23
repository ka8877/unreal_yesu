#requires -Version 7.2
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common.ps1')
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('Path of Dawn tooling ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
$originalStreamRoot = $script:StreamRoot
$checks = 0
function Require([bool]$Condition,[string]$Message) { if (-not $Condition) { throw $Message }; $script:checks++ }
function MustReject([scriptblock]$Action,[string]$Message) { $rejected=$false; try { & $Action } catch { $rejected=$true }; Require $rejected $Message }
try {
    MustReject { Assert-DawnBuildId '../escape' } 'Traversal build ID accepted'
    MustReject { Assert-DawnBuildId 'id;command' } 'Shell punctuation build ID accepted'
    Assert-DawnBuildId 'demo-001'
    $payload = Join-Path $temporary 'game data.bin'
    [IO.File]::WriteAllText($payload, 'payload-v1')
    $hash = Get-DawnPayloadHash $temporary
    Write-DawnJson (Join-Path $temporary 'build-manifest.json') @{buildId='demo-001';payloadSha256=$hash}
    Require ((Get-DawnPayloadHash $temporary) -eq $hash) 'Manifest changed payload hash'
    [IO.File]::WriteAllText((Join-Path $temporary 'debug.pdb'),'debug')
    Require ((Get-DawnPayloadHash $temporary) -eq $hash) 'Excluded debug file changed distribution hash'
    New-Item -ItemType Directory -Path (Join-Path $temporary 'Saved') | Out-Null
    [IO.File]::WriteAllText((Join-Path $temporary 'Saved/user.sav'),'private-user-save')
    Require ((Get-DawnPayloadHash $temporary) -eq $hash) 'User save changed distribution hash'
    $report = Join-Path $temporary 'report.json'
    Write-DawnJson $report @{buildId='wrong-build';payloadSha256=$hash}
    MustReject { Assert-DawnSmoke $temporary $report } 'Wrong-build smoke was accepted'
    Remove-Item -LiteralPath $report
    $report = Join-Path $temporary 'smoke-report.json'
    Write-DawnJson $report @{buildId='demo-001';payloadSha256=$hash;checks=@{graphicalLaunch=$false}}
    MustReject { Assert-DawnSmoke $temporary $report } 'Unperformed graphics was accepted'
    [IO.File]::WriteAllText($payload,'payload-v2')
    MustReject { Assert-DawnSmoke $temporary $report } 'Changed payload was accepted'
    $record = Join-Path $temporary 'atomic.json'
    Write-DawnJson $record @{name='first'}
    Write-DawnJson $record @{name='second'}
    Require ((Get-Content -Raw -LiteralPath $record | ConvertFrom-Json).name -eq 'second') 'Atomic replacement failed'
    Require (@(Get-ChildItem -LiteralPath $temporary -Filter '*.tmp').Count -eq 0) 'Atomic temporary file leaked'
    $script:StreamRoot = $temporary
    $pwshPath = (Get-Process -Id $PID).Path
    $owned = Start-DawnProcess 'local-game' $pwshPath @('-NoLogo','-NoProfile','-Command','Start-Sleep -Seconds 15') $temporary
    Require (Test-DawnProcessRunning 'local-game') 'Owned process identity was not recognized'
    MustReject { Start-DawnProcess 'stream-game' $pwshPath @('-NoLogo','-NoProfile','-Command','Start-Sleep -Seconds 15') $temporary } 'Two games could share one save session'
    Stop-DawnProcess 'local-game'
    Require (-not (Test-DawnProcessRunning 'local-game')) 'Owned process did not stop'
    Write-DawnJson (Join-Path $temporary 'runtime/unrelated.process.json') @{pid=$PID;startedUtc='not-this-process-start';startIdentity='not-this-process-start';executable=$pwshPath;role='unrelated'}
    MustReject { Stop-DawnProcess 'unrelated' } 'Stop accepted an unrelated/reused PID'
    Write-Output "PASS $checks tooling assertions (space paths, unsafe IDs, hashes, smoke rejection, atomic JSON, session exclusion, owned-process cleanup). Host: $([Environment]::OSVersion.Platform); no Unreal/media test."
} finally {
    if ($script:StreamRoot -eq $temporary) { Stop-DawnProcess 'local-game'; Stop-DawnProcess 'stream-game' }
    $script:StreamRoot = $originalStreamRoot
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
