# 실행 환경 — 2026-10-23 (한국 시간)

## 확인 결과

이 작업은 사용자의 Windows PC가 아니라 **관리형 원격 Debian 13.6 x86_64 컨테이너**에서 수행했다. 작업 저장소는 `/workspace/unreal_yesu`이며 최초 상태는 `work` 브랜치, 커밋 없음, 작업 파일 없음이었다. `/workspace`에서 기존 Unity 프로젝트, `.ink`, 원화·모델·음원을 검색했으나 발견하지 못했다. 기존 파일을 삭제하거나 덮어쓰지 않았다.

| 항목 | 관측 결과 |
|---|---|
| Unreal 설치 위치·정확한 버전 | 설치 없음. PATH 및 `/opt`, `/usr/local`, `/workspace` 제한 탐색에서 Editor, UBT, Build.version, UAT 발견 안 됨 |
| UnrealEditor / UBT / AutomationTool | 실행 불가: 바이너리 없음 |
| Windows / Visual Studio / MSVC / SDK | Linux 호스트, `cl.exe`, .NET, PowerShell 없음. Windows 패키징 불가 |
| GPU / 드라이버 | `/dev/dri`, `/dev/nvidia*`, `nvidia-smi` 없음. GPU 장치가 전달되지 않음 |
| 인코더 실제 시험 | FFmpeg H.264 NVENC 128×128 입력 시험 실패: `Cannot load libcuda.so.1`. 목록에 인코더가 표시되는 것과 작동은 다름 |
| 자원 | cgroup 메모리 16 GiB, CPU 할당 4코어, 시작 시 작업 디스크 약 30 GiB 여유 |
| Node / npm | v24.19.0 / 11.9.0. 스트리밍 의존성의 검증 대상 Node와 별도 |
| Blender | 4.3.2, 실제 CLI 사용 가능 |
| Python / C++ | Python 3.12.14, GCC 14.2.0. 엔진 독립 핵심 로직 테스트에 사용 |
| 후속 검증 도구 | `/tmp/pathofdawn-tools`에 PowerShell 7.4.6 Linux와 Node 22.14.0/npm10.9.2를 받아 구문·소스·시그널링 테스트에 사용. Windows 빌드 도구는 여전히 없음 |
| 이미지 생성 | 세션에 제공된 `image_gen` 도구 사용. 실제 PNG를 SourceArt에 저장 |
| 한국어 글꼴 | 시스템 Noto Sans CJK KR의 정규체 face를 OTF로 분리. SIL OFL 조건·Debian 저작권 문서를 함께 보관 |
| 기존 상용 에셋·음성 | 발견 안 됨. 신규 절차적 모델·직접 합성한 음향·생성 원화 사용 |
| 네트워크 | 환경 상태는 unrestricted/enforced. 기본 셸에서 상속 프록시 연결은 실패했으나 도구의 추가 network 권한을 사용한 요청은 성공. 프록시를 우회하지 않고 공식 웹/GitHub 자료 확인 |

기계 판독 가능한 실제 명령·종료 코드: [environment-probe.json](Evidence/environment-probe.json). 엔진 설치 부재로 M0의 Editor 실행·최소 Windows 패키지는 통과하지 못했다. 후속 소스 작업은 사용자의 “엔진이나 Windows 빌드 환경이 없으면 가능한 소스·콘텐츠·생성 스크립트까지” 지시에 따라 진행했다.

## 엔진 및 도구 선택

[공식 발표](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available)를 확인했다. UE 5.8 정식 출시는 2026-06-23이다. 프로젝트의 대상 계열은 **UE 5.8 정식**이다. **설치된 패치 번호는 없음**: 존재하지 않는 5.8.x 패치를 검증·고정했다고 기록하지 않는다. Windows에서 `CheckEnvironment.ps1 -EngineRoot ...`를 실행하면 설치된 `Engine/Build/Build.version`, 플러그인 파일과 도구를 검사·기록한다. 첫 성공 빌드의 정확한 패치 및 toolchain을 증거와 함께 고정해야 한다. Preview나 소스 main은 의존하지 않는다.

