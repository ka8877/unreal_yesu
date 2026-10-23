#requires -Version 7.2
[CmdletBinding()]
param()
. "$PSScriptRoot/Common.ps1"
$lock = Get-Content -Raw -LiteralPath (Join-Path $script:StreamRoot 'versions.lock.json') | ConvertFrom-Json
$git = (Get-Command git -ErrorAction Stop).Source
$node = (Get-Command node -ErrorAction Stop).Source
$npm = (Get-Command npm -ErrorAction Stop).Source
if ((& $node --version).Trim() -ne $lock.node) { throw "Use Node $($lock.node), matching the upstream NODE_VERSION pin. Current $(& $node --version)." }
if ((& $npm --version).Trim() -ne $lock.npm) { throw "Use npm $($lock.npm) bundled with the pinned Node installation." }
$vendor = Join-Path $script:StreamRoot 'vendor/PixelStreamingInfrastructure'
if (-not (Test-Path -LiteralPath $vendor)) {
    Invoke-DawnCommand $git @('clone','--depth','1','--branch',$lock.branch,$lock.repository,$vendor) (Join-Path $script:EvidenceRoot 'streaming-clone.log')
}
$origin = (& $git -C $vendor remote get-url origin).Trim()
if ($origin.TrimEnd('/') -ne $lock.repository.TrimEnd('/')) { throw "Unexpected vendor origin: $origin" }
if (@(& $git -C $vendor status --porcelain).Count -gt 0) { throw 'Vendor has local changes. Do not overwrite them.' }
if ((& $git -C $vendor rev-parse HEAD).Trim() -ne $lock.commit) {
    Invoke-DawnCommand $git @('-C',$vendor,'fetch','origin',$lock.commit,'--depth','1') (Join-Path $script:EvidenceRoot 'streaming-fetch.log')
    Invoke-DawnCommand $git @('-C',$vendor,'checkout','--detach',$lock.commit) (Join-Path $script:EvidenceRoot 'streaming-checkout.log')
}
Push-Location $vendor
try {
    Invoke-DawnCommand $npm @('ci','--ignore-scripts','--cache',(Join-Path $script:StreamRoot 'runtime/npm-cache')) (Join-Path $script:EvidenceRoot 'streaming-npm-ci.log')
    Invoke-DawnCommand $npm @('run','build:all:cjs') (Join-Path $script:EvidenceRoot 'streaming-build.log')
} finally { Pop-Location }
Assert-DawnFile (Join-Path $vendor 'SignallingWebServer/www/player.html')
Invoke-DawnCommand $node @((Join-Path $script:StreamRoot 'test-server.mjs'),'--vendor',$vendor) (Join-Path $script:EvidenceRoot 'streaming-server-tests.log')
Write-Host 'Infrastructure prepared and connection-policy tests passed. This is not a video/audio/gameplay test.'
