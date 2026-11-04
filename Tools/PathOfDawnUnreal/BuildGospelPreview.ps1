#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [string]$BuildId, [ValidateSet('Development','Shipping')][string]$Configuration='Development', [string]$SourceCommit, [string]$Python)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
if (-not $BuildId) { $BuildId = New-DawnBuildId }
Assert-DawnBuildId $BuildId
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$candidate = Join-Path $script:BuildRoot "GospelWindows/$BuildId"
if (Test-Path -LiteralPath $candidate) { throw "Candidate already exists; choose a new BuildId: $candidate" }
$evidence = Join-Path $script:EvidenceRoot "GospelHost/Build-$BuildId"
$gospelTools = Join-Path $PSScriptRoot 'Gospel'
$checker = Join-Path $gospelTools 'check_generated_assets.py'
Assert-DawnFile $checker
# Portable checks and original C# byte provenance do not require a .NET SDK.
& "$PSScriptRoot/TestGospel.ps1" -SourceOnly -Python $Python
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
& "$PSScriptRoot/CheckEnvironment.ps1" -EngineRoot $resolved | Tee-Object -FilePath (Join-Path $evidence 'environment-check.log') | Write-Host
Copy-Item -LiteralPath (Join-Path $script:EvidenceRoot 'windows-environment.json') -Destination (Join-Path $evidence 'windows-environment.json')
$sourceDirty = $null
$observedCommit = $null
$identityMethod = 'supplied-commit'
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    $head = & $git.Source -C $script:RepoRoot rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0) {
        $observedCommit = [string]$head
        $sourceDirty = [bool](& $git.Source -C $script:RepoRoot status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect source working-tree status.' }
        $identityMethod = 'git-head'
    }
}
if (-not $observedCommit) {
    $receipt = Join-Path $script:RepoRoot '.dawn-source.json'
    if (Test-Path -LiteralPath $receipt -PathType Leaf) {
        $observedCommit = [string]((Get-Content -Raw -LiteralPath $receipt | ConvertFrom-Json).commit)
        $identityMethod = 'source-receipt'
    }
}
if ($SourceCommit -and $observedCommit -and $SourceCommit -cne $observedCommit) { throw 'Supplied source commit differs from the observed Unreal checkout/source receipt.' }
if (-not $SourceCommit) { $SourceCommit = $observedCommit }
if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') { throw 'An Unreal source identity is required. Use an immutable Git checkout/source receipt or supply -SourceCommit <full lowercase SHA>.' }
$map = '/Game/PathOfDawnGospel/Maps/L_GospelTemplePreview'
$verification = Join-Path $script:ProjectRoot 'Saved/PathOfDawnGospel/asset-verification-report.json'
Assert-DawnFile $verification
$mutex = [Threading.Mutex]::new($false, 'Local\PathOfDawnUnrealEditorAssets')
$owned = $false
try {
    try { $owned = $mutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] {
        $owned = $true
        throw 'A previous Editor asset operation ended unexpectedly. Inspect saved reports and generated packages before retrying.'
    }
    if (-not $owned) { throw 'Another PathOfDawn asset operation is running; packaging requires a stable asset set.' }
    if (@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object { $_.CommandLine -like '*PathOfDawnUnreal.uproject*' }).Count -gt 0) {
        throw 'Close the PathOfDawnUnreal Editor before packaging the Gospel preview.'
    }
    # Reject stale reports and changed .uasset/.umap bytes before UAT.
    Invoke-DawnCommand $Python @($checker) (Join-Path $evidence 'generated-package-check.log')
    $assetReport = Get-Content -Raw -LiteralPath $verification | ConvertFrom-Json
    if ($assetReport.status -ne 'passed' -or $assetReport.mode -ne 'reload-verification') { throw 'Run GenerateGospelAssets.ps1; fresh Editor reload verification is required.' }
    $uat = Join-Path $resolved 'Engine/Build/BatchFiles/RunUAT.bat'
    Assert-DawnFile $uat
    New-Item -ItemType Directory -Path $candidate | Out-Null
    # Forward the engine override through UAT to the real cooker; do not rewrite
    # the preserved project configuration. Arrays cannot use -ini overrides, so
    # an existing legacy AlwaysCook directory can still add legacy content.
    # Official config syntax: dev.epicgames.com/documentation/unreal-engine/configuration-files-in-unreal-engine
    $cookerOptions = "-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap=$map -NoDefaultMaps -CookDir=/Game/PathOfDawnGospel"
    $arguments = @('BuildCookRun',"-project=$script:ProjectFile",'-noP4','-platform=Win64',"-clientconfig=$Configuration",'-build','-cook',"-map=$map",'-CookDir=/Game/PathOfDawnGospel',"-AdditionalCookerOptions=$cookerOptions",'-stage','-pak','-iostore','-archive',"-archivedirectory=$candidate",'-prereqs','-nodebuginfo','-utf8output')
    Invoke-DawnCommand $uat $arguments (Join-Path $evidence 'BuildGospelPreview.log')
    # Ensure no source package changed while Cook was reading it.
    Invoke-DawnCommand $Python @($checker) (Join-Path $evidence 'generated-package-postcook-check.log')
    $launcher = Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter 'PathOfDawnUnreal.exe' | Sort-Object {$_.FullName.Length} | Select-Object -First 1
    $runtime = @(Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter 'PathOfDawnUnreal*.exe' | Where-Object { $_.DirectoryName -match '[\\/]Binaries[\\/]Win64$' })
    if (-not $launcher -or $runtime.Count -ne 1) { throw 'UAT returned success without exactly one packaged Win64 game binary and launcher.' }
    if (@(Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter '*.utoc').Count -eq 0 -or @(Get-ChildItem -LiteralPath $candidate -Recurse -File -Filter '*.ucas').Count -eq 0) { throw 'Cooked IoStore containers were not produced.' }
    $notices = Join-Path $candidate 'ThirdPartyNotices'
    New-Item -ItemType Directory -Path $notices | Out-Null
    $license = Join-Path $script:RepoRoot 'SourceArt/PathOfDawnUnreal/Fonts/LICENSE-Debian-Noto.txt'
    Assert-DawnFile $license
    Copy-Item -LiteralPath $license -Destination (Join-Path $notices 'LICENSE-Debian-Noto.txt')
    $campaignFile = Join-Path $script:RepoRoot 'SourceArt/PathOfDawnUnreal/Gospel/Campaign.json'
    $campaign = Get-Content -Raw -LiteralPath $campaignFile -Encoding utf8 | ConvertFrom-Json
    $notice = @('말씀을 따라 예수님의 길 · 성경 본문 출처', '')
    foreach ($reading in $campaign.Readings) { $notice += "$($reading.Reference) — $($reading.Source)" }
    $notice += @('', '성경 직접 인용·본문 요약·게임을 위한 극화는 게임 안에서 구분합니다.', "Unity story source: $($campaign.Source.Repository) @ $($campaign.Source.Commit)", 'Gospel preview is a development blockout; cinematic final art/BGM and graphical validation remain pending.')
    [IO.File]::WriteAllText((Join-Path $notices 'Scripture-Provenance.txt'), ($notice -join "`r`n"), [Text.UTF8Encoding]::new($false))
    $relativeLauncher = [IO.Path]::GetRelativePath($candidate,$launcher.FullName)
    $launchText = "@echo off`r`npushd `"%~dp0`"`r`n`"%~dp0$relativeLauncher`" $map %*`r`npopd`r`n"
    [IO.File]::WriteAllText((Join-Path $candidate 'Launch-GospelPreview.cmd'), $launchText, [Text.Encoding]::ASCII)
    $files = @(Get-ChildItem -LiteralPath $candidate -Recurse -File | Sort-Object FullName | ForEach-Object {
        [ordered]@{path=[IO.Path]::GetRelativePath($candidate,$_.FullName).Replace('\','/'); bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    })
    $manifest = [ordered]@{buildId=$BuildId; builtUtc=[DateTime]::UtcNow.ToString('O'); configuration=$Configuration; sourceCommit=$SourceCommit; sourceDirty=$sourceDirty; sourceIdentityMethod=$identityMethod; unitySourceCommit=$campaign.Source.Commit; campaignSha256=$assetReport.campaignSha256; recipeSha256=$assetReport.recipeSha256; generatorSha256=$assetReport.generatorSha256; map=$map; cookerOptions=$cookerOptions; previewQuestIds=@($campaign.Quests | Where-Object {$_.ChapterId -eq 'temple'} | ForEach-Object {$_.Id}); executable=$relativeLauncher.Replace('\','/'); runtimeExecutable=[IO.Path]::GetRelativePath($candidate,$runtime[0].FullName).Replace('\','/'); engineVersion=(Get-Content -Raw -LiteralPath (Join-Path $resolved 'Engine/Build/Build.version') | ConvertFrom-Json); files=$files; payloadSha256=(Get-DawnPayloadHash $candidate); graphicalSmoke='not-performed'; streaming='not-performed'; publicDeployment='not-performed'; visualQuality='development-blockout'}
    $manifest['runtimeSourceSha256'] = $assetReport.runtimeSourceSha256
    Write-DawnJson (Join-Path $candidate 'build-manifest.json') $manifest
    Write-Host "Packaged Gospel candidate: $candidate"
    Write-Host 'No public promotion occurred. Extracted-package graphical launch, gameplay, audio and streaming still require actual GPU-host verification.'
} finally {
    if ($owned) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