[공식 VS 호환성 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine)의 UE 5.8 표: VS 2022 17.14 이상 또는 VS 2026 18.0 이상, 일반 개발 권장 VS 2026. MSVC 최소 14.38/권장 14.50, Windows SDK 최소 10.0.22621.0/권장 10.0.26100 이상. 실제 설치 엔진의 UBT가 최종 호환성 판정자다. 이 호스트에서 해당 조합을 실행한 것은 아니다.

런타임: Enhanced Input, UMG, CineCamera, LevelSequence, USaveGame, Win64 PixelStreaming2. 에디터 전용: PythonScriptPlugin, EditorScriptingUtilities, SequencerScripting. MetaHuman/Groom/GAS/World Partition/Unity 패키지는 추가하지 않았다. Lumen 설정을 제공하나 GPU 성능 검증은 미수행이다.

## MCP

[공식 UE 5.8 MCP 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor)에서 `ModelContextProtocol`, `AllToolsets`, `ModelContextProtocol.GenerateClientConfig Codex` 및 localhost 서버를 확인했다. MCP는 **Experimental**이며 필수 의존성으로 만들지 않았다. 현재 설치 파일·실행 서버·Codex 연결 도구 목록은 검증할 엔진이 없어 확인 불가다. 기본 `.uproject`에서 활성화하지 않는다.

지원 PC에서 사용하려면 설치된 `.uplugin` 파일을 먼저 확인하고 에디터에서 두 플러그인을 활성화한 뒤 에디터 콘솔로 클라이언트 설정을 생성한다. 기존 Codex TOML은 보존한다. 실제 MCP `initialize`/`tools/list` 응답을 확인한 뒤 사용하며, 하나의 에디터 변경 호출을 직렬화한다. 인터넷 공개 금지. 이 프로젝트는 MCP 없이 Editor Python으로 생성하도록 작성했다.

## 재개에 필요한 사용자 환경

Windows 64비트 GPU PC, 정식 UE 5.8 설치와 Epic 약관 동의, 호환 C++ workload/SDK가 필요하다. 계정 로그인·약관·관리자 설치는 여기서 대신 수행하지 않았다. 엔진 바이너리나 자격 증명을 저장소에 넣지 않는다. 약 30 GiB 컨테이너에 전체 엔진을 다운로드하거나 새 유료 GPU 서버를 만들지 않았다.

빌드·생성 순서는 [BuildAndRun.md](BuildAndRun.md), 스트리밍의 고정 버전 및 차단 조건은 [Streaming.md](Streaming.md)를 따른다.

## 사용자 PC 연결 재확인

2026-10-23 URL 우선 요청 뒤 다시 확인했다. 현재 작업은 동일한 원격 Debian 환경이고, 로컬 앱 터미널 연결과 사용 가능한 GPU 호스트·클라우드 인증 연결이 없다. 사용자는 로컬 PC가 Windows라고 답했다. GPU/Unreal 설치는 아직 확인하지 못했으며 직접 연결도 없다. `Start-PathOfDawn.cmd`와 `StartHere.ps1`은 Windows PC에서 진단·제작을 이어갈 시작 도구이며 이 원격 환경에서 사용자 PC에 실행한 것이 아니다. GPU 임대·유료 계정 생성·외부 포트 변경은 수행하지 않았다.

## 사용자가 보내온 Windows 진단 결과

2026-10-23 08:47:47 UTC에 실행한 StartHere 진단 출력을 사용자가 제공했다. AMD Radeon(TM) Graphics와 NVIDIA GeForce RTX 5080이 감지됐고, PowerShell 7.2+, UE5.8, 지원 Visual Studio C++ 도구, Windows SDK, Python3.10+는 발견되지 않았다. 이 정보는 사용자 제공 로그이며 Codex가 PC에 직접 접속한 결과가 아니다. GPU 드라이버 버전·메모리·디스크·실제 인코딩은 이 출력으로 확인되지 않았다. [PCSetup](PCSetup.md)에 다음 설치 절차를 정리했다.

