#requires -Version 7.2
[CmdletBinding()]
param([Parameter(Mandatory)][string]$BuildId, [string]$SmokeReport)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$candidate = Get-DawnCandidate $BuildId
if (-not $SmokeReport) { $SmokeReport = Join-Path $candidate 'smoke-report.json' }
Assert-DawnSmoke $candidate $SmokeReport | Out-Null
$zip = Join-Path $script:BuildRoot "PathOfDawn-Demo-Windows-$BuildId.zip"
if (Test-Path -LiteralPath $zip) { throw "Archive exists; refusing to overwrite: $zip" }
$staging = Join-Path ([IO.Path]::GetTempPath()) "PathOfDawn-package-$([guid]::NewGuid().ToString('N'))"
$extract = Join-Path $script:BuildRoot "Extracted/$BuildId"
if (Test-Path -LiteralPath $extract) { throw "Extraction directory exists: $extract" }
try {
    New-Item -ItemType Directory -Path $staging | Out-Null
    foreach ($file in (Get-ChildItem -LiteralPath $candidate -Recurse -File)) {
        if ($file.FullName -match '[\\/]Saved[\\/]' -or $file.Extension -in @('.pdb','.exp','.lib','.pem','.key') -or $file.Name -eq 'smoke-report.json') { continue }
        $relative = [IO.Path]::GetRelativePath($candidate,$file.FullName)
        $destination = Join-Path $staging $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
    [IO.Compression.ZipFile]::CreateFromDirectory($staging,$zip,[IO.Compression.CompressionLevel]::Optimal,$false)
    [IO.Compression.ZipFile]::ExtractToDirectory($zip,$extract)
    $manifest = Get-DawnManifest $extract
    if ((Get-DawnPayloadHash $extract) -ne $manifest.payloadSha256) { throw 'Extracted payload differs from tested payload.' }
    "$((Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash)  $([IO.Path]::GetFileName($zip))" | Set-Content -LiteralPath "$zip.sha256" -Encoding utf8
    Write-DawnJson (Join-Path $script:EvidenceRoot "package-$BuildId.json") @{zip=$zip; extractedDirectory=$extract; byteIntegrityVerified=$true; extractedGraphicalLaunch='Not performed'; cleanOtherPc='Not performed'}
    Write-Host "ZIP: $zip"
    Write-Host "Extracted for final actual launch: $(Join-Path $extract $manifest.executable)"
    Write-Host 'Extraction and hashes passed. Run this extracted copy without Editor, verify save/restart, and record actual screenshots before claiming package execution verified.'
} finally { if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force } }
