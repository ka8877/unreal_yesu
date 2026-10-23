# 새벽의 길: 갈릴리의 첫 아침

수동 ZIP 대신 GitHub에서 자동 갱신하려면 [GitHubUpdates.md](GitHubUpdates.md)와 저장소 [첫 실행 안내](../../README.md)를 따른다. 한 번 준비한 뒤 `C:\PathOfDawn\Play-in-Browser.cmd`로 최신 소스를 받아 로컬 Windows 빌드와 브라우저 후보 테스트를 시작할 수 있다. 공개 인터넷용 게임 주소와 현재 버전의 Windows 실행 검증은 아직 없다.

**v7은 사용자 Windows PC에서 실행됐다는 보고를 받았다. 현재 v8 제공물은 시각 요소를 개편한 프로젝트 소스와 제작 원본이며, v8 실행 파일·플레이 ZIP·게임 URL은 아직 제공하지 않는다.** 이 클라우드 Linux 환경에서는 Unreal 컴파일·가져오기·게임 실행을 수행할 수 없다. [환경](Environment.md)과 [검증 범위](TestReport.md)를 참고한다.

사용자는 v7 인물·환경의 각진 형태와 화면 구성이 기대한 품질에 못 미친다고 지적했다. v8은 타이틀·메뉴·대화·결과 화면, 일러스트 7종, 예수님을 포함한 인물의 얼굴·복식 형상, 호숫가 지형·소품 배치에 집중한다. 새 원본은 `SourceArt/PathOfDawnUnreal/VisualV8/Illustrations`와 `VisualV8/Models`에 분리해 기존 v7 원본을 보존한다. 인물은 여전히 정적 메시이며 골격 보행·표정 애니메이션은 없다. 원본 이미지나 Blender 미리보기는 Unreal 게임 캡처가 아니다.

## 이번 v8을 빠르게 확인하기

1. `PathOfDawn-Source-20261023-v8.zip`을 `C:\game\PathOfDawn-v8`처럼 **새 영문 폴더**에 압축 해제한다.
2. 기존 v7 폴더는 그대로 둔다. v7 `Content`, `Binaries`, `Intermediate`, `Saved`를 새 폴더에 복사하지 않는다. 이번에는 맵·재질도 달라져 옛 Content가 있으면 보호 검사에서 중단한다.
3. 새 폴더의 `Start-PathOfDawn.cmd`를 실행한다. 이미 준비한 Unreal/Visual Studio를 다시 설치할 필요는 없다. Blender도 필요하지 않으며 생성된 FBX와 PNG가 들어 있다.

[타이틀 구성 참고](Evidence/UI-V8/title-layout-preview.png), [새 인물 원본](../../SourceArt/PathOfDawnUnreal/VisualV8/Models/CharacterPreview_Trio.png), [환경 원본](../../SourceArt/PathOfDawnUnreal/VisualV8/Models/EnvironmentPreview.png)을 먼저 볼 수 있다. **모두 제작 미리보기이며 Unreal 실행 캡처가 아니다.** 현재 v8은 새 실행 파일을 동봉한 플레이 ZIP이 아니라 로컬 제작·실행 도구를 포함한 소스 ZIP이다.

## 구현된 소스와 원본

- 싱글플레이 3인칭 이동·조사, 한국어 UMG 타이틀/설정/크레딧/기록/대화/선택/결과 화면.
- 누가복음 5:1–11 기반 한국어 34노드. 그물·배·돌 조사, 예수님·시몬의 창작 대화, 선택 2회, 결말 3종.
- 첫 선택 뒤 그물/물가 직접 행동, 사건 뒤 시몬에게 돌아가기, 마을 입구까지 걷고 떠나는 결과 확정. 약 5분은 실제 측정 전의 목표다.
- CP01·CP02 값 복사, 밧줄/관계/그물/조사/Transform 복원, MetaProgress 유지, 새 게임과 기억 초기화 분리.
- 같은 C++ 코어의 자동 테스트 및 USaveGame 저장·검증·백업·손상 복구 어댑터.
- 기존 원화·모델·음향·한국어 폰트 원본과 라이선스 보존. v8 시각 원본은 별도 `VisualV8` 폴더에 구성하며 상세 출처와 한계는 [AssetManifest](AssetManifest.md)에 기록한다.
- 실제 Editor API로 DataAsset·Blueprint·폰트·맵·Sequencer를 만드는 생성기, Windows 빌드/패키징·스트리밍 운영 스크립트.