## 후속 사용자 PC 로그 — 10:25:39 UTC

사용자가 제공한 environment/editor 로그로 UE **5.8.4, CL 58902052**, 설치 경로 `C:\Program Files\Epic Games\UE_5.8`, Visual Studio Build Tools **17.14.37806.7**, MSVC **14.44.35207**, Windows SDK **10.0.26100.0**을 확인했다. Windows 빌드 10.0.26200, 8 physical / 16 logical cores가 보고되었다. NVIDIA RTX 5080 드라이버는 WMI 표기 `32.0.16.1047`이다. WMI AdapterRAM은 32비트 값이므로 실제 VRAM 용량으로 판정하지 않는다.

환경 확인 단계는 성공했고 UBT는 실행되었다. Editor 컴파일 준비 중 프로젝트의 V5 설정이 설치된 UnrealEditor의 공유 빌드 설정과 달라 42.55초 뒤 실패했다. v4에서 두 Target을 V7로 맞췄다. 수정 후 컴파일·Editor 실행·Cook·게임·인코더는 아직 미검증이다. 개인정보를 제외한 기록은 [windows-build-first-attempt.json](Evidence/windows-build-first-attempt.json)에 있다. Codex의 원격 Debian 환경에는 여전히 해당 엔진/GPU나 사용자 PC 연결이 없다.

## 두 번째 사용자 빌드 — 10:36:13 UTC

v4에서 실제 선택된 컴파일러는 MSVC 14.44.35229 (설치 디렉터리 14.44.35207), SDK 10.0.26100.0이다. UBA는 물리 메모리 61.66 GB, 8 physical / 16 logical CPU를 보고했다. V7 설정 오류를 통과했지만 첫 PCH 작업에서 비ASCII 프로젝트 경로가 깨져 C1083로 실패했다. GPU 렌더링·인코딩 시험은 여전히 실행 전이다. 영문 경로에 새로 압축 해제하는 재시도 절차는 [PCSetup](PCSetup.md)에 기록했다.

## 세 번째 사용자 빌드 — 10:52:18 UTC, 전체 로그 수신

사용자가 v4를 영문 `C:\game\PathOfDawn-Source-20261023-v4`에서 실행했다. 전체 editor 로그에서 동일한 MSVC/SDK 선택과 SharedPCH 단계 통과, 여러 프로젝트 C++ 파일 컴파일을 확인했다. 한글 경로 차단은 이 실행에서 재현되지 않았다. 이후 C4458 5건과 C2440 1건으로 빌드가 실패했다. 환경 재설치가 아니라 v5의 소스 수정 대상이며, 별도 C4996 경고 2건도 함께 정리했다. [진단 요약](Evidence/windows-build-third-attempt.json)과 [TestReport](TestReport.md)에 대응 내용을 기록했다. v5의 Windows 재빌드는 아직 실행하지 못했고, 원격 Debian 환경에서 사용자 PC를 직접 조작할 연결도 여전히 없다.

## v5 실제 에셋 생성 — 12:13:22 UTC

사용자 제공 assets 로그와 추가로 붙여 넣은 내부 보고서에서 UE `5.8.4-58902052+++UE5+Release-5.8`가 이미지 7개, FBX 10개, WAV 4개, 폰트 얼굴 1개를 실제 생성한 것을 확인했다. 컴파일된 DawnAssetTools의 복합 폰트 생성 호출도 지나 서사 생성에 도달했다. 이는 StartHere의 에디터 빌드 단계가 통과했음을 뒷받침하지만 개별 성공 빌드 로그를 직접 검토한 것은 아니다.

