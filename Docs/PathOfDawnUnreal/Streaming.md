# Unreal Pixel Streaming

GitHub 자동 업데이트 실행기는 [GitHubUpdates](GitHubUpdates.md)를 따른다. 최초 Bootstrap에 `-Streaming`을 붙인 뒤에는 `C:\PathOfDawn\Play-in-Browser.cmd`를 사용한다. Windows 패키지 생성과 첫 loopback 후보 테스트를 연결하며, 누락된 Node/Git은 공식 휴대용 배포본을 검증하여 로컬 도구 폴더에 준비한다. 이 경로도 실제 미디어 검증이나 공개 인터넷 주소를 제공했다고 간주하지 않는다.

**현재 플레이 URL은 없다.** 실제 Unreal 실행 파일·GPU·인코더가 없는 Debian 환경이므로 Unreal 영상·음성·입력은 검증하지 못했다. 작성된 웹페이지는 공식 Pixel Streaming 프런트엔드를 여는 클라이언트이며 HTML 게임이나 동영상 대체물이 아니다. HTTP/WebSocket 단독 테스트를 게임 스트리밍 성공으로 기록하지 않는다.

## 고정한 버전과 확인한 API

`Streaming/PathOfDawnUnreal/versions.lock.json`이 인프라의 기준이다.

| 항목 | 고정/확인 상태 |
| --- | --- |
| 게임 엔진 | 안정 UE 5.8 대상, 설치 패치 미확인 |
| 플러그인 | PixelStreaming2; 설치 파일/작동은 Windows에서 확인 필요 |
| 공식 저장소 | EpicGames/PixelStreamingInfrastructure |
| 브랜치 | UE5.8, 공식 README에서 Current |
| 커밋 | `a5b526b2383110dcd84e6b56580bca8f459e1836` |
| Node | `v22.14.0` (해당 커밋 NODE_VERSION) |
| 시그널링 라이브러리 | `@epicgames-ps/lib-pixelstreamingsignalling-ue5.8` 0.2.0 |
| upstream Wilbur | 3.1.0; 본 프로젝트는 라이브러리와 전용 로컬 래퍼 사용 |
| npm 의존성 | npm 10.9.2, 같은 커밋의 package-lock.json + npm ci |