성경의 사건을 바탕으로 구성한 창작 서사입니다. 여행자의 존재, 선택과 시간 회귀는 허구입니다. 대사·선택을 신앙 점수나 구원의 우열로 평가하지 않습니다.

## Windows PC에서 처음 시작하기

**현재 수정본은 `PathOfDawn-Source-20261023-v8.zip`이다.** 전체를 `C:\game\PathOfDawn-v8` 같은 새 영문 폴더에 압축 해제하고 `Start-PathOfDawn.cmd`를 실행한다. 기존 폴더와 사용자 작업은 보존하고 이전 `Intermediate`/`Binaries`는 옮기지 않는다. 엔진·Visual Studio 재설치는 필요 없다.

v8은 **새 폴더에서 시작해야 한다.** 기존 v7의 `Content`/`Intermediate`/`Binaries`를 복사하지 않는다. 생성기는 사용자가 편집했을 수 있는 맵·재질·Blueprint를 보존하므로 기존 폴더에서 코드를 바꾸는 것만으로 새 장면이 반영되지는 않는다. v7 폴더는 보관하고 [재시도 절차](PCSetup.md)를 따른다. v8의 Unreal 컴파일·가져오기·게임 내 외관은 아직 미검증이다.

**PC에서 Codex가 직접 수정·재빌드하게 하려면:** [Windows 로컬 Codex로 이어가기](LocalCodex.md)에 따라 새 로컬 프로젝트 작업을 시작한다. 현재 클라우드 대화에는 PC 연결이 없으며 접근 허용 메시지만으로 연결되지 않는다. 안내에는 현재까지의 상태와 그대로 붙여 넣을 이어가기 요청이 포함되어 있다.

시작 도구가 개발 도구를 찾지 못했다면 [Windows PC 설치 도우미 안내](PCSetup.md)를 먼저 따른다. 새 설치 도우미 ZIP은 기존 프로젝트와 별도 폴더에 압축 해제해 사용할 수 있다.

소스 ZIP을 내려받아 전체를 압축 해제한 뒤 루트의 **Start-PathOfDawn.cmd**를 더블클릭한다. 이 파일 자체가 완성된 게임은 아니다. PC의 엔진·개발 도구·그래픽 장치를 먼저 진단하고, 준비된 경우 Editor 컴파일→실제 에셋 생성/재로드→소스 검사→Windows 패키징→로컬 게임 실행을 이어서 수행한다. 준비가 안 됐으면 필요한 설치 항목과 공식 주소를 보여 주고 멈춘다. 엔진 계정 로그인·약관 동의는 사용자가 직접 진행한다.

현재 Codex 작업 공간은 사용자 PC와 별개인 원격 Linux다. 사용자 PC에 실행 명령을 전달할 연결은 없으므로 **압축 해제와 첫 더블클릭은 사용자 PC에서 해야 한다.** 처음 실행한 진단 파일은 `Docs/PathOfDawnUnreal/Evidence/start-here-*.json`에 남는다. 오류가 나면 창의 마지막 안내를 확인한다. 자동 진단은 GPU의 실제 Unreal 렌더링/인코딩 성공을 보장하지 않는다.

설치 확인만 하려면 PowerShell에서 `powershell -NoProfile -File .\Tools\PathOfDawnUnreal\StartHere.ps1 -CheckOnly`를 실행한다. 사용자는 v7 실행을 보고했으며, v8 빌드·가져오기·게임 실행은 별도로 확인해야 한다.

로컬 게임 창을 확인한 뒤, 명령창에서 `Start-PathOfDawn.cmd -BuildId <표시된빌드이름> -Streaming -TestCandidate`로 첫 브라우저 테스트를 시작할 수 있다. 필요한 Node/Git이 없으면 설치 안내를 출력한다. 이 모드는 localhost의 미검증 후보 실행이며 정상 서비스 버전으로 승격하거나 검사 완료로 기록하지 않는다. 종료는 `pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1`을 사용한다.

브라우저 테스트는 로컬 게임 실행이 성공한 다음 Pixel Streaming으로 연결한다. `localhost`는 그 PC 안에서만 접속하는 주소이며, 다른 사람과 공유할 인터넷 주소는 GPU PC 연결과 네트워크 검증 뒤에 별도로 배포해야 한다. 현재 공개 게임 URL은 없다.