서사 생성은 `Illustration` SoftObjectProperty에 SoftObjectPath를 대입해 실패했다. Texture2D가 필요하다는 엔진 예외를 근거로 v6에서 수정했다. Win64는 VALID이며 LinuxArm64/VisionOS의 SDK 탐색 경고를 Windows 설치 누락으로 판정하지 않는다. 맵·연출 완료·재로드·Cook·Windows 게임·인코더는 여전히 미검증이다. [실패 근거](Evidence/windows-assets-v5.json).

현재 클라우드 환경 상태는 연결된 Debian 작업 환경이며 PC 터미널 세션은 없고, 프로젝트 목록에도 연결된 Windows 호스트가 없다. 접근 허용 답변만으로 현재 작업이 PC에서 실행되지는 않는다. 공식 Windows 앱의 로컬 Codex로 프로젝트를 여는 재개 방법은 [LocalCodex](LocalCodex.md)에 기록했다. 새 설치·로그인·로컬 연결은 이 세션에서 실행하지 않았다.

## v6 생성 후 검증 실패 — 12:28:48 UTC

사용자가 제공한 `start-here-20261023T122848Z-assets.log`에는 22개 원본 임포트 이후 서사·맵·연출 생성과 동일 프로세스 검증 진입이 기록됐다. `L_Galilee` 월드의 오디오 등록/해제가 보이며, `verify()`의 필수 에셋 로드와 맵 로드 다음인 플레이어 메시 검사에서 중단됐다. 원인은 Unreal Python에 없는 `get_static_mesh()` 호출이다. 별도로 `M_LakeWater`의 Sine 입력 누락과 기본 재질 대체도 확인했다. [사용자 로그 요약](Evidence/windows-assets-v6.json).

GPU 쪽에서는 RTX 5080 CUDA API 초기화와 context 생성에 성공했다. 이는 NVENC 인코딩·픽셀 스트리밍의 영상/음성/입력 검증이 아니다. 시작 시 `LogAutomationTest: Error: Condition failed` 15건과 Engine 초기화 전 PixelStreaming2RTC 오류도 있으나, 프로젝트 자동 테스트가 실행됐다는 근거는 없고 이후 에셋 생성은 계속됐다. 원인을 확인하기 전 해결 또는 무해하다고 단정하지 않는다.

v7은 두 메시 조회를 `get_editor_property('static_mesh')`로 수정하고 Time→Sine 첫 입력 연결과 각 연결 반환값 검사를 추가한다. 새로 만든 Blueprint의 메시·기본 Pawn 설정을 저장하고 성공 여부도 확인한다. 기존 사용자 에셋은 덮어쓰지 않으므로 새 영문 폴더에서 수정된 재질을 생성한다. v7 제공 당시 실제 Unreal 실행·새 프로세스 검증·Cook은 미검증이었다. 이후 실행 사용자 보고는 다음 항목에 구분해 기록한다.

## v7 실행 사용자 보고와 v8 제작

사용자는 v7이 Windows PC에서 실행됐다고 보고했으며 인물·환경이 각진 블록처럼 보이고 타이틀·메뉴·일러스트가 기대한 품질에 못 미친다고 지적했다. 이는 실행 여부와 사용자가 본 외관에 관한 보고이며, 전체 분기·저장 복구·약 5분 플레이 시간·URL 접속을 확인한 기록은 아니다.

v8은 새 원화를 `SourceArt/PathOfDawnUnreal/VisualV8/Illustrations`, 새 모델을 `VisualV8/Models`에 분리하고 기존 원본을 보존한다. 클라우드 작업 환경의 Unreal/Windows/GPU 부재는 달라지지 않았다. v8 컴파일·임포트·재로드·Cook·게임 실행은 아직 수행하지 못했으며 원본 이미지나 Blender 미리보기를 Unreal 화면으로 보고하지 않는다. 이미 v7을 실행한 PC는 엔진 재설치 없이 새 `C:\game\PathOfDawn-v8` 폴더에서 시작한다.
