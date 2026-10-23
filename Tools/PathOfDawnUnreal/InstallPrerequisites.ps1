#requires -Version 5.1
# UTF-8 BOM is required for Korean text in inbox Windows PowerShell 5.1.
[CmdletBinding()]
param([switch]$PlanOnly)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,4)
$logDirectory=Join-Path $repo 'Docs/PathOfDawnUnreal/Evidence'
$log=Join-Path $logDirectory "setup-pc-$stamp.log"
$diagnostic=Join-Path $logDirectory "setup-pc-$stamp.json"
$report=[ordered]@{checkedUtc=[DateTime]::UtcNow.ToString('O');planOnly=[bool]$PlanOnly;status='checking';before=$null;after=$null;steps=@();manualActions=@();error=$null}
$resultCode=1
$transcriptStarted=$false
function Find-Tool([string]$Name,[string[]]$Candidates=@()) {
    $command=Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and ($Name -eq 'pwsh.exe' -or $command.Source -notlike '*\WindowsApps\*')) { return $command.Source }
    foreach ($candidate in $Candidates) { if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate } }
    return $null
}
function Get-SetupState {
    $state=[ordered]@{pwsh=$null;python=$null;visualStudio=$null;existingVisualStudio=$false;sdk=$null;epic=$null;existingEpic=$false}
    $p=Find-Tool 'pwsh.exe' @((Join-Path $script:programFiles 'PowerShell/7/pwsh.exe'))
    if ($p) { try { $v=(& $p -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()' 2>$null | Select-Object -Last 1); if ([version]$v -ge [version]'7.2') { $state.pwsh=@{path=$p;version=$v} } } catch {} }
    $paths=@((Find-Tool 'python.exe'))
    $py=Find-Tool 'py.exe'
    if ($py) { try { $paths+=(& $py -3 -c 'import sys;print(sys.executable)' 2>$null | Select-Object -Last 1) } catch {} }
    foreach ($folder in @((Join-Path $script:localApp 'Programs/Python'),$script:programFiles)) {
        if (Test-Path -LiteralPath $folder) { $paths+=Get-ChildItem -LiteralPath $folder -Directory -Filter 'Python3*' | ForEach-Object {Join-Path $_.FullName 'python.exe'} }
    }
    foreach ($p in ($paths | Where-Object {$_} | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $p)) { continue }
        try {
            $probe=(& $p -c "import sys,json,importlib.util;print(json.dumps(dict(version='.'.join(map(str,sys.version_info[:3])),pil=importlib.util.find_spec('PIL') is not None,fontTools=importlib.util.find_spec('fontTools') is not None)))" 2>$null | Select-Object -Last 1) | ConvertFrom-Json
            if ([version]$probe.version -ge [version]'3.10') { $state.python=@{path=$p;version=$probe.version;pil=$probe.pil;fontTools=$probe.fontTools}; break }
        } catch {}
    }
    $vswhere=Join-Path $script:programFilesX86 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (Test-Path -LiteralPath $vswhere) {
        try {
            $instances=@((& $vswhere -all -products '*' -format json) | ConvertFrom-Json)
            $state.existingVisualStudio=($instances.Count -gt 0)
            foreach ($instance in $instances) {
                if ([version]$instance.installationVersion -lt [version]'17.14') { continue }
                $msvc=Get-ChildItem -LiteralPath (Join-Path $instance.installationPath 'VC/Tools/MSVC') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d+\.\d+\.\d+' -and [version]$_.Name -ge [version]'14.38' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'bin/Hostx64/x64/cl.exe')) } | Select-Object -First 1
                if ($msvc -and (Test-Path -LiteralPath (Join-Path $instance.installationPath 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll'))) { $state.visualStudio=@{path=$instance.installationPath;version=$instance.installationVersion;msvc=$msvc.Name}; break }
            }
        } catch { $state.existingVisualStudio=$true }
    } else {
        foreach ($folder in @((Join-Path $script:programFiles 'Microsoft Visual Studio'),(Join-Path $script:programFilesX86 'Microsoft Visual Studio'))) {
            if (Test-Path -LiteralPath $folder) { if (Get-ChildItem -LiteralPath $folder -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -match '^20\d\d$'}) { $state.existingVisualStudio=$true } }
        }
    }
    $sdkRoot=Join-Path $script:programFilesX86 'Windows Kits/10'
    $sdk=Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'Include') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^10\.0\.\d+\.\d+$' -and [version]$_.Name -ge [version]'10.0.22621' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'um/Windows.h')) -and (Test-Path -LiteralPath (Join-Path $sdkRoot "Lib/$($_.Name)/um/x64/kernel32.lib")) } | Select-Object -First 1
    if ($sdk) { $state.sdk=$sdk.Name }
    foreach ($folder in @($script:programFilesX86,$script:programFiles)) {
        foreach ($arch in @('Win64','Win32')) { $p=Join-Path $folder "Epic Games/Launcher/Portal/Binaries/$arch/EpicGamesLauncher.exe"; if (Test-Path -LiteralPath $p) { $state.epic=$p } }
    }
    foreach ($hive in @('HKLM:\SOFTWARE','HKLM:\SOFTWARE\WOW6432Node','HKCU:\SOFTWARE')) {
        $appPath=Join-Path $hive 'Microsoft/Windows/CurrentVersion/App Paths/EpicGamesLauncher.exe'
        if (Test-Path $appPath) { $p=(Get-ItemProperty $appPath).'(default)'; if ($p -and (Test-Path -LiteralPath $p.Trim('"') -PathType Leaf)) { $state.epic=$p.Trim('"') } }
        $uninstall=Join-Path $hive 'Microsoft/Windows/CurrentVersion/Uninstall'
        if (-not (Test-Path $uninstall)) { continue }
        foreach ($entry in (Get-ChildItem $uninstall -ErrorAction SilentlyContinue | Get-ItemProperty -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -eq 'Epic Games Launcher'})) {
            $state.existingEpic=$true
            if (-not $entry.InstallLocation) { continue }
            foreach ($relative in @('Portal/Binaries/Win64/EpicGamesLauncher.exe','Portal/Binaries/Win32/EpicGamesLauncher.exe','Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe','Launcher/Portal/Binaries/Win32/EpicGamesLauncher.exe')) { $p=Join-Path $entry.InstallLocation $relative; if (Test-Path -LiteralPath $p -PathType Leaf) { $state.epic=$p } }
        }
    }
    return [pscustomobject]$state
}
function Invoke-SetupCommand([string]$Name,[string]$Executable,[string[]]$Arguments) {
    $display='& '+("'"+$Executable.Replace("'","''")+"' ")+(($Arguments | ForEach-Object {"'"+$_.Replace("'","''")+"'"}) -join ' ')
    Write-Host ''; Write-Host "[$Name] $display"
    $step=[ordered]@{name=$Name;executable=$Executable;arguments=$Arguments;command=$display;status='planned';exitCode=$null}
    $script:report.steps+=$step
    if ($script:PlanOnly) { return }
    $step.status='running'
    [void](Get-Command $Executable -CommandType Application -ErrorAction Stop)
    # Native output stays attached to this console: agreement prompts must remain visible.
    # Windows PowerShell must not turn a native stderr warning into a failed install.
    $previousPreference=$ErrorActionPreference
    $global:LASTEXITCODE=$null
    try { $ErrorActionPreference='Continue'; & $Executable @Arguments; $nativeExit=$global:LASTEXITCODE }
    finally { $ErrorActionPreference=$previousPreference }
    if ($null -eq $nativeExit) { $step.status='launch-failed'; throw "$Name 설치 프로그램을 시작하지 못했습니다. 실행 경로와 Windows 권한 안내를 확인하세요." }
    $step.exitCode=$nativeExit
    $hex=('{0:X8}' -f ([int64]$nativeExit -band 4294967295))
    if ($hex -eq '8A150019') {
        $step.status='administrator-required'; $script:resultCode=$nativeExit
        throw '설치에 관리자 권한이 필요합니다. 이 창을 닫고 Setup-PathOfDawn-PC.cmd를 마우스 오른쪽 버튼으로 클릭한 뒤 관리자 권한으로 실행을 선택하세요. Windows 권한 요청 창에서 직접 승인해야 합니다.'
    }
    if ($nativeExit -in @(3010,1641) -or $hex -in @('8A150109','8A15010A','8A15010B')) {
        $step.status='reboot-required'; $script:resultCode=$nativeExit
        throw "설치 도구가 재시작을 요구했습니다(종료 코드 $nativeExit / 0x$hex). 작업을 저장하고 직접 Windows를 재시작한 뒤 이 파일을 다시 실행하세요. 자동 재부팅은 하지 않습니다."
    }
    if ($nativeExit -ne 0) { $step.status='failed'; $script:resultCode=$nativeExit; throw "$Name 설치가 완료되지 않았습니다(종료 코드 $nativeExit / 0x$hex). 위 설치 창의 안내와 로그를 확인한 뒤 다시 실행하세요." }
    $step.status='completed'
}
function Install-Package([string]$Id,[string]$Version,[string[]]$Extra=@()) {
    # These pinned non-VS installers are MSI/WiX or Burn; retain UI but suppress reboot.
    if ($Id -ne 'Microsoft.VisualStudio.2022.BuildTools') { $Extra+=@('--custom','/norestart') }
    Invoke-SetupCommand $Id $script:winget (@('install','--id',$Id,'--version',$Version,'--exact','--source','winget','--interactive')+$Extra)
}
try {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    Start-Transcript -LiteralPath $log -Force | Out-Null; $transcriptStarted=$true
    Write-Host '새벽의 길 — Windows 개발 도구 준비'
    Write-Host '누락된 도구만 설치합니다. 설치 창의 약관·관리자 권한 요청은 직접 확인하세요.'
    Write-Host 'Unreal Engine 설치·로그인·결제·방화벽 변경·재부팅은 자동으로 하지 않습니다.'
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitOperatingSystem) { throw '이 설치 도우미는 64비트 Windows용입니다.' }
    $programFiles=[Environment]::GetFolderPath('ProgramFiles')
    $programFilesX86=[Environment]::GetFolderPath('ProgramFilesX86')
    $localApp=[Environment]::GetFolderPath('LocalApplicationData')
    $wingetCommand=Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $winget='winget.exe'
    if ($wingetCommand) { $winget=$wingetCommand.Source }
    elseif (-not $PlanOnly) { throw 'Windows 앱 설치 관리자가 필요합니다. https://apps.microsoft.com/detail/9nblggh4nns1 에서 설치/업데이트한 뒤 이 파일을 다시 실행하세요.' }
    $state=Get-SetupState; $report.before=$state
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $principal=New-Object Security.Principal.WindowsPrincipal($identity)
        $report.elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } finally { $identity.Dispose() }
    # Machine-scoped installers need elevation; user-only Python setup and PlanOnly do not.
    $machineSetupNeeded=(-not $state.pwsh) -or (-not $state.visualStudio -and -not $state.existingVisualStudio) -or (-not $state.sdk) -or (-not $state.epic -and -not $state.existingEpic)
    if (-not $PlanOnly -and $machineSetupNeeded -and -not $report.elevated) {
        $resultCode=-1978335207
        throw '개발 도구를 PC 전체에 설치하려면 관리자 권한이 필요합니다. 아직 설치를 시작하지 않았습니다. 이 창을 닫고 Setup-PathOfDawn-PC.cmd를 마우스 오른쪽 버튼으로 클릭 → 관리자 권한으로 실행 → Windows 권한 요청에서 예를 선택하세요.'
    }
    if ($PlanOnly) { Write-Host '계획만 표시합니다. 설치 명령은 실행하지 않습니다.' }
    if (-not $state.pwsh) { Install-Package 'Microsoft.PowerShell' '7.6.7.0' @('--scope','machine','--architecture','x64') }
    if (-not $state.python) { Install-Package 'Python.Python.3.12' '3.12.10' @('--scope','user','--architecture','x64') }
    $installVs=(-not $state.visualStudio -and -not $state.existingVisualStudio)
    if ($installVs) {
        Install-Package 'Microsoft.VisualStudio.2022.BuildTools' '17.14.42' @('--override','--wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.Windows11SDK.26100')
    } elseif (-not $state.visualStudio) {
        $report.manualActions+="기존 Visual Studio를 찾았습니다. Visual Studio Installer에서 2022 17.14 이상으로 업데이트하고 C++ 빌드 도구(MSVC14.38 이상)를 추가하세요: $(Join-Path $programFilesX86 'Microsoft Visual Studio/Installer/vs_installer.exe')"
    }
    if (-not $state.sdk -and -not $installVs) { Install-Package 'Microsoft.WindowsSDK.10.0.26100' '10.0.26100.7705' }
    if (-not $state.epic -and -not $state.existingEpic) { Install-Package 'EpicGames.EpicGamesLauncher' '1.3.210.0' }
    elseif (-not $state.epic) { $report.manualActions+='Epic Games Launcher의 설치 기록은 있지만 실행 파일을 찾지 못했습니다. Windows 설정 > 앱 > 설치된 앱에서 Epic Games Launcher를 복구하거나 기존 설치 폴더의 실행 파일을 확인하세요. 같은 패키지를 다시 설치하지 않았습니다.' }
    $checked=$state
    if (-not $PlanOnly) { $checked=Get-SetupState }
    if (-not $checked.python -or -not $checked.python.pil -or -not $checked.python.fontTools) {
        $requirements=Join-Path $PSScriptRoot 'requirements-setup.txt'
        if (-not (Test-Path -LiteralPath $requirements)) { throw "프로젝트 검사 라이브러리 목록이 없습니다: $requirements . 설치 ZIP 전체를 풀어 주세요." }
        $pythonPath=Join-Path $localApp 'Programs/Python/Python312/python.exe'
        if ($checked.python) { $pythonPath=$checked.python.path }
        elseif (-not $PlanOnly) { throw 'Python 설치 후 실행 파일을 찾지 못했습니다. 로그를 확인하고 설치 도우미를 다시 실행하세요.' }
        Invoke-SetupCommand 'Pillow/fontTools' $pythonPath @('-m','pip','install','--user','-r',$requirements)
    }
    if (-not $PlanOnly) {
        $report.after=Get-SetupState
        foreach ($tool in @('pwsh','python','visualStudio','sdk','epic')) { if (-not $report.after.$tool) { $report.manualActions+="설치 후 $tool 도구를 확인하지 못했습니다. 위 로그/설치 관리자의 안내를 확인한 뒤 다시 실행하세요." } }
        if ($report.after.python -and (-not $report.after.python.pil -or -not $report.after.python.fontTools)) { $report.manualActions+='Python에서 Pillow/fontTools를 불러올 수 없습니다. pip 로그를 확인하세요.' }
    }
    Write-Host ''; Write-Host '다음 단계: Epic Games Launcher를 열고 로그인 → Unreal Engine → 라이브러리 → 안정 버전 5.8을 설치하세요.'
    Write-Host '설치가 끝나면 원래 게임 폴더의 Start-PathOfDawn.cmd를 다시 실행하세요.'
    Write-Host '이 도우미는 Unreal 게임 빌드·실행·그래픽 검증을 수행하지 않습니다.'
    foreach ($action in $report.manualActions) { Write-Host ('- '+$action) }
    $report.status=$(if ($PlanOnly) {'planned'} elseif ($report.manualActions.Count) {'manual-action-required'} else {'prerequisites-detected-engine-manual'})
    $resultCode=$(if ($report.manualActions.Count -and -not $PlanOnly) {2} else {0})
} catch {
    $report.status='stopped'; $report.error=$_.Exception.Message
    Write-Host ''; Write-Host ('진행을 멈췄습니다: '+$_.Exception.Message)
} finally {
    $report.exitCode=$resultCode
    try { [IO.File]::WriteAllText($diagnostic,($report | ConvertTo-Json -Depth 12),(New-Object System.Text.UTF8Encoding($true))); Write-Host "진단 결과: $diagnostic"; Write-Host "실행 기록: $log" }
    catch { Write-Host '진단 파일을 저장하지 못했습니다. ZIP을 쓰기 가능한 일반 폴더에 풀어 주세요.'; $resultCode=1 }
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
exit $resultCode
