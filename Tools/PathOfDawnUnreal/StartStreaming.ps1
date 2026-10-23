#requires -Version 7.2
[CmdletBinding()]
param([Parameter(Mandatory)][string]$BuildId, [string]$EngineRoot, [ValidateSet('720p','1080p')][string]$Resolution='720p', [ValidateSet(30,60)][int]$FramesPerSecond=30, [switch]$TestCandidate)
. "$PSScriptRoot/Common.ps1"
Assert-WindowsHost
$resolved = Resolve-DawnEngine $EngineRoot
$candidate = Get-DawnCandidate $BuildId
$manifest = Get-DawnManifest $candidate
if ($TestCandidate) {
    if ((Get-DawnPayloadHash $candidate) -ne $manifest.payloadSha256) { throw 'Candidate payload changed after build. Rebuild before testing.' }
    Write-Host 'UNVERIFIED CANDIDATE: localhost-only first test. Actual video/audio/input still require observation. This does not certify or promote the build.'
} else { Assert-DawnSmoke $candidate (Join-Path $candidate 'smoke-report.json') | Out-Null }
if ($manifest.engineVersion.MajorVersion -ne 5 -or $manifest.engineVersion.MinorVersion -ne 8) { throw 'Package/streaming engine major/minor mismatch.' }
$plugin = @(Get-ChildItem -LiteralPath (Join-Path $resolved 'Engine/Plugins') -Recurse -Filter 'PixelStreaming2.uplugin')
if ($plugin.Count -ne 1) { throw 'Installed PixelStreaming2 plugin could not be uniquely verified.' }
$lock = Get-Content -Raw -LiteralPath (Join-Path $script:StreamRoot 'versions.lock.json') | ConvertFrom-Json
$vendor = Join-Path $script:StreamRoot 'vendor/PixelStreamingInfrastructure'
$node = (Get-Command node -ErrorAction Stop).Source
if ((& $node --version).Trim() -ne $lock.node) { throw "Node $($lock.node) is required." }
$git = (Get-Command git -ErrorAction Stop).Source
if ((& $git -C $vendor rev-parse HEAD).Trim() -ne $lock.commit) { throw 'Infrastructure SHA mismatch. Run PrepareStreaming.ps1.' }
Assert-DawnFile (Join-Path $vendor 'SignallingWebServer/www/player.html')
foreach ($port in @(8080,8888)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is already in use. No unrelated process will be stopped." }
}
$runtime = Join-Path $script:StreamRoot 'runtime'
$config = Join-Path $runtime 'server-config.json'
$exe = Join-Path $candidate $manifest.runtimeExecutable
Assert-DawnFile $exe
$size = if ($Resolution -eq '720p') { @(1280,720) } else { @(1920,1080) }
$hostRoot = Get-DawnHostRoot
$startMutex = [Threading.Mutex]::new($false,'Local\PathOfDawnUnrealStreamingStart')
if (-not $startMutex.WaitOne(0)) { $startMutex.Dispose(); throw 'Another streaming start is in progress.' }
$createdServer = $false
$createdGame = $false
try {
    Write-Host 'Starting offscreen Unreal rendering. The game picture appears in the browser, not in an Unreal log window.'
    Write-Host 'Player address: http://127.0.0.1:8080/ . Keep the host running; click the page and video start buttons.'
    Write-DawnJson $config @{vendor=$vendor; buildId=$BuildId; payloadSha256=$manifest.payloadSha256; port=8080; streamerPort=8888; logRoot=(Join-Path $runtime 'logs')}
    $server = Start-DawnProcess 'signalling' $node @((Join-Path $script:StreamRoot 'server.mjs'),'--config',$config) $script:StreamRoot
    $createdServer = $true
    $game = Start-DawnProcess 'stream-game' $exe @('-RenderOffscreen','-ForceRes',"-ResX=$($size[0])","-ResY=$($size[1])",'-AudioMixer','-Unattended','-StdOut','-FullStdOutLogOutput','-PixelStreamingURL=ws://127.0.0.1:8888',"-PixelStreamingWebRTCMaxFps=$FramesPerSecond","-DawnBuildId=$BuildId","-UserDir=$hostRoot",'-log') (Split-Path -Parent $exe)
    $createdGame = $true
    $ready = $false
    for ($attempt=0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        if ($server.HasExited -or $game.HasExited) { throw 'A streaming process exited before registration. Inspect runtime/logs and game logs.' }
        try { $status = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/status' -TimeoutSec 2; $ready = $status.streamerRegistered -and $status.hostBuildId -eq $BuildId } catch { $ready = $false }
        if ($ready) { break }
    }
    if (-not $ready) { throw 'No Unreal streamer registered within 45 seconds. HTTP availability alone is insufficient.' }
    if (-not $TestCandidate) { Write-DawnJson (Join-Path $runtime 'current.json') @{buildId=$BuildId; switchedUtc=[DateTime]::UtcNow.ToString('O'); payloadSha256=$manifest.payloadSha256} }
    Write-Host 'Streamer registered: http://127.0.0.1:8080/ (same host only). Now verify actual video, audio, movement, choices and rewind. Registration is not media proof.'
} catch {
    # Detached processes write to their own files; preserve useful startup errors
    # in the launcher log before cleaning up this attempt's owned processes.
    foreach ($role in @('signalling','stream-game')) {
        $recordPath = Join-Path $runtime "$role.process.json"
        if (Test-Path -LiteralPath $recordPath) {
            $record = Get-Content -Raw -LiteralPath $recordPath | ConvertFrom-Json
            if ($record.PSObject.Properties.Name -contains 'stderrLog' -and $record.stderrLog -and (Test-Path -LiteralPath $record.stderrLog)) {
                Write-Host "Startup stderr ($role): $($record.stderrLog)"
                Get-Content -LiteralPath $record.stderrLog -Tail 16 | ForEach-Object { Write-Host $_ }
            }
        }
    }
    if ($createdGame) { Stop-DawnProcess 'stream-game' }
    if ($createdServer) { Stop-DawnProcess 'signalling' }
    throw
} finally { $startMutex.ReleaseMutex(); $startMutex.Dispose() }