## Windows에서 제작 재개

소스 폴더 전체를 Windows로 옮긴다. 정식 UE 5.8, 호환 Visual Studio C++/Windows SDK, PowerShell 7.2+, Python 3를 준비한다. 아래는 **이 Linux 환경에서 성공한 Windows 명령이 아니라 재개 명령**이다. 첫 Editor 컴파일에서 발견되는 API 차이는 수정 후 재검증해야 한다.

PowerShell에서 저장소 루트로 이동한 뒤:

```powershell
$ue = 'C:\Program Files\Epic Games\UE_5.8'
python -m pip install -r .\Tools\PathOfDawnUnreal\requirements-art.txt
pwsh -File .\Tools\PathOfDawnUnreal\CheckEnvironment.ps1 -EngineRoot $ue
pwsh -File .\Tools\PathOfDawnUnreal\BuildEditor.ps1 -EngineRoot $ue
pwsh -File .\Tools\PathOfDawnUnreal\GenerateDemoAssets.ps1 -EngineRoot $ue -SkipCompile
# cl.exe를 사용할 수 있는 VS Developer PowerShell에서:
pwsh -File .\Tools\PathOfDawnUnreal\TestDemo.ps1 -SourceOnly -RequireArt
pwsh -File .\Tools\PathOfDawnUnreal\BuildDemo.ps1 -EngineRoot $ue -BuildId first-demo
pwsh -File .\Tools\PathOfDawnUnreal\RunLocal.ps1 -BuildId first-demo
```

`GenerateDemoAssets`는 새 에디터 프로세스로 저장 결과를 다시 연다. 실패하면 `Docs/PathOfDawnUnreal/Evidence` 로그를 보고 중단 지점부터 수정한다. 가짜 `.uasset`/`.umap`은 포함하지 않았다. 첫 맵은 이 단계에서 실제로 생성된다. 로컬 조작은 WASD·마우스·E, 대화 Enter/1/2, 메뉴 Esc다.

실제 플레이로 타이틀→탐색→세 결과→회귀→종료/이어하기를 확인하고 최소 여섯 화면을 캡처한다. [BuildAndRun.md](BuildAndRun.md)의 스모크 기록을 작성한 뒤 `TestDemo`와 `PackageDemo`를 실행한다. 압축을 푼 사본도 에디터 없이 실행해야 한다. 최종 플레이용 ZIP의 예정 형식은 `Builds/PathOfDawnUnreal/PathOfDawn-Demo-Windows-<BuildId>.zip`이며 현재 그 파일은 없다.

## 스트리밍과 업데이트

Windows 로컬 실행 성공 후 [Streaming.md](Streaming.md)를 따른다. 현재는 연결 서버 소스의 제한된 테스트만 가능하고 실제 Unreal 영상·음성·입력은 미검증이다. 구성 기본값은 한 호스트·한 활성 사용자·localhost다. `127.0.0.1`을 공유 URL로 안내하지 않는다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\PrepareStreaming.ps1
pwsh -File .\Tools\PathOfDawnUnreal\StartStreaming.ps1 -EngineRoot $ue -BuildId first-demo
pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1
```

새 버전 제작은 `UpdateDemo.ps1 -EngineRoot $ue -BuildId <새ID>`로 시작한다. 그래픽 검증 전에는 기존 서비스가 유지된다. 실제 검사 후 `-ExistingBuildId <새ID> -SmokeReport <해당빌드검사.json> -StartStreaming`으로 동일 localhost 주소의 활성 버전을 전환한다. 자동 그래픽 검사 드라이버를 마련하면 `-SmokeCommand`로 한 명령에 연결할 수 있으며, 현재는 가짜 통과 드라이버를 제공하지 않는다. 프로세스는 공식 시그널링 Node 서버와 패키지 게임이 계속 켜져 있어야 한다. 절전·종료 시 접속이 끊긴다.

## 안내 문서

[Architecture](Architecture.md) · [Narrative](Narrative.md) · [ArtDirection](ArtDirection.md) · [AssetManifest](AssetManifest.md) · [BuildAndRun](BuildAndRun.md) · [Streaming](Streaming.md) · [TestReport](TestReport.md) · [KnownIssues](KnownIssues.md)
