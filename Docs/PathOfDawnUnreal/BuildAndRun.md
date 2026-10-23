# Windows 빌드와 실행

사용자는 v7이 Windows PC에서 실행됐다고 보고했다. v8은 시각 구성 변경 후 다시 Editor 컴파일·에셋 생성/재로드·Cook·게임 실행을 확인해야 한다. **현재 v8의 실행 검증과 플레이용 ZIP은 없다.** 이 작업 환경은 Unreal/GPU가 없는 Debian 원격 컨테이너이며, 아래 Windows 명령은 로컬 PC에서 수행할 재개 절차다. Editor/게임 Target의 UE 5.8 `BuildSettingsVersion.V7`은 배포 묶음 이름 v8과 별개다.

## Windows 준비

`PathOfDawn-Source-20261023-v8.zip` 전체를 `C:\game\PathOfDawn-v8` 같은 새 영문 경로에 압축 해제하고 `Start-PathOfDawn.cmd`를 실행한다. 기존 v7 폴더는 보관하고 `Content`/`Intermediate`/`Binaries`는 옮기지 않는다. 생성기는 기존 맵·재질·Blueprint를 보존하므로 새 폴더에서 v8 원본으로 장면을 생성해야 한다. 엔진·Visual Studio 재설치는 필요 없다. PC에서 Codex가 직접 빌드를 진행하려면 [LocalCodex](LocalCodex.md)를 따른다.

Epic Games Launcher에서 안정 UE 5.8을 설치하고 사용자 본인이 로그인·약관 동의를 완료한다. 현재 컨테이너에는 엔진 인증이나 Windows PC 접근 권한이 없다. 정확한 패치·Changelist는 `CheckEnvironment.ps1`가 설치 파일 `Engine/Build/Build.version`에서 기록한다. 설치되지 않은 패치를 고정했다고 주장하지 않는다.

공식 5.8 도구 요구사항은 VS2022 17.14 이상 또는 VS2026 18.0 이상, MSVC 14.38 이상, Windows SDK 10.0.22621 이상이다. VS2026/MSVC14.50/SDK10.0.26100 권장 여부와 실제 설치 호환성은 [공식 Visual Studio 구성 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine) 및 UBT 결과를 우선한다. C++ 게임 개발 워크로드, Python 3, PowerShell 7.2 이상이 필요하다. VS Developer PowerShell에서 실행하면 `cl.exe`가 설정된다. GPU 드라이버와 하드웨어 인코더는 별도 실제 테스트 대상이다.

저장소 루트에서 실행한다. 아래 `$ue`는 설치 위치 예시이며 스크립트에는 엔진 경로가 고정되어 있지 않다.

```powershell
$ue = 'C:\Program Files\Epic Games\UE_5.8'
python -m pip install -r .\Tools\PathOfDawnUnreal\requirements-art.txt
pwsh -File .\Tools\PathOfDawnUnreal\CheckEnvironment.ps1 -EngineRoot $ue
pwsh -File .\Tools\PathOfDawnUnreal\BuildEditor.ps1 -EngineRoot $ue
pwsh -File .\Tools\PathOfDawnUnreal\GenerateDemoAssets.ps1 -EngineRoot $ue -SkipCompile
pwsh -File .\Tools\PathOfDawnUnreal\TestDemo.ps1 -SourceOnly -RequireArt -UnrealAutomation -EngineRoot $ue
pwsh -File .\Tools\PathOfDawnUnreal\BuildDemo.ps1 -EngineRoot $ue -BuildId demo-001
pwsh -File .\Tools\PathOfDawnUnreal\RunLocal.ps1 -BuildId demo-001
```

v8의 새 시각 원본은 `SourceArt/PathOfDawnUnreal/VisualV8/Illustrations`와 `VisualV8/Models`에 있다. 기존 v7 원본과 혼동하지 않는다. 원본 미리보기는 Unreal 캡처가 아니며 아래 재로드와 실제 화면 검사가 필요하다.

`GenerateDemoAssets`는 컴파일된 Editor를 두 번 직렬 실행한다. 첫 실행에서 실제 에셋을 생성하고, 새 Editor 프로세스에서 `-PODVerifyAssets`로 저장 후 참조를 다시 검사한다. 두 JSON 보고서의 `status=passed`가 필요하다. 기존 사용자 편집 에셋은 생성기의 보존 정책을 따른다. 자동 생성 보고서는 그래픽 품질/플레이 성공 증거가 아니다.

v6는 생성/검증마다 고유한 `GenerateDemoAssets-<시각-ID>-editor.log` / `VerifyDemoAssets-<시각-ID>-editor.log`를 Evidence에 남긴다(`-stdout`, `-ABSLOG`). 실패한 `asset-generation-report-<시각-ID>.json`과 Python traceback도 다음 단계로 넘어가기 전에 보존·출력한다. 프로세스 종료 0만으로 성공으로 보지 않으며, 이전 passed 보고서를 새 실행의 성공으로 재사용하지 않는다. 런타임 게임에 Python이 포함되는 변경은 아니다.

`BuildDemo`는 엔진에 존재하는 `Engine/Build/BatchFiles/RunUAT.bat BuildCookRun`을 호출한다. Development가 기본이며 `-Configuration Shipping`을 별도로 실행할 수 있다. `-build -cook -stage -pak -iostore -archive -prereqs`와 `/Game/PathOfDawn/Maps/L_Galilee`를 전달한다. 결과는 `Builds/PathOfDawnUnreal/Windows/<BuildId>/`에 생성하며, 같은 폴더로 재빌드하지 않는다. 로그는 `Docs/PathOfDawnUnreal/Evidence/BuildDemo-<BuildId>.log`다. 프로그램·Cook 데이터가 없으면 실패한다.