[고정 커밋](https://github.com/EpicGames/PixelStreamingInfrastructure/commit/a5b526b2383110dcd84e6b56580bca8f459e1836)의 `Signalling/src/SignallingServer.ts`와 `PlayerConnection.ts`를 확인했다. `httpServer`, `streamerWsOptions`, `playerWsOptions`, `maxSubscribers`, `playerKeepaliveTimeout`을 사용한다. CLI의 임의 `--host`를 추측하지 않고 Node HTTP 서버와 WebSocket 옵션에 명시적으로 127.0.0.1을 전달한다.

공식 [Pixel Streaming 2 개요](https://dev.epicgames.com/documentation/en-us/unreal-engine/pixel-streaming-2-overview-in-unreal-engine)와 [실행 옵션](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-pixel-streaming-reference)을 확인했다. `-PixelStreamingURL`, `-RenderOffscreen`, `-ForceRes`, `-ResX/-ResY`, `-AudioMixer`를 사용한다. 설치된 패치에서 성공 여부는 실제 실행 로그와 미디어를 기준으로 판단한다. `NullRHI`는 스트리밍 명령에 없다. 브라우저 콘솔 명령 실행 허용 옵션도 사용하지 않는다.

## Windows 로컬 재개

먼저 [BuildAndRun](BuildAndRun.md)에 따라 Windows 후보를 만들고 실제 그래픽 스모크 보고서를 연결한다. Node 22.14.0, Git을 준비한 다음 저장소 루트에서 실행한다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\PrepareStreaming.ps1
pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1 -IncludeLocalGame
pwsh -File .\Tools\PathOfDawnUnreal\StartStreaming.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -BuildId demo-001 -Resolution 720p -FramesPerSecond 30
```

준비 스크립트는 공식 커밋을 체크아웃하고 npm ci와 실제 존재하는 `build:all:cjs`를 실행한다. 개발자가 편집한 vendor 체크아웃은 덮어쓰지 않는다. 결과 공식 프런트엔드는 `vendor/PixelStreamingInfrastructure/SignallingWebServer/www/player.html`이다. vendor/런타임/로그는 소스 ZIP과 Git에서 제외된다.

시작 스크립트는 그래픽 검증된 빌드의 직접 실행 바이너리와 Node를 실행한다. 부트스트랩 EXE가 분리 프로세스를 만들고 종료하는 문제를 피하도록 실제 Binaries/Win64 EXE를 추적한다. 45초 동안 Unreal streamer 등록을 확인하며, 등록 실패 시 자신이 시작한 프로세스만 정리한다. 등록 성공도 영상 성공은 아니다.

성공한 호스트에서 브라우저로 `http://127.0.0.1:8080/`를 연다. 이 주소는 다른 PC에서 접속할 수 있는 공개 URL이 아니다. 첫 버튼은 iframe을 열고, 공식 플레이어의 별도 시작 클릭으로 영상·오디오·포인터 입력을 활성화한다. 시작 클릭이 게임 선택으로 전달되지 않도록 외부 버튼 이벤트를 소비하고 플레이어를 이후에 만든다.

`-Resolution 720p|1080p`, `-FramesPerSecond 30|60`을 제공한다. 해당 GPU/해상도/품질/프레임 시간/메모리/네트워크를 실제 측정해야 하며 60fps를 보장하지 않는다. 현재 NVENC 실제 호출은 GPU 드라이버 `libcuda.so.1` 부재로 실패했다.

## 한 개의 제어 세션

`server.mjs`의 WebSocket 업그레이드 검사에서 두 번째 플레이어 연결을 거절한다. 추가로 공식 서버 `maxSubscribers=1`을 설정해 구독 단계도 제한한다. 다른 탭에 버튼만 숨기는 구현이 아니다. 두 번째 streamer도 거절한다. 연결이 끊기면 기존 게임 프로세스는 계속 실행되며, 재연결은 같은 게임 상태에 붙는다. 응답이 사라진 탭은 keepalive 15초 이후 정리될 수 있다. 새 탭마다 별도 게임/저장이 생성되지 않는다.

모든 HTTP/WebSocket 리스너는 loopback이다. Host와 브라우저 Origin을 확인하고, 외부 Origin을 거절한다. REST 관리 API, SFU, 원격 콘솔, 에디터, MCP, 임의 파일/프로세스 명령은 노출하지 않는다. HTTP 정적 파일은 공식 플레이어 공개 디렉터리와 지정한 두 래퍼 파일만 허용한다. `/status`는 기대 호스트 빌드 ID·등록 상태·제어 수만 반환한다. 게임 화면의 실제 빌드 ID와 직접 대조해야 한다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1
```

정상 서비스 중에는 시그널링 Node 프로세스와 Unreal 게임 프로세스, GPU 호스트가 계속 켜져 있어야 한다. 절전·종료·재부팅 시 중단된다. 종료는 PID/시작 시각/경로 일치 여부를 검사한다. 게임 종료 전 게임 안에서 저장하고 타이틀로 돌아오는 것이 권장된다.

로컬 실행과 스트리밍 실행은 같은 저장 슬롯을 사용하므로 상호 배제한다. 실행 스크립트가 추적하는 게임이 있으면 다른 게임 실행을 거절한다. 스크립트 밖에서 수동으로 실행한 복사본도 먼저 종료해야 한다. 직접 `StartStreaming`으로 시작한 경우에도 성공한 빌드를 `current.json`에 기록하여 다음 업데이트의 롤백 기준으로 삼는다.

## 검증 범위

`test-server.mjs`는 실제 공식 서버 래퍼를 실행하고 로컬 WebSocket 테스트 피어로 단일 연결, 두 번째 연결 거절, 잘못된 Origin, 재연결, 관리 경로 비공개, 캐시 방지, 상태 구분을 검사한다. 테스트 피어는 렌더링하지 않으며 오디오/영상/게임 입력을 만들지 않는다. 결과는 Evidence의 `streaming-server-tests.log`에 기록한다.

Windows에서 다음을 별도 수행해야 한다: 실제 영상과 물소리, WASD/마우스/E, 대화·선택·회귀, 포커스 이탈 후 입력 복귀, 새로고침·재연결, 두 번째 탭 거절, 호스트 재시작·이어하기, 업데이트 후 같은 주소의 새 게임 빌드 ID, 720p/1080p 30/60 성능. 아직 이 검증은 수행하지 않았다.

## LAN과 외부 공개

현재 래퍼는 localhost 전용이므로 LAN/공개 인터넷 접근을 지원한다고 주장하지 않는다. 공개 단계에는 별도 인증/접근 제한, HTTPS/WSS, 실제 WebRTC ICE 검사, 필요 시 인증된 STUN/TURN과 외부망 테스트가 필요하다. HTTP 터널만으로 미디어 성공을 판단하지 않는다. 방화벽/라우터 변경이나 유료 GPU/TURN 자원을 자동 생성하지 않았다. 이 작업은 현재 권한·Windows GPU 호스트를 확보한 뒤 별도 검토할 확장 지점이다.

저장은 Unreal 호스트의 안정적인 UserDir에 존재한다. 사용자별 세션 저장, 브라우저→PC 저장 이동, 여러 호스트, 무중단 배포는 이번 범위에 없다. 업데이트는 [BuildAndRun](BuildAndRun.md)의 후보→검증→프로세스 교체→동일 주소 재연결 절차를 사용하며 Live Coding/파일 감시 자동 빌드를 사용하지 않는다.

## Windows 첫 테스트 시작 도구

저장소 루트의 `Start-PathOfDawn.cmd`는 설치 상태를 검사한 뒤 준비된 PC에서 제작과 로컬 실행을 잇는다. 첫 로컬 그래픽 실행을 확인한 뒤 다음 명령으로 브라우저 연결을 시험할 수 있다.

```cmd
Start-PathOfDawn.cmd -BuildId <빌드이름> -Streaming -TestCandidate
```

`-TestCandidate`는 실행하려는 패키지의 해시를 검증하되, 첫 관찰을 위해 기존 smoke-report.json 없이 loopback에서 실행하는 옵션이다. 검증 완료로 표시하지 않으며 `runtime/current.json`의 정상 서비스 버전을 변경하지 않는다. 기본 StartStreaming과 UpdateDemo의 검증된 버전 교체 조건은 유지한다. 시작 도구는 프로젝트가 기록한 소유 프로세스만 정리하고 기존 호스트 저장을 유지한다. 브라우저가 열려도 실제 영상·음성·입력은 직접 검사해야 한다. 이 명령의 Windows 실제 실행은 아직 미검증이다.


## 2026-10-24 KST 첫 Windows 스트리밍 시작 기록

사용자 로그에서 `efd9d2c361a7`의 Editor, 에셋 생성/검증, tests, Windows 패키징과 streaming-prepare가 완료됐다. 빌드 ID는 `local-20261023T161912Z-d6bd`이며 Unreal의 `DefaultStreamer`가 localhost WebSocket에 연결했다. 아직 브라우저 영상·음성·입력 검증은 아니다.

`-RenderOffscreen` 모드이므로 Unreal 로그 창에 게임 화면이 나오지 않는 것은 그 자체로 렌더링 실패를 뜻하지 않는다. 호스트를 켜둔 채 Chrome/Edge 한 탭에서 http://127.0.0.1:8080/ → **플레이 화면 열기** → 영상 시작 버튼을 누른다. 게임/시그널링을 종료하면 브라우저로 접속할 수 없다.

자동 브라우저 열기를 막을 수 있는 부모 출력 파이프 상속을 실제 자식 프로세스로 재현했다. Windows에서는 지속 실행 프로세스의 stdout/stderr를 `runtime/logs/<역할>-<고유ID>.stdout.log` / `.stderr.log` 파일로 보내도록 변경했다. 기록된 프로세스의 PID·시작 식별자·실행 경로 검사와 종료 규칙은 유지한다. 인자 전달 검사는 통과했고 Windows의 실제 분리 실행/늦은 로그 보존 검사는 TestDemo에 추가했지만 이 Linux 환경에서는 실행하지 않았다.

## 후속 수정: Windows 핸들 상속 제한

위 첫 수정(`b8b392c2ec60`)은 사용자 PC의 실행기 검사에서 실패했다. `Start-Process`는 stdout/stderr를 파일로 바꿔도 다른 상속 가능한 부모 파이프까지 자식에게 넘긴다. 현재 `WindowsProcessLauncher.cs`는 `CreateProcessW`의 `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`에 NUL 입력과 두 로그 파일만 지정한다. PowerShell에 포함된 C# 컴파일 기능을 사용하며 별도 설치·관리자 권한·방화벽 변경이 필요하지 않다. 실행 경로·PID·시작 식별자 확인은 유지한다.

[Windows CI 실행 39991292356](https://github.com/ka8877/unreal_yesu/actions/runs/39991292356)에서 PowerShell 7.6.7과 Windows PowerShell 5.1 부모 프로세스 모두 통과했다. 실제 Run-Step 반환, 다음 단계 도달, 자식 생존, 부모 종료 후 로그 기록, 불필요한 파이프 비상속을 확인했다. 사용자 GPU PC에서의 재시도와 Unreal 영상·음성·입력은 별도 미검증이다.

기존 설치에서 `& 'C:\PathOfDawn\Play-in-Browser.cmd'`를 실행하면 main의 수정본을 자동으로 가져온다. 새 소스 버전은 별도 폴더에서 빌드하며 기존 저장·패키지는 보존한다. 브라우저가 자동으로 열리지 않으면 실행 세션을 유지한 채 `http://127.0.0.1:8080/`를 연다.
