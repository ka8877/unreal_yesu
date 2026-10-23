#requires -Version 5.1
# UTF-8 BOM is intentional: inbox Windows PowerShell 5.1 must read Korean correctly.
# The .cmd uses process-scoped execution policy only; no machine policy is changed.
[CmdletBinding()]
param([string]$EngineRoot, [string]$BuildId, [switch]$Streaming, [switch]$TestCandidate, [switch]$CheckOnly, [switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $OutputEncoding
[Console]::OutputEncoding = $OutputEncoding
# Redirected Python stdout otherwise follows the Windows locale, not the console
# code page. All downstream PowerShell logs expect UTF-8 native output.
$env:PYTHONIOENCODING = 'utf-8'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$diagnostic = Join-Path $repo "Docs/PathOfDawnUnreal/Evidence/start-here-$stamp.json"
$report = [ordered]@{ checkedUtc=[DateTime]::UtcNow.ToString('O'); mode=$(if ($BuildOnly) {'build-only'} elseif ($Streaming) {'streaming'} elseif ($BuildId) {'existing-local'} else {'build-local'}); status='checking'; root=$repo; engine=$null; pwsh=$null; visualStudio=$null; windowsSdk=$null; gpu=@(); python=$null; missing=@(); steps=@(); renderingVerified=$false; encoderVerified=$false; publicUrl=$null }
function Need([string]$Name,[string]$Action,[string]$Link='') { $script:report.missing += [ordered]@{name=$Name;action=$Action;link=$Link} }
function Find-Executable([string]$Name,[string[]]$Candidates=@()) {
    $command=Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and ($Name -eq 'pwsh.exe' -or $command.Source -notlike '*\WindowsApps\*')) { return $command.Source }
    foreach ($candidate in $Candidates) { if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate } }
    return $null
}
function Get-EngineInfo([string]$Location) {
    if (-not $Location) { return $null }
    $file=Join-Path $Location 'Engine/Build/Build.version'
    if (-not (Test-Path -LiteralPath $file)) { return $null }
    try {
        $v=Get-Content -Raw -LiteralPath $file | ConvertFrom-Json
        if ($v.MajorVersion -ne 5 -or $v.MinorVersion -ne 8 -or "$Location $($v.BranchName)" -match 'Preview|ue5-main') { return $null }
        foreach ($required in @('Engine/Binaries/Win64/UnrealEditor.exe','Engine/Binaries/Win64/UnrealEditor-Cmd.exe','Engine/Build/BatchFiles/Build.bat','Engine/Build/BatchFiles/RunUAT.bat')) { if (-not (Test-Path -LiteralPath (Join-Path $Location $required))) { return $null } }
        return [pscustomobject]@{path=[IO.Path]::GetFullPath($Location);version=$v}
    } catch { return $null }
}
function Run-Step([string]$Name,[string]$Script,[string[]]$Arguments=@()) {
    $log=Join-Path (Split-Path -Parent $script:diagnostic) "start-here-$script:stamp-$Name.log"
    $stepFile=Join-Path $PSScriptRoot $Script
    if (-not (Test-Path -LiteralPath $script:pwsh -PathType Leaf)) { throw "PowerShell 실행 파일을 찾지 못했습니다: $script:pwsh" }
    if (-not (Test-Path -LiteralPath $stepFile -PathType Leaf)) { throw "단계 스크립트를 찾지 못했습니다: $stepFile" }
    Write-Host "[$Name] 실행 중입니다. 자세한 기록: $log"
    $previousPreference=$ErrorActionPreference
    try {
        # Windows PowerShell 5.1 treats redirected native stderr as ErrorRecord.
        # Preserve the full child log and exit code instead of stopping on its
        # first stderr line (which used to hide the actual UBT failure).
        $ErrorActionPreference='Continue'
        $PSNativeCommandUseErrorActionPreference=$false
        $global:LASTEXITCODE=$null
        & $script:pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $stepFile @Arguments *> $log
        $code=$LASTEXITCODE
    } finally { $ErrorActionPreference=$previousPreference }
    $stepResult=[ordered]@{name=$Name;exitCode=$code;log=$log;errorSummary=@()}
    $script:report.steps += $stepResult
    if ($null -eq $code -or $code -ne 0) {
        # Native compiler diagnostics often precede the wrapper's final exception
        # by hundreds of lines. Preserve them in the JSON as well as on screen.
        $diagnostics=@(Select-String -LiteralPath $log -Pattern '\b(?:fatal\s+)?error\s+(?:C|LNK|MSB)\d+\s*:|\berror\s*:' -Context 0,2 -ErrorAction SilentlyContinue | Select-Object -First 16)
        $stepResult.errorSummary=@(foreach ($match in $diagnostics) {
            foreach ($line in @($match.Line)+@($match.Context.PostContext)) {
                $clean=$line -replace '\x1B\[[0-?]*[ -/]*[@-~]',''
                if ($clean.Length -gt 2000) { $clean=$clean.Substring(0,2000)+' [truncated; see full log]' }
                $clean
            }
        })
        if ($stepResult.errorSummary.Count -gt 0) {
            Write-Host ''; Write-Host '컴파일/빌드 오류 요약(진단 JSON에도 기록):'
            $stepResult.errorSummary | ForEach-Object { Write-Host $_ }
        }
        Write-Host ''; Write-Host '실패 직전 로그(전체 내용은 위 로그 파일에 보관):'
        Get-Content -LiteralPath $log -Tail 24 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }
        throw "$Name 단계가 완료되지 않았습니다(종료 코드: $code). 상세 원인은 $log 에 기록했습니다. 로그 파일을 보내 주세요."
    }
}
$code=1
try {
    Write-Host '새벽의 길: 갈릴리의 첫 아침 — 내 PC에서 실행 준비'
    Write-Host '이 프로그램은 지금 실행한 Windows PC를 검사합니다. 설치·결제·방화벽 변경은 자동으로 하지 않습니다.'
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw '이 시작 도구는 Windows용입니다. 현재 환경에서는 Windows 게임을 실행할 수 없습니다.' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw '64비트 Windows가 필요합니다.' }
    if ($BuildOnly -and ($Streaming -or $BuildId)) { throw '-BuildOnly는 기존 빌드 실행이나 스트리밍 옵션과 함께 사용할 수 없습니다.' }
    if ($TestCandidate -and -not $Streaming) { throw '-TestCandidate는 -Streaming과 함께 사용하는 첫 브라우저 테스트 옵션입니다.' }
    New-Item -ItemType Directory -Path (Split-Path -Parent $diagnostic) -Force | Out-Null
    $programFiles=[Environment]::GetFolderPath('ProgramFiles')
    $programFilesX86=[Environment]::GetFolderPath('ProgramFilesX86')
    $localApp=[Environment]::GetFolderPath('LocalApplicationData')
    $programData=[Environment]::GetFolderPath('CommonApplicationData')
    $buildRoot=Join-Path $repo 'Builds/PathOfDawnUnreal/Windows'
    if ($Streaming -and -not $BuildId) {
        $current=Join-Path $repo 'Streaming/PathOfDawnUnreal/runtime/current.json'
        if (Test-Path -LiteralPath $current) { $BuildId=(Get-Content -Raw -LiteralPath $current | ConvertFrom-Json).buildId }
        if (-not $BuildId -and (Test-Path -LiteralPath $buildRoot)) {
            $latest=Get-ChildItem -LiteralPath $buildRoot -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'build-manifest.json') } | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
            if ($latest) { $BuildId=$latest.Name }
        }
        if (-not $BuildId) { Need '먼저 Windows 게임 만들기' 'Start-PathOfDawn.cmd를 옵션 없이 실행해 먼저 게임을 만들고 직접 실행하세요.' }
    }
    if ($BuildId) {
        if ($BuildId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$') { throw '빌드 이름에는 영문·숫자·점·밑줄·하이픈만 사용할 수 있습니다.' }
        $candidate=Join-Path $buildRoot $BuildId
        if (-not (Test-Path -LiteralPath (Join-Path $candidate 'build-manifest.json'))) { Need '기존 게임 빌드' "빌드 $BuildId 를 찾지 못했습니다. 옵션 없이 실행하면 새로 빌드합니다." }
        if ($Streaming -and -not $TestCandidate -and -not (Test-Path -LiteralPath (Join-Path $candidate 'smoke-report.json'))) { Need '게임 실행 확인 기록' "빌드 $BuildId 의 실제 플레이 확인 기록이 없습니다. 첫 브라우저 테스트는 -BuildId $BuildId -Streaming -TestCandidate 옵션으로 실행할 수 있습니다. 이 옵션은 검증 완료 처리나 서비스 버전 승격을 하지 않습니다." }
    }
    $needsBuild=(-not $BuildId -and -not $Streaming)
    $needsEngine=$needsBuild -or $Streaming
    $pwsh=Find-Executable 'pwsh.exe' @((Join-Path $programFiles 'PowerShell/7/pwsh.exe'))
    if ($pwsh) { try { $pwshVersion=(& $pwsh -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()' 2>$null | Select-Object -Last 1); if ([version]$pwshVersion -lt [version]'7.2') { $pwsh=$null } } catch { $pwsh=$null } }
    if (-not $pwsh) { Need 'PowerShell 7.2 이상' 'PowerShell 7을 설치한 뒤 이 시작 파일을 다시 실행하세요. 지금 진단에는 Windows 기본 PowerShell을 사용했습니다.' 'https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows' }
    else { $report.pwsh=@{path=$pwsh;version=$pwshVersion} }

    $engineCandidates=@()
    if ($EngineRoot) { $engineCandidates=@($EngineRoot) }
    elseif ($env:UE_ROOT) { $engineCandidates=@($env:UE_ROOT) }
    else {
        foreach ($key in @('HKLM:\SOFTWARE\EpicGames\Unreal Engine\5.8','HKLM:\SOFTWARE\WOW6432Node\EpicGames\Unreal Engine\5.8')) {
            if (Test-Path $key) { $engineCandidates += (Get-ItemProperty $key -ErrorAction SilentlyContinue).InstalledDirectory }
        }
        $registered='HKCU:\Software\Epic Games\Unreal Engine\Builds'
        if (Test-Path $registered) { $engineCandidates += (Get-ItemProperty $registered).PSObject.Properties | Where-Object {$_.Name -notlike 'PS*'} | ForEach-Object {$_.Value} }
        $installed=Join-Path $programData 'Epic/UnrealEngineLauncher/LauncherInstalled.dat'
        if (Test-Path -LiteralPath $installed) { try { $engineCandidates += (Get-Content -Raw -LiteralPath $installed | ConvertFrom-Json).InstallationList | Where-Object {$_.AppName -like 'UE_5.8*'} | ForEach-Object {$_.InstallLocation} } catch {} }
        $manifests=Join-Path $programData 'Epic/EpicGamesLauncher/Data/Manifests'
        if (Test-Path -LiteralPath $manifests) { foreach ($item in (Get-ChildItem -LiteralPath $manifests -Filter '*.item')) { try { $entry=Get-Content -Raw -LiteralPath $item.FullName | ConvertFrom-Json; if ($entry.AppName -like 'UE_5.8*') { $engineCandidates += $entry.InstallLocation } } catch {} } }
        $epic=Join-Path $programFiles 'Epic Games'
        if (Test-Path -LiteralPath $epic) { $engineCandidates += Get-ChildItem -LiteralPath $epic -Directory -Filter 'UE_5.8*' | ForEach-Object {$_.FullName} }
    }
    $engine=@($engineCandidates | Where-Object {$_} | Select-Object -Unique | ForEach-Object {Get-EngineInfo $_}) | Sort-Object {$_.version.PatchVersion} -Descending | Select-Object -First 1
    if ($engine) { $report.engine=$engine }
    elseif ($needsEngine) {
        $launcher=Join-Path $programFilesX86 'Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe'
        $hint='Epic Games Launcher의 Unreal Engine > 라이브러리에서 안정 버전 5.8을 설치하세요. 로그인·약관은 본인이 진행해야 합니다.'
        if (Test-Path -LiteralPath $launcher) { $hint += " 설치된 런처: $launcher" }
        if ($EngineRoot) { $hint += " 지정 경로에서 정상 설치를 찾지 못했습니다: $EngineRoot" }
        Need 'Unreal Engine 5.8' $hint 'https://www.unrealengine.com/download'
    }

    $vswhere=Join-Path $programFilesX86 'Microsoft Visual Studio/Installer/vswhere.exe'
    $vs=$null
    if (Test-Path -LiteralPath $vswhere) {
        try {
            $instances=@((& $vswhere -all -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json) | ConvertFrom-Json)
            foreach ($instance in ($instances | Sort-Object installationVersion -Descending)) {
                if ([version]$instance.installationVersion -lt [version]'17.14') { continue }
                $msvcDir=Join-Path $instance.installationPath 'VC/Tools/MSVC'
                $msvc=Get-ChildItem -LiteralPath $msvcDir -Directory -ErrorAction SilentlyContinue | Where-Object { [version]$_.Name -ge [version]'14.38' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'bin/Hostx64/x64/cl.exe')) } | Sort-Object Name -Descending | Select-Object -First 1
                $devShell=Join-Path $instance.installationPath 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll'
                if ($msvc -and (Test-Path -LiteralPath $devShell)) { $vs=@{path=$instance.installationPath;version=$instance.installationVersion;msvc=$msvc.Name;devShell=$devShell}; break }
            }
        } catch { $vs=$null }
    }
    $report.visualStudio=$vs
    if ($needsBuild -and -not $vs) { Need 'Visual Studio C++ 빌드 도구' "Visual Studio Installer에서 VS2022 17.14 이상 또는 VS2026의 MSVC x64/x86 도구를 준비하세요. Build Tools는 'C++를 사용한 데스크톱 개발', Community/Professional은 'C++를 사용한 게임 개발'을 선택합니다. 설치됨이 비어 있으면 Build Tools를 새로 설치하세요. 설치 관리자: $(Join-Path $programFilesX86 'Microsoft Visual Studio/Installer/vs_installer.exe')" 'https://aka.ms/vs/17/release/vs_buildtools.exe' }
    $sdkRoot=Join-Path $programFilesX86 'Windows Kits/10'
    $sdk=Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'Include') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^10\.0\.\d+\.\d+$' -and [version]$_.Name -ge [version]'10.0.22621' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'um/Windows.h')) -and (Test-Path -LiteralPath (Join-Path $sdkRoot "Lib/$($_.Name)/um/x64/kernel32.lib")) } | Sort-Object Name -Descending | Select-Object -First 1
    if ($sdk) { $report.windowsSdk=$sdk.Name } elseif ($needsBuild) { Need 'Windows SDK 10.0.22621 이상' 'Visual Studio Installer의 개별 구성 요소에서 Windows 11 SDK를 선택하세요.' 'https://developer.microsoft.com/windows/downloads/windows-sdk/' }
    $report.gpu=@(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object Name,DriverVersion,AdapterRAM)
    if ($report.gpu.Count -eq 0) { Need '그래픽 장치/드라이버' 'Windows 장치 관리자에서 그래픽 카드와 제조사 드라이버를 확인하세요. 그래픽 카드 이름만으로 Unreal 실행/인코딩 성공을 판정하지 않습니다.' }
    else { Write-Host ('발견한 그래픽 장치: ' + (($report.gpu | ForEach-Object {$_.Name}) -join ', ')) }

    $pythonCandidates=@()
    $pythonCommand=Find-Executable 'python.exe'
    if ($pythonCommand) { $pythonCandidates += $pythonCommand }
    $py=Find-Executable 'py.exe'
    if ($py) { try { $pythonCandidates += (& $py -3 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -Last 1) } catch {} }
    $pythonDirectory=Join-Path $localApp 'Programs/Python'
    if (Test-Path -LiteralPath $pythonDirectory) { $pythonCandidates += Get-ChildItem -LiteralPath $pythonDirectory -Directory -Filter 'Python3*' | ForEach-Object {Join-Path $_.FullName 'python.exe'} }
    $python=$null
    foreach ($path in ($pythonCandidates | Where-Object {$_} | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        try {
            $probe=(& $path -c "import sys,json,importlib.util; print(json.dumps(dict(version='.'.join(map(str,sys.version_info[:3])),pil=importlib.util.find_spec('PIL') is not None,fontTools=importlib.util.find_spec('fontTools') is not None)))" 2>$null | Select-Object -Last 1) | ConvertFrom-Json
            if ([version]$probe.version -ge [version]'3.10') { $python=@{path=$path;version=$probe.version;pil=$probe.pil;fontTools=$probe.fontTools}; break }
        } catch {}
    }
    $report.python=$python
    if ($needsBuild -and -not $python) { Need 'Python 3.10 이상' 'Windows용 Python을 설치한 뒤 다시 실행하세요. 프로젝트 원화/서사 검사용이며 배포 게임에는 필요하지 않습니다.' 'https://www.python.org/downloads/windows/' }
    elseif ($needsBuild -and (-not $python.pil -or -not $python.fontTools)) { Need 'Pillow / fontTools' ("다음 명령으로 프로젝트 검사 도구를 준비할 수 있습니다(자동 실행하지 않음): & '{0}' -m pip install -r '{1}'" -f $python.path.Replace("'","''"),(Join-Path $PSScriptRoot 'requirements-art.txt').Replace("'","''")) }

    if ($Streaming) {
        $lock=Get-Content -Raw -LiteralPath (Join-Path $repo 'Streaming/PathOfDawnUnreal/versions.lock.json') | ConvertFrom-Json
        $node=Find-Executable 'node.exe' @((Join-Path $programFiles 'nodejs/node.exe'))
        if (-not $node -or ((& $node --version 2>$null | Select-Object -Last 1) -ne $lock.node)) { Need "Node $($lock.node)" '공식 스트리밍 인프라에 맞는 Node 버전을 준비하세요.' 'https://nodejs.org/dist/v22.14.0/' }
        else { $env:PATH=(Split-Path -Parent $node)+';'+$env:PATH }
        $npm=Find-Executable 'npm.cmd' @($(if ($node) { Join-Path (Split-Path -Parent $node) 'npm.cmd' }))
        if (-not $npm -or ((& $npm --version 2>$null | Select-Object -Last 1) -ne $lock.npm)) { Need "npm $($lock.npm)" '고정 Node 배포에 포함된 npm을 사용하세요.' 'https://nodejs.org/dist/v22.14.0/' }
        $git=Find-Executable 'git.exe' @((Join-Path $programFiles 'Git/cmd/git.exe'))
        if (-not $git) { Need 'Git' '공식 Pixel Streaming 인프라를 준비하려면 Git이 필요합니다.' 'https://git-scm.com/download/win' }
        else { $env:PATH=(Split-Path -Parent $git)+';'+$env:PATH }
    }
    if ($report.missing.Count -gt 0) {
        $report.status='missing-prerequisites'
        Write-Host ''; Write-Host '다음 준비가 필요합니다. 설치 후 같은 시작 파일을 다시 실행하면 됩니다.'
        foreach ($entry in $report.missing) { Write-Host ("- {0}: {1}" -f $entry.name,$entry.action); if ($entry.link) { Write-Host "  $($entry.link)" } }
        $code=2
    } elseif ($CheckOnly) { $report.status='prerequisites-detected'; Write-Host '필요한 도구를 찾았습니다. 게임 실행·그래픽·인코더 검증은 아직 하지 않았습니다.'; $code=0 }
    else {
        if ($python) { $env:PATH=(Split-Path -Parent $python.path)+';'+$env:PATH }
        if ($needsBuild) {
            Import-Module -Name $vs.devShell -ErrorAction Stop
            Enter-VsDevShell -VsInstallPath $vs.path -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
            if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'Visual Studio 개발 환경을 활성화하지 못했습니다. Visual Studio Installer의 C++ 구성 요소를 확인하세요.' }
            $env:PATH=(Split-Path -Parent $python.path)+';'+$env:PATH
            $BuildId='local-'+$stamp+'-'+[guid]::NewGuid().ToString('N').Substring(0,4)
            Run-Step 'environment' 'CheckEnvironment.ps1' @('-EngineRoot',$engine.path)
            Run-Step 'editor' 'BuildEditor.ps1' @('-EngineRoot',$engine.path)
            Run-Step 'assets' 'GenerateDemoAssets.ps1' @('-EngineRoot',$engine.path,'-SkipCompile')
            Run-Step 'tests' 'TestDemo.ps1' @('-SourceOnly','-RequireArt','-UnrealAutomation','-EngineRoot',$engine.path)
            Run-Step 'windows-build' 'BuildDemo.ps1' @('-EngineRoot',$engine.path,'-BuildId',$BuildId)
        }
        $report.buildId=$BuildId
        if ($BuildOnly) {
            Write-Host "빌드를 완료했습니다: $BuildId. 기존 실행 세션은 유지합니다. 실제 게임 화면 검증은 아직 수행하지 않았습니다."
        } elseif ($Streaming) {
            Run-Step 'streaming-prepare' 'PrepareStreaming.ps1'
            Write-Host '이 프로젝트가 실행한 기존 게임/스트리밍 프로세스를 종료하고 같은 호스트 저장으로 브라우저 테스트를 시작합니다.'
            Run-Step 'switch-session' 'StopStreaming.ps1' @('-IncludeLocalGame')
            $streamArguments=@('-EngineRoot',$engine.path,'-BuildId',$BuildId)
            if ($TestCandidate) { $streamArguments += '-TestCandidate'; $report.testCandidate=$true; Write-Host '미검증 후보의 첫 브라우저 테스트입니다. 서비스 버전을 승격하지 않습니다.' }
            Run-Step 'streaming-start' 'StartStreaming.ps1' $streamArguments
            Start-Process 'http://127.0.0.1:8080/'
            Write-Host '같은 PC의 브라우저를 열었습니다. 공개 인터넷 주소가 아닙니다. 영상·소리·조작은 직접 확인하세요.'
        } else {
            Run-Step 'local-game' 'RunLocal.ps1' @('-BuildId',$BuildId)
            Write-Host "게임 시작을 요청했습니다. 빌드 이름: $BuildId"
            Write-Host '실제 게임 창에서 타이틀, 이동, 대화, 선택, 회귀를 확인하세요. 실행 요청만으로 플레이 검증이 끝난 것은 아닙니다.'
        }
        $report.status=$(if ($BuildOnly) {'built-not-launched'} else {'launch-requested'}); $code=0
    }
} catch {
    $report.status='stopped'; $report.error=$_.Exception.Message
    Write-Host ''; Write-Host ('진행을 멈췄습니다: ' + $_.Exception.Message)
    $code=1
} finally {
    try {
        New-Item -ItemType Directory -Path (Split-Path -Parent $diagnostic) -Force | Out-Null
        [IO.File]::WriteAllText($diagnostic,($report | ConvertTo-Json -Depth 14),(New-Object System.Text.UTF8Encoding($true)))
        Write-Host "진단 결과: $diagnostic"
    } catch { Write-Host '진단 파일을 저장하지 못했습니다. 소스 ZIP을 쓰기 가능한 일반 폴더에 풀어 주세요.'; $code=1 }
}
exit $code
