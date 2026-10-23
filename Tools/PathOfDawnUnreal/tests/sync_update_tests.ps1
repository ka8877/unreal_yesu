#requires -Version 7.2
# Test real updater functions with synthetic archives/processes; no Unreal launch.
$ErrorActionPreference='Stop'
$path=Join-Path $PSScriptRoot '../SyncAndPlay.ps1'
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
foreach ($function in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)) { Invoke-Expression $function.Extent.Text }
$script:checks=0
function Check([bool]$Value,[string]$Message) { if (-not $Value) { throw $Message }; $script:checks++ }
function Rejected([scriptblock]$Action,[string]$Message) {
    $caught=$null; try { & $Action | Out-Null } catch { $caught=$_.Exception.Message }
    Check ([bool]$caught) $Message
}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('dawn-sync-tests-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temporary)
$commit='0123456789abcdef0123456789abcdef01234567'
$required=@('Start-PathOfDawn.cmd','Tools/PathOfDawnUnreal/StartHere.ps1','Tools/PathOfDawnUnreal/SyncAndPlay.ps1','Tools/PathOfDawnUnreal/Bootstrap.ps1','Tools/PathOfDawnUnreal/StopManagedSession.ps1','Games/PathOfDawnUnreal/PathOfDawnUnreal.uproject','SourceArt/PathOfDawnUnreal/Narrative/episode.json','SourceArt/PathOfDawnUnreal/VisualV8/Illustrations/IL_Title_Dawn.png')
function Archive([string]$Name,[string[]]$Extra=@(),[switch]$Lfs,[switch]$OmitRequired) {
    $archivePath=Join-Path $temporary "$Name.zip"
    $zip=[IO.Compression.ZipFile]::Open($archivePath,[IO.Compression.ZipArchiveMode]::Create)
    try {
        $files=if ($OmitRequired) { $required[0..6] } else { $required }
        foreach ($file in @($files)+$Extra) {
            $entry=$zip.CreateEntry("unreal_yesu-$commit/$file")
            $writer=[IO.StreamWriter]::new($entry.Open())
            try { $writer.Write($(if ($Lfs -and $file.EndsWith('.png')) { "version https://git-lfs.github.com/spec/v1`noid sha256:abc`nsize 9000" } else { 'fixture '+$file })) } finally { $writer.Dispose() }
        }
    } finally { $zip.Dispose() }
    return $archivePath
}
try {
    $valid=Archive 'valid' @('Docs/PathOfDawnUnreal/Evidence/generated.json','folder with spaces/test.txt')
    $destination=Join-Path $temporary 'source'
    Expand-SyncArchive $valid $destination $commit
    Assert-SyncSource $destination $commit
    Check (Test-Path -LiteralPath (Join-Path $destination '.dawn-source.json')) 'Receipt missing.'
    Check (Test-Path -LiteralPath (Join-Path $destination 'folder with spaces/test.txt')) 'Spaces were not preserved.'
    Set-Content -LiteralPath (Join-Path $destination 'Docs/PathOfDawnUnreal/Evidence/generated.json') -Value 'updated generated evidence'
    Assert-SyncSource $destination $commit
    $script:checks++
    Rejected { Expand-SyncArchive $valid $destination $commit } 'Existing destination was overwritten.'
    Check ((Get-Content -Raw -LiteralPath (Join-Path $destination 'Start-PathOfDawn.cmd')) -like 'fixture*') 'Existing file changed.'
    Set-Content -LiteralPath (Join-Path $destination 'Start-PathOfDawn.cmd') -Value 'user edit'
    Rejected { Assert-SyncSource $destination $commit } 'User edit was ignored.'
    Check ((Get-Content -Raw -LiteralPath (Join-Path $destination 'Start-PathOfDawn.cmd')).Trim() -eq 'user edit') 'User edit was not preserved.'
    Rejected { Assert-SyncSource $destination ('f'*40) } 'Wrong commit receipt accepted.'
    foreach ($bad in @('../outside.txt','bad\outside.txt','bad:stream.txt','NUL.txt','trail.','empty//file.txt','Start-PATHOFDAWN.cmd')) {
        $archivePath=Archive ('unsafe-'+[guid]::NewGuid().ToString('N')) @($bad)
        Rejected { Expand-SyncArchive $archivePath (Join-Path $temporary ('reject-'+[guid]::NewGuid().ToString('N'))) $commit } "Unsafe path accepted: $bad"
    }
    Rejected { Expand-SyncArchive (Archive 'lfs' -Lfs) (Join-Path $temporary 'lfs-source') $commit } 'LFS pointer accepted as artwork.'
    Rejected { Expand-SyncArchive (Archive 'missing' -OmitRequired) (Join-Path $temporary 'missing-source') $commit } 'Missing artwork accepted.'
    Rejected { Expand-SyncArchive $valid (Join-Path $temporary 'wrong-sha') ('f'*40) } 'Archive for wrong commit accepted.'
    Rejected { Expand-SyncArchive $valid (Join-Path $temporary 'bad-sha') 'main' } 'Branch name accepted as immutable SHA.'
    Rejected { Assert-SyncRoot '/tmp/OneDrive/PathOfDawn' } 'OneDrive root accepted.'
    Rejected { Assert-SyncRoot '/tmp/바탕화면/PathOfDawn' } 'Non-ASCII root accepted.'
    Rejected { Assert-SyncRoot '/tmp/Path&OfDawn' } 'Unsafe CMD root accepted.'
    Rejected { Assert-SyncRoot 'relative' } 'Relative root accepted.'
    Check ((Assert-SyncRoot '/tmp/Path Of Dawn').EndsWith('Path Of Dawn')) 'Spaces in root should be supported.'
    $jsonPath=Join-Path $temporary 'atomic.json'
    Write-SyncJson $jsonPath @{value=1}; Write-SyncJson $jsonPath @{value=2}
    Check ((Get-Content -Raw -LiteralPath $jsonPath | ConvertFrom-Json).value -eq 2) 'Atomic JSON replacement failed.'
    $build=Join-Path $temporary 'build-source/Builds/PathOfDawnUnreal/Windows/fixture-build'
    [void][IO.Directory]::CreateDirectory($build)
    Write-SyncJson (Join-Path $build 'build-manifest.json') @{buildId='fixture-build';runtimeExecutable='game.exe'}
    Check ($null -eq (Get-SyncBuild (Join-Path $temporary 'build-source'))) 'Missing executable was accepted.'
    [IO.File]::WriteAllText((Join-Path $build 'game.exe'),'not a real game')
    Check ((Get-SyncBuild (Join-Path $temporary 'build-source')) -eq 'fixture-build') 'Valid package manifest was not reused.'
    Write-SyncJson (Join-Path $build 'build-manifest.json') @{buildId='fixture-build';runtimeExecutable='../outside.exe'}
    Rejected { Get-SyncBuild (Join-Path $temporary 'build-source') } 'Runtime path traversal accepted.'
    $child=Join-Path $temporary 'child.ps1'
    [IO.File]::WriteAllText($child,"param([string]`$Value)`nif (`$Value -ne 'path with spaces') { exit 3 }; exit 0")
    $shell=(Get-Process -Id $PID).Path
    Invoke-SyncChild $shell $child @('-Value','path with spaces'); $script:checks++
    [IO.File]::WriteAllText($child,'exit 42')
    Rejected { Invoke-SyncChild $shell $child } 'Failed child was treated as success.'
    $launcherRoot=Join-Path $temporary 'launcher-root'
    [void][IO.Directory]::CreateDirectory($launcherRoot)
    Install-SyncLaunchers $launcherRoot $destination
    Check (Test-Path -LiteralPath (Join-Path $launcherRoot 'Stop-PathOfDawn.cmd')) 'Stop launcher missing.'
    Install-SyncLaunchers $launcherRoot $destination; $script:checks++
    [IO.File]::WriteAllText((Join-Path $launcherRoot 'Update-PathOfDawn.cmd'),'user launcher edit')
    Rejected { Install-SyncLaunchers $launcherRoot $destination } 'Edited launcher was overwritten.'
    Check ([IO.File]::ReadAllText((Join-Path $launcherRoot 'Update-PathOfDawn.cmd')) -eq 'user launcher edit') 'Edited launcher was not preserved.'

    # Exercise actual session orchestration with process calls replaced by explicit
    # fixtures. This verifies ordering/rollback only, not UE process or rendering.
    $sessionRoot=Join-Path $temporary 'session-root'; $versions=Join-Path $sessionRoot 'versions'
    $oldCommit='1111111111111111111111111111111111111111'
    $newCommit='2222222222222222222222222222222222222222'
    foreach ($sha in @($oldCommit,$newCommit)) {
        $version=Join-Path $versions ('source-'+$sha.Substring(0,12))
        [void][IO.Directory]::CreateDirectory($version)
        Write-SyncJson (Join-Path $version '.dawn-source.json') @{schema=1;repository='ka8877/unreal_yesu';commit=$sha;files=@()}
    }
    $oldRecord=@{commit=$oldCommit;buildId='old-build';streaming=$true;engineRoot='C:\Engine With Spaces'}
    $script:calls=@(); $script:failNew=$false; $script:unowned=$false
    function Invoke-SyncChild([string]$Shell,[string]$ScriptPath,[string[]]$Arguments=@()) {
        $script:calls += [pscustomobject]@{path=$ScriptPath;arguments=$Arguments}
        if ($script:failNew -and $ScriptPath -like '*source-222222222222*StartHere.ps1') { throw 'fixture: new launch failed' }
    }
    function Get-Process { if ($script:unowned) { [pscustomobject]@{Id=123;Name='PathOfDawnUnreal-Legacy'} } }
    Write-SyncJson (Join-Path $sessionRoot 'last-launch.json') $oldRecord
    Invoke-SyncLaunch $sessionRoot $newCommit 'new-build' 'C:\Engine With Spaces' $true 'shell' 'pwsh'
    Check ($script:calls[0].path -like '*source-111111111111*StopStreaming.ps1') 'Previous source process was not stopped first.'
    Check (($script:calls[-1].arguments -contains '-TestCandidate') -and ($script:calls[-1].arguments -contains 'C:\Engine With Spaces')) 'Browser candidate or engine path arguments were lost.'
    Check ((Get-Content -Raw -LiteralPath (Join-Path $sessionRoot 'last-launch.json') | ConvertFrom-Json).commit -eq $newCommit) 'Successful launch receipt was not switched.'
    Check ((Get-Content -Raw -LiteralPath (Join-Path $sessionRoot 'previous-launch.json') | ConvertFrom-Json).commit -eq $oldCommit) 'Previous source was not recorded.'
    Write-SyncJson (Join-Path $sessionRoot 'last-launch.json') $oldRecord
    $script:calls=@(); $script:failNew=$true
    Rejected { Invoke-SyncLaunch $sessionRoot $newCommit 'new-build' '' $false 'shell' 'pwsh' } 'New launch failure was hidden.'
    Check ($script:calls[-1].path -like '*source-111111111111*StartHere.ps1') 'Failed launch did not restart previous source.'
    Check ($script:calls[-1].arguments -contains '-Streaming') 'Rollback lost the previous browser mode.'
    Check ((Get-Content -Raw -LiteralPath (Join-Path $sessionRoot 'last-launch.json') | ConvertFrom-Json).commit -eq $oldCommit) 'Failed launch replaced last-launch receipt.'
    $script:calls=@(); $script:failNew=$false; $script:unowned=$true
    Rejected { Invoke-SyncLaunch $sessionRoot $newCommit 'new-build' '' $false 'shell' 'pwsh' } 'Unowned existing game was ignored.'
    Check (@($script:calls | Where-Object { $_.path -like '*StartHere.ps1' }).Count -eq 0) 'Updater started a second game while an unowned game was running.'
    "PASS: $script:checks updater archive/path/hash/build-reuse/process checks. No Unreal run was performed."
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