## 실제 플레이 검사와 ZIP

실제로 게임을 플레이하며 타이틀→조사→대화→선택→결과→회귀→다른 결과, 종료→재실행→이어하기를 확인한다. `Tools/PathOfDawnUnreal/smoke-report.template.json`을 복사하고 실제 관찰만 기록한다. 후보의 `build-manifest.json`에서 BuildId/SHA256를 옮기고 실제 캡처 6개 이상(타이틀, 호숫가, 대화, 선택, 결과, 회귀)의 경로를 기록한다. 자동으로 성공 값을 채우는 도구는 제공하지 않는다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\TestDemo.ps1 -BuildId demo-001 -RequireArt -SmokeReport 'C:\Evidence\demo-001.json'
pwsh -File .\Tools\PathOfDawnUnreal\PackageDemo.ps1 -BuildId demo-001
```

`PackageDemo`는 필수 폴더 전체를 복사하고 Saved·디버그 심볼·키 파일을 제외한다. ZIP, SHA256 파일, 별도 압축 해제 폴더를 만들며 해제된 게임 데이터 해시를 대조한다. **압축 해제/해시 검사는 실행 검증이 아니다.** 스크립트가 표시한 `Builds/PathOfDawnUnreal/Extracted/<BuildId>/.../PathOfDawnUnreal.exe`를 에디터 없이 직접 실행하여 재검증하고 결과를 Evidence에 기록한다. 다른 깨끗한 PC 실행은 별도 항목이다. 현재는 실제 ZIP 경로가 존재하지 않는다.

## 저장과 종료

`RunLocal`/`StartStreaming`은 `-UserDir=<LOCALAPPDATA>\PathOfDawnUnreal\Host`를 전달한다. 실행 폴더와 분리해 업데이트 시 저장을 유지한다. 실제 SaveGame 위치는 게임 로그 및 생성된 Saved/SaveGames 경로로 확인해야 한다. 직접 더블클릭 실행은 엔진 기본 사용자 저장 위치를 사용할 수 있으므로 스크립트 실행과 섞지 않는다. 브라우저 localStorage는 Unreal 저장소가 아니다.

저장을 초기화하려면 게임을 종료한 뒤 해당 호스트 Saved/SaveGames를 별도 백업하고 원하는 세이브 파일만 이동한다. 게임의 새 게임은 세계 진행을 초기화하며 기억 삭제는 별도 확인 동작이다. 전체 AppData나 다른 Unreal 저장 폴더를 삭제하지 않는다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1 -IncludeLocalGame
```

종료 스크립트는 자신이 기록한 PID·시작 시각·실행 파일 경로를 모두 검사한다. 다른 UnrealEditor/게임/Node 프로세스를 이름으로 일괄 종료하지 않는다.

## 같은 주소로 업데이트

처음에는 다음 명령으로 새 후보를 컴파일·에셋 검사·소스 테스트·Cook한다. 실제 그래픽 증거가 없으면 기존 서비스는 유지한 채 후보 단계에서 멈춘다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\UpdateDemo.ps1 -EngineRoot $ue -BuildId demo-002
# 후보를 실제 테스트한 다음 승격
pwsh -File .\Tools\PathOfDawnUnreal\UpdateDemo.ps1 -EngineRoot $ue -ExistingBuildId demo-002 -SmokeReport 'C:\Evidence\demo-002.json' -StartStreaming
```

실제 GUI 테스트 드라이버를 구축한 호스트에서는 `-SmokeCommand 'C:\Tests\RealGameSmoke.ps1'`를 주면 한 명령으로 빌드부터 검사·교체까지 실행한다. 드라이버는 `-BuildDirectory`와 `-ReportPath`를 받아 실제 게임 검사 결과를 위 스키마로 작성해야 한다. 이 저장소에는 검증되지 않은 GUI 드라이버를 성공하는 것처럼 넣지 않았다. 완전 자동 그래픽 검사는 미완료다.

승격 시 `runtime/current.json`/`previous.json`을 원자적으로 교체한다. 실행 중 폴더를 덮어쓰지 않고 게임/서버만 재시작하며 실패 시 이전 버전을 재시작한다. 호스트 저장은 유지한다. 동일 주소는 `http://127.0.0.1:8080/`이며 **서비스를 성공적으로 실행한 같은 Windows PC에서만** 의미가 있다. 소스 수정, Live Coding 또는 웹 새로고침만으로 패키지가 갱신되지는 않는다.

## 이 환경에서 수행 가능한 검사

```bash
python3 Tools/PathOfDawnUnreal/validate_content.py --root .
g++ -std=c++17 -Wall -Wextra -pedantic -I Games/PathOfDawnUnreal/Source/PathOfDawnUnreal/Core Tools/PathOfDawnUnreal/tests/core_tests.cpp -o /tmp/dawn_core_tests
/tmp/dawn_core_tests
```

Unreal API/UHT/UBT 컴파일, USaveGame 파일 IO, Cook 참조, 한국어 렌더링, 충돌, 성능, 그래픽 캡처는 위 검사로 대체되지 않는다.

v8에서는 가져오기 전에 `validate_visual_sources.py`가 활성 이미지·FBX·표면 텍스처 25개의 파일과 출처 해시를 확인한다. 새 환경 모델이 빠졌거나 구버전 원본이 섞이면 정상 완료로 넘기지 않는다. 새 맵·지면/수면 재질은 v8 revision 메타데이터가 있어야 재로드 검증을 통과한다.
