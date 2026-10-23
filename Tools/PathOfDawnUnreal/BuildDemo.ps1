#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [string]$BuildId, [ValidateSet('Development','Shipping')][string]$Configuration='Development')
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
if (-not $BuildId) { $BuildId = New-DawnBuildId }
Assert-DawnBuildId $BuildId
$candidate = Join-Path $script:BuildRoot "Windows/$BuildId"
if (Test-Path -LiteralPath $candidate) { throw "Candidate already exists; choose a new BuildId: $candidate" }
$verification = Join-Path $script:ProjectRoot 'Saved/PathOfDawn/asset-verification-report.json'
Assert-DawnFile $verification
$assetReport = Get-Content -Raw -LiteralPath $verification | ConvertFrom-Json
if ($assetReport.status -ne 'passed' -or $assetReport.mode -ne 'reload-verification') { throw 'Run GenerateDemoAssets.ps1; a successful fresh-editor reload report is required.' }
$requiredAssets = @('/Game/PathOfDawn/Maps/L_Galilee','/Game/PathOfDawn/UI/F_Korean','/Game/PathOfDawn/Narrative/DA_DawnNarrative','/Game/PathOfDawn/Cinematics/LS_Arrival','/Game/PathOfDawn/Characters/BP_Traveler','/Game/PathOfDawn/Characters/BP_DawnGameMode')
$requiredAssets += @('IL_Title_Dawn','IL_Arrival','IL_Portrait_Jesus','IL_Portrait_Simon','IL_Ending_Together','IL_Ending_Witness','IL_Ending_Departure') | ForEach-Object { "/Game/PathOfDawn/Illustrations/$_" }
foreach ($asset in $requiredAssets) { if ($assetReport.required -notcontains $asset) { throw "Asset reload report omitted $asset" } }
foreach ($asset in $assetReport.required) {
    if ($asset -notmatch '^/Game/PathOfDawn/[A-Za-z0-9_/]+$') { throw "Unexpected asset path in report: $asset" }
    $extension = if ($asset -eq '/Game/PathOfDawn/Maps/L_Galilee') { '.umap' } else { '.uasset' }
    Assert-DawnFile (Join-Path $script:ProjectRoot ('Content/' + $asset.Substring(6) + $extension))
}
$uat = Join-Path $resolved 'Engine/Build/BatchFiles/RunUAT.bat'
Assert-DawnFile $uat
New-Item -ItemType Directory -Path $candidate | Out-Null
Invoke-DawnCommand $uat @('BuildCookRun',"-project=$script:ProjectFile",'-noP4','-platform=Win64',"-clientconfig=$Configuration",'-build','-cook','-map=/Game/PathOfDawn/Maps/L_Galilee','-stage','-pak','-iostore','-archive',"-archivedirectory=$candidate",'-prereqs','-utf8output') (Join-Path $script:EvidenceRoot "BuildDemo-$BuildId.log")
$exe = Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter 'PathOfDawnUnreal.exe' | Sort-Object {$_.FullName.Length} | Select-Object -First 1
if (-not $exe) { throw 'UAT returned success but packaged launcher is missing.' }
$runtimeExe = Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter 'PathOfDawnUnreal*.exe' | Where-Object { $_.DirectoryName -match '[\\/]Binaries[\\/]Win64$' } | Select-Object -First 1
if (-not $runtimeExe) { throw 'Packaged Win64 game binary is missing.' }
if (@(Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter '*.utoc').Count -eq 0) { throw 'Expected cooked IoStore data not found.' }
$notices = Join-Path $candidate 'ThirdPartyNotices'
New-Item -ItemType Directory -Path $notices -Force | Out-Null
$fontLicense = Join-Path $script:RepoRoot 'SourceArt/PathOfDawnUnreal/Fonts/LICENSE-Debian-Noto.txt'
Assert-DawnFile $fontLicense
Copy-Item -LiteralPath $fontLicense -Destination (Join-Path $notices 'LICENSE-Debian-Noto.txt')
$manifest = [ordered]@{buildId=$BuildId; builtUtc=[DateTime]::UtcNow.ToString('O'); configuration=$Configuration; executable=[IO.Path]::GetRelativePath($candidate,$exe.FullName); runtimeExecutable=[IO.Path]::GetRelativePath($candidate,$runtimeExe.FullName); engineVersion=(Get-Content -Raw -LiteralPath (Join-Path $resolved 'Engine/Build/Build.version') | ConvertFrom-Json); payloadSha256=(Get-DawnPayloadHash $candidate); graphicalSmoke='Not performed'; streaming='Not performed'}
Write-DawnJson (Join-Path $candidate 'build-manifest.json') $manifest
Write-Host "Packaged candidate: $candidate. Graphical launch, extracted ZIP and streaming remain separate checks."
