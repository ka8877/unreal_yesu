#requires -Version 7.2
[CmdletBinding()]
param([string[]]$AssetRoots,[switch]$OpenOfficialPages)
. (Join-Path $PSScriptRoot '../Common.ps1')
Assert-WindowsHost
$output=Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Path $output -Force | Out-Null
if (-not $AssetRoots) {
    $AssetRoots=@((Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Unreal Projects')) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
}
$stamp=(New-DawnBuildId)+'-'+[guid]::NewGuid().ToString('N').Substring(0,6)
Write-Host '말씀의 여정 — 실제 아트 자산 준비'
Write-Host '기존 게임과 서버는 유지합니다. 유료 구매·계정 로그인·약관 동의는 자동 처리하지 않습니다.'
if ($AssetRoots) {
    & (Join-Path $PSScriptRoot 'CollectAssetInventory.ps1') -Roots $AssetRoots -Output (Join-Path $output "asset-inventory-$stamp.json")
} else {
    Write-Host '기본 Unreal Projects 폴더를 찾지 못했습니다. 다른 위치가 있다면 -AssetRoots 인자로 지정할 수 있습니다.'
}
$sampleUrl='https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016'
$metaHumanUrl='https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-creator'
Write-Host ''
Write-Host '무료 이동 기반: Game Animation Sample (Epic Games)'
Write-Host $sampleUrl
Write-Host 'Fab에서 본인 계정으로 라이브러리에 추가한 뒤 Epic Games Launcher에서 UE 5.8용 별도 프로젝트를 만드세요.'
Write-Host '이 샘플의 현대 복장·기본 인물을 최종 성경 인물로 사용하지 않습니다. 리타기팅과 복식 검증이 별도로 필요합니다.'
Write-Host ''
Write-Host '성인 인물 기반: 설치된 UE 5.8의 옵션에서 MetaHuman Creator Core Data를 확인하세요.'
Write-Host $metaHumanUrl
Write-Host 'Creator의 성인 인물만으로 아기·열두 살 인물·시대 의상·완성된 석조 공간이 확보되지는 않습니다.'
Write-Host '계정/약관이 필요한 다운로드는 이 도구가 대신 동의할 수 없습니다. 실제 설치 상태는 아직 검증하지 않았습니다.'
if ($OpenOfficialPages) {
    Start-Process $sampleUrl
    Start-Process $metaHumanUrl
}
Write-Host ''
Write-Host '계정 없이 확보한 CC0 환경 원본은 이 소스에 이미 포함되어 있습니다.'
Write-Host 'Windows Editor에서 환경 원본만 가져오는 명령:'
Write-Host "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'PrepareRebuild.ps1')`" -EngineRoot `"C:\Program Files\Epic Games\UE_5.8`" -ImportSourcesOnly"
Write-Host '라이선스 제한이 있는 Fab/MetaHuman 원본은 공개 GitHub에 올리지 마세요. 로컬 바인딩은 .local 아래에 보관하세요.'
