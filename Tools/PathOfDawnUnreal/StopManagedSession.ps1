#requires -Version 5.1
[CmdletBinding()]
param([string]$InstallRoot='C:\PathOfDawn')
$ErrorActionPreference='Stop'
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Stopping a Windows game requires its Windows host.' }
    $root=[IO.Path]::GetFullPath($InstallRoot)
    $last=Join-Path $root 'last-launch.json'
    if (-not (Test-Path -LiteralPath $last -PathType Leaf)) { Write-Host 'No managed game session has been launched from this installation.'; exit 0 }
    $record=Get-Content -Raw -LiteralPath $last | ConvertFrom-Json
    if ($record.commit -cnotmatch '^[a-f0-9]{40}$') { throw 'Invalid managed session record. No processes were stopped.' }
    $source=Join-Path $root ('versions/source-'+$record.commit.Substring(0,12))
    $receipt=Get-Content -Raw -LiteralPath (Join-Path $source '.dawn-source.json') | ConvertFrom-Json
    if ($receipt.repository -ne 'ka8877/unreal_yesu' -or $receipt.commit -ne $record.commit) { throw 'Source identity does not match the session record.' }
    foreach ($relative in @('Tools/PathOfDawnUnreal/Common.ps1','Tools/PathOfDawnUnreal/StopStreaming.ps1')) {
        $expected=@($receipt.files | Where-Object { $_.path -eq $relative })
        if ($expected.Count -ne 1 -or (Get-FileHash -LiteralPath (Join-Path $source $relative) -Algorithm SHA256).Hash -ne $expected[0].sha256) {
            throw 'The local stop script has changed. No modified script was executed and no process was stopped.'
        }
    }
    $command=Get-Command pwsh.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $shell=if ($command) { $command.Source } else { Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'PowerShell/7/pwsh.exe' }
    if (-not (Test-Path -LiteralPath $shell -PathType Leaf)) { throw 'PowerShell 7 was not found.' }
    $ErrorActionPreference='Continue'; $PSNativeCommandUseErrorActionPreference=$false
    & $shell -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $source 'Tools/PathOfDawnUnreal/StopStreaming.ps1') -IncludeLocalGame
    $result=$LASTEXITCODE
    if ($null -eq $result) { throw 'The stop command did not return a status.' }
    exit $result
} catch { Write-Host "Stop failed: $($_.Exception.Message)"; exit 1 }
