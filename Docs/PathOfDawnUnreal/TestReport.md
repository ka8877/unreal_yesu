# 검증 보고 — 2026-10-23

**v7은 사용자 PC에서 실행됐다는 보고를 받았다. v8의 Unreal 컴파일·가져오기·게임 실행·브라우저 플레이는 아직 미검증이다.** 사용자는 v7의 인물·환경·화면 구성 품질을 문제로 지적했다. 현재 클라우드에는 엔진/Windows 빌드 환경/GPU가 없으며 아래 기존 소스 검사와 사용자 실행 보고, v8 신규 검증을 구분한다.

## v8 이번 변경의 검증

- 실제 `TestDemo.ps1 -SourceOnly -RequireArt`를 PowerShell 7.4.6/Linux에서 실행: C++ 코어 479개, 콘텐츠 8경로·오류 주입 20개, 에셋 보호 7개, 대화 변환 6개, 에디터 검증/재질 연결 계약 13개 통과.
- 활성 일러스트 7개·FBX 15개·표면 텍스처 3개의 실제 파일, PNG 해독, 중복 해시, 출처 목록 해시 일치 통과: [visual-source-validation-v8.json](Evidence/visual-source-validation-v8.json).
- 기존 v7 제작 원본 27개 보존: [v8-source-preservation.json](Evidence/v8-source-preservation.json).
- 캐릭터 FBX 3개 단일 메시·스무딩·높이 재수입 검사: [캐릭터 검사](Evidence/visual-v8-characters-roundtrip.json). 환경 12개와 지면 UV0 재수입 검사: [환경 검사](../../SourceArt/PathOfDawnUnreal/VisualV8/Models/environment-validation.json).
- 새 원화 7장을 실제 생성·시각 검사. [IllustrationManifestV8.json](IllustrationManifestV8.json)에 원본 해상도와 한계를 기록. 타이틀 1920×1080 목표 미달 경고는 유지한다.
- UMG에 사용한 새 문구를 포함하여 한글 446종 모두 실제 OTF에 존재. PowerShell 19개 parser 검사 통과. UMG API는 UE 5.8 공식 문서와 교차 검토했지만 컴파일 검사 대체는 아니다.
- 레벨 구도 렌더에서 시작 화면의 빈 공간·외곽 지면 단절을 찾아 나무/소품과 배경 지면을 추가했다. FBX 최소 높이를 기준으로 배·그물·인물의 지면 높이도 보정했다: [높이 검수](Evidence/v8-grounding-review.json). 이 검사는 실제 Unreal 충돌 검증이 아니다.
- 오래된 맵/재질이 새 v8 검증으로 통과하지 않도록 revision 검사와 계약 테스트를 추가했다. 수면 노멀/지면 색 연결 실패 시 저장을 막는 검사도 통과했다.

[portable-checks-v8.json](Evidence/portable-checks-v8.json)과 개별 로그에 실제 출력이 있다. **v8 Unreal C++ 컴파일, 실제 에셋 저장/재로드, 셰이더, Cook, Windows 실행, 작은 창 UI, 충돌, 프레임 성능, Pixel Streaming은 이 환경에서 실행하지 않았다.** Blender 렌더와 정적 UI 미리보기는 게임 캡처가 아니다.

## 기존 검사 기록과 최신 로그

| 검사 | 결과 | 증거와 한계 |
|---|---|---|
| 동일 런타임 C++ 코어, GCC 14.2 C++17, 경고 오류 처리 | 479 assertions 통과 | [core-tests.log](Evidence/core-tests.log). UE 어댑터 컴파일은 아님 |
| ASan / UBSan | 통과 | [core-tests-asan.log](Evidence/core-tests-asan.log), 같은 479개. LeakSanitizer는 ptrace 제약으로 자체 실패하여 제외 |
| 분기와 상태 | 네 조합/세 결과, 중복 선택, CP01/CP02, Transform, 이전 분기 제거, Meta, stale callback 통과 | 위 C++ 테스트. 기억 초기화 중 도입 타이머 유효성, 네 Task의 우회·연타 차단, 마을 도착 전 결과 미기록, 작업 중 저장·회귀 포함 |
| 저장 형식 | 바이트 파일→새 Session 왕복, 손상·버전·불가능한 상태 거부 통과 | USaveGame 디스크/프로세스 재시작 테스트는 별도 미수행 |
| 한국어 서사 | 34노드, 39키, 진입 2종×분기 4종=8경로, 오류 주입 20개 통과 | [content-validation.json](Evidence/content-validation.json). 단어/문자 수로 실제 플레이 시간을 확정하지 않음 |
| 실제 원화 7장 | 파일 decode·ID 경로·육안 검사 통과 | [IllustrationManifest.json](IllustrationManifest.json). 원화이며 게임 캡처 아님. 가로 해상도 목표 미달 경고 |
| 실제 한국어 폰트 | 현재 v8 한글 446종 cmap에 존재 | [font-validation.json](Evidence/font-validation.json). UMG 글리프/줄바꿈 렌더링은 미검증 |
| Blender FBX | 기존 v7 10개 재임포트·크기 확인 통과 | [blender-fbx-validation.json](Evidence/blender-fbx-validation.json). Unreal collision/mesh import는 미검증 |
| 음향 PCM | 4개 정상 포맷·무클리핑 | [audio-validation.json](Evidence/audio-validation.json). 게임 오디오 출력은 미검증 |
| 원본 보존 | 17개 기존 모델·음향 파일 해시 보존, 새 폴더 오디오 재현 통과 | [source-preservation-validation.json](Evidence/source-preservation-validation.json) |
| 변경 에셋 보호 | 7개 실제 임시 파일 테스트 통과 | [source-refresh-guard-tests.log](Evidence/source-refresh-guard-tests.log). 원본만 변경/사용자 패키지 편집/둘 다 변경/기준 없음/원자적 index 보존. Unreal reimport 자체는 미검증 |
| PowerShell | 7.4.6 parser 검사 및 실제 source test 스크립트 실행 통과 | [powershell-parse-v2.log](Evidence/powershell-parse-v2.log), 총 14개 파일, 현재 코어·콘텐츠 개별 로그 (v2 SourceOnly 재실행 성공). Windows 전용 명령 실행은 아님 |
| 빌드 스크립트 유틸리티 | 경로 공백·해시·잘못된 증거 거부·소유 프로세스 정리 등 14개 통과 | [tooling-tests.log](Evidence/tooling-tests.log) |
| 공식 Pixel Streaming 인프라 빌드 | 고정 UE5.8 커밋·Node22.14/npm10.9.2 설치 및 빌드 성공 | [streaming-npm-ci.log](Evidence/streaming-npm-ci.log), [streaming-build.log](Evidence/streaming-build.log) |
| 시그널링 연결 제한 | HTTP/WebSocket 실제 로컬 서버 검사 9개 통과 | [streaming-server-tests.log](Evidence/streaming-server-tests.log). 두 번째 player/streamer 차단·Origin·재연결·비공개 경로. 프로토콜 테스트 피어이며 Unreal 미디어는 없음 |

코어 실행 명령:

```bash
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -I Games/PathOfDawnUnreal/Source/PathOfDawnUnreal/Core Tools/PathOfDawnUnreal/tests/core_tests.cpp -o /tmp/dawn_core_tests
/tmp/dawn_core_tests
python3 Tools/PathOfDawnUnreal/validate_content.py --root . --require-art --self-test --report Docs/PathOfDawnUnreal/Evidence/content-validation.json
python3 Tools/PathOfDawnUnreal/validate_font.py
```

ASan/UBSan 명령은 위 컴파일에 `-fsanitize=address,undefined -fno-omit-frame-pointer`를 추가하고 `ASAN_OPTIONS=detect_leaks=0`으로 실행했다. 최초 LeakSanitizer 종료 코드 1은 ptrace 환경 제한이었으며, 누수 검증 통과로 바꾸어 기록하지 않는다.

## 실패·차단·미실행

- NVENC 실제 인코딩: 실패. `Cannot load libcuda.so.1`. [environment-probe.json](Evidence/environment-probe.json)에 명령·종료 코드 보관.
- v7 실행은 사용자 보고로 기록한다. v8의 Editor 생성/재로드·Cook·Windows 실행은 아직 미검증이며, 이 클라우드 환경에서 직접 실행한 것은 아니다.
- Unreal Automation 2개는 작성만 했다: `PathOfDawn.Core.BranchesAndRewind`, `PathOfDawn.SaveGame.MemoryRoundtrip`. 실행한 테스트 수에 포함하지 않는다.
- v8 신규 원화·모델의 실제 Unreal 가져오기, 새 맵·재질·Blueprint 참조 재로드, UMG 표시·Cook 포함은 별도로 확인해야 한다. v5/v6의 부분 생성 로그와 v7 실행 보고를 v8의 성공 근거로 사용하지 않는다.
- 타이틀→새게임→이동→조사→대화→선택→결과→회귀, 종료/재실행 이어하기, 설정, 도입 건너뛰기·연타 전체 경로는 아직 검증 결과가 없다. v7 실행 보고만으로 통과 처리하지 않는다.
- v8 Development/Shipping Windows 패키지, 플레이 ZIP, 압축 해제 실행, 깨끗한 다른 PC 실행: 미검증.
- Pixel Streaming 영상·음성·입력·회귀·재연결·호스트 재시작·빌드 교체: 미실행. localhost/LAN/인터넷 어디에도 검증된 게임 URL이 없다.
- 그래픽 품질, 최초 플레이 시간 약 5분, 로컬1080p60·스트리밍720p/1080p30/60, 프레임 시간·GPU 메모리: 미측정.

## 증거의 구분

`Blender_ModelPreview.png`는 **Blender 원본 모델 미리보기**다. `SourceArt/.../IL_*.png`는 **생성 원화**다. 실제 게임 캡처는 0장이다. 시그널링 HTTP 200, 소스 테스트, NullRHI 테스트를 실행 화면 또는 성능 증거로 사용하지 않는다. 사용자 제공 Windows 실패 로그의 개인정보 제외 요약은 `Evidence/windows-build-first-attempt.json`이다. `streaming-build.log`는 Node 인프라 빌드 로그다.

실행 가능한 Windows 호스트에서는 [BuildAndRun](BuildAndRun.md)에 따라 재개하고 실제 캡처와 정확한 빌드 해시가 있는 smoke report를 추가한다. [KnownIssues](KnownIssues.md)의 미완료 항목을 해소한 뒤에만 플레이 데모 완료로 표시한다.

Windows 시작 도구의 CMD ASCII / StartHere.ps1 UTF-8 BOM과 PowerShell 파서 검사도 통과했다. Windows 레지스트리·VS 개발 셸 활성화·설치 탐색·자동 빌드·브라우저 실행은 이 Linux 검사에 포함되지 않는다.

## Windows 개발 도구 설치 도우미 후속 검사

사용자 제공 Windows 진단에서 시작 도구의 진단 단계 실행과 RTX5080 감지를 확인했다. 설치·빌드·게임 실행 성공을 의미하지 않는다. 새 InstallPrerequisites 도우미의 공식 패키지 ID/버전/인수는 [조회 기록](Evidence/setup-official-sources.json)으로 확인했다. 현재 PowerShell 파일 16개 파서 검사 통과([setup-parser.log](Evidence/setup-parser.log)), 실제 공용 호출 함수에 Linux child process를 연결한 경고 출력 후 성공·오류 선호도 복원·실패 코드 37 보존·PlanOnly 미실행 검사 4개 통과([setup-helper-tests.log](Evidence/setup-helper-tests.log)). 재현 명령은 `pwsh -File Tools/PathOfDawnUnreal/tests/setup_native_tests.ps1`이다. Windows 네이티브 설치, UAC, winget 약관 UI, 실제 재부팅 필요 종료는 미검증이다.

## UE 5.8.4 첫 사용자 빌드와 v4 수정

사용자 제공 UTF-16 로그를 해독했다. Build.bat → bundled .NET 10.0 → UBT 진입은 성공했고, Editor 공유 빌드 설정 불일치로 실패했다. `Common.ps1:54`는 실패를 전달하는 위치이며 원인은 Game/Editor Target의 V5 기본 설정이다. 로그가 지시한 V7을 두 Target에 적용했다. 설치 엔진을 재설치하거나 공유 환경 검사를 강제 우회하지 않는다.

StartHere는 자식 PowerShell stderr 첫 줄에서 조기 중단되지 않도록 종료 코드와 전체 로그를 보존하고 실패 로그 마지막 24줄을 화면에 표시한다. 실제 Run-Step 함수를 자식 pwsh에 연결한 6개 검사(성공+stderr, 공백/한국어 인수, 호출자 선호도, 실패 코드 37, 전체 실패 로그, 없는 스크립트 거부)가 Linux PowerShell 7.4.6에서 통과했다. 증거: [start-step-tests-v4.log](Evidence/start-step-tests-v4.log). Windows PowerShell 5.1에서의 재실행은 아직 미검증이다.

`TestDemo.ps1 -SourceOnly -RequireArt` 재실행도 통과했다: C++ 코어 479 assertions, 콘텐츠 8경로/20오류 주입, 원본 보호 7개, 한국어 450글리프. [source-tests-v4.log](Evidence/source-tests-v4.log). 이 검사는 V7 Target의 UBT 실행이나 Windows 게임 실행을 검증하지 않는다.

## v4 Windows 재시도 — 10:36:13 UTC

사용자 제공 editor 로그에서 V7 수정 후 공유 빌드 설정 충돌이 사라지고, UBT가 MSVC 14.44.35229 / SDK 10.0.26100.0을 선택해 21개 작업 중 첫 SharedPCH 컴파일을 실행한 것을 확인했다. 해당 작업은 깨진 한글 `바탕 화면` 경로의 PCH 파일을 열지 못해 C1083로 실패했다. 실행 시간은 1.29초다. [개인정보 제외 증거 요약](Evidence/windows-build-second-attempt.json).

당시 조치는 기존 v4 ZIP을 짧은 영문 경로에 새로 전체 압축 해제해 시작하는 것이었다. 생성된 Intermediate/Binaries는 이전 폴더에서 옮기지 않도록 했다. 게임 소스나 빌드 옵션을 추가로 변경하지 않았고 엔진 재설치도 지시하지 않았다. 시스템 로캘·UTF-8 옵션이나 UBA 비활성화가 해결책이라고 검증한 것은 아니다. 후속 영문 경로 시도의 실제 결과는 아래에 기록한다.

## 세 번째 Windows 시도 — 10:52:18 UTC, 전체 로그 확인 및 v5 수정

사용자 JSON과 추가 제공된 `start-here-20261023T105218Z-editor.log`(UTF-16 LE, SHA256 `31ac1815b5e8954771d80ea587d1612e2773a1f80f70cd25ef71bb557eb37cfb`)를 대조했다. 영문 `C:\game` 경로와 누락 도구 없음, environment 종료 0, editor 래퍼 종료 1, Build.bat 종료 6을 확인했다. SharedPCH 및 여러 프로젝트 파일 컴파일 후 37.37초에 실패했다. 전체 로그의 오류는 다음 6건이다. 행 번호는 실패한 v4 기준이다.

| 파일 | 오류/행 | v5 수정 |
|---|---|---|
| DawnPlayerController.cpp | C4458 / 227, 231, 329 | 상속 멤버 Player를 가리는 지역변수 3곳을 TravelerPawn으로 변경 |
| DawnWidget.cpp | C4458 / 87, 166 | 상속 멤버 Slot을 가리는 지역변수 2곳을 TextSlot/HudSlot으로 변경 |
| DawnAssetTools.cpp | C2440 / 22 | FTypefaceEntry 기본 생성 후 Name/Font 필드를 지정 |

같은 Editor 파일의 UFont::CompositeFont 직접 접근 경고 C4996 2건(22, 46행)은 `GetMutableInternalCompositeFont()`와 `GetInternalCompositeFont()` 사용으로 수정했다. 두 반환형이 각각 `FCompositeFont&`, `const FCompositeFont&`임을 [공식 UFont API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UFont)에서 확인했다. Package/InputComponent 선언 헤더도 직접 포함했다. 경고를 끄거나 빌드 실패를 무시하도록 변경하지 않았다. 개인정보를 제외한 구조화 요약은 [windows-build-third-attempt.json](Evidence/windows-build-third-attempt.json)이다.

StartHere는 마지막 24줄뿐 아니라 앞선 MSVC/링커/UHT 형태의 오류 최대 16건과 뒤 2줄을 콘솔/진단 JSON에 보존하도록 수정했다. 실제 child pwsh 회귀 검사 9개와 PowerShell 파서 17파일 검사를 통과했다([start-step-tests-v5.log](Evidence/start-step-tests-v5.log), [powershell-parse-v5.log](Evidence/powershell-parse-v5.log)). 소스 검사도 통과했다: 코어 479 assertions, 콘텐츠 8경로/20오류 주입, 원본 보호 7개, 한글 450글리프([source-tests-v5.log](Evidence/source-tests-v5.log)). 이 검사는 변경한 Unreal 클래스의 컴파일을 대체하지 않는다.

수신한 실제 UTF-16 로그에도 StartHere 소스 AST에서 읽은 오류 추출 패턴을 적용해 C4458 5건·C2440 1건 전부를 찾았다([compiler-log-extraction-v5.log](Evidence/compiler-log-extraction-v5.log)). 컴파일을 다시 실행한 검사가 아니다.

v4 배포 ZIP은 변경하지 않고 v5 소스 묶음으로 제공했다. 당시 v5의 UE 재실행은 미검증이었으며, 이후 받은 실제 PC 결과는 아래에 기록한다. 소스 검사를 Unreal 빌드 성공으로 보고하지 않는다.

## v5 에셋 생성 실패 — 12:13:22 UTC와 v6 수정

사용자 assets 로그와 직접 붙여 넣은 `Saved/PathOfDawn/asset-generation-report.json`을 확인했다. UE `5.8.4-58902052+++UE5+Release-5.8`에서 이미지 7개·모델 10개·WAV 4개·폰트 얼굴 1개, 총 22개 임포트가 기록됐고 복합 폰트 생성 호출을 지난 뒤 `create_narrative()`에서 실패했다. 정확한 예외는 `Illustration`의 SoftObjectProperty가 `SoftObjectPath`를 `Texture2D`로 변환하지 못한다는 TypeError다. [사용자 증거 요약](Evidence/windows-assets-v5.json).

v6는 `Portrait`·`Illustration`에 로드한 Texture2D 객체를 대입한다. C++ 속성은 계속 TSoftObjectPtr이며 에셋 내부에는 소프트 참조로 저장된다. 임포터·폰트 생성이나 이미 통과한 C++ 코드는 이 변경으로 교체하지 않는다. 맵·Sequencer의 다음 API도 공식 문서와 대조했지만 실제 실행을 대신한 검증으로 보지 않는다.

실패 보고서가 이미 있었는데 GenerateDemoAssets.ps1이 `status` 검사 직후 throw하여 error/traceback을 출력·복사하지 않은 문제도 수정했다. v6는 고유한 전체 Editor 로그를 지정하고, native 실패 여부와 무관하게 새 보고서를 보존한 뒤 Python 예외를 출력한다. 이전 보고서는 보관하며 새 실행의 성공 근거로 재사용하지 않는다. 새 에디터 검증에는 플레이어 Blueprint의 메시·게임 모드·기본 Pawn 참조도 포함했다.

실행한 v6 검사:

- **서사 변환 계약 검사 6개 통과.** 실제 생성 함수와 실제 34노드 데이터를 좁은 자료형 fixture에서 실행했다. 사용자 엔진 예외의 Texture2D 제약, 7개 이미지 연결, 누락/잘못된 이미지의 저장 차단, 기존 에셋 보존·갱신을 검사한다. Unreal 또는 `.uasset` 생성을 흉내 낸 성공 증거가 아니다. [narrative-import-contract-tests.log](Evidence/narrative-import-contract-tests.log).
- **에셋 실행 도구 검사 20 assertions 통과.** 실제 child PowerShell 프로세스로 실패/손상/없는 보고서·이전 보고서·종료 코드 37·mode 오류·Traceback 표시·공백/한글 인수를 검사했다. [asset-diagnostics-tests-v6.json](Evidence/asset-diagnostics-tests-v6.json). Windows Unreal 실행은 아니다.
- **통합 소스 검사 통과.** 코어 479 assertions, 콘텐츠 8경로/20오류 주입, 원본 보호 7개, 위 서사 계약 6개, 한국어 450글리프. [source-tests-v6.log](Evidence/source-tests-v6.log).
- **PowerShell 19파일 및 변경 Python 구문 검사 통과.** [powershell-parse-v6.log](Evidence/powershell-parse-v6.log).

v6 제공 당시 실제 UE 실행은 미검증이었다. 이후 받은 사용자 PC 결과는 아래에 기록한다. 이 세션은 Windows PC에 연결되지 않았으며, 사용자 PC에서 직접 명령을 수행할 새 로컬 Codex 작업은 [LocalCodex](LocalCodex.md)의 안내로 이어갈 수 있다.

## v6 검증 중단 — 12:28:48 UTC와 v7 수정

전체 assets 로그의 실제 중단은 `verify()` 306행의 `body.get_static_mesh()`에서 발생한 `AttributeError`다. 같은 잘못된 메서드가 상호작용 메시 검사에도 있었다. 서사·맵·연출 생성 이후 필수 에셋 로드와 `L_Galilee` 로드까지 진행한 상태이며, 새 프로세스 재로드 검증 단계는 아직 실행되지 않았다. [근거 요약](Evidence/windows-assets-v6.json).

v7은 두 곳 모두 `get_editor_property('static_mesh')`로 조회한다. 검증 항목을 생략하거나 예외를 무시하지 않는다. 새 Blueprint만 대상으로 메시·기본 Pawn 변경 후 강제 저장과 성공 여부 확인을 추가했으며, 기존 사용자 Blueprint는 보존한다.

로그의 별도 재질 오류 `M_LakeWater: Missing Sine input`도 수정한다. Time→Sine 연결에 첫 입력을 뜻하는 빈 입력 이름을 사용하고, 재질의 6개 연결 함수 반환값을 모두 검사한다. 연결 실패 시 저장 전에 멈추며, 실제 셰이더 컴파일·외관 검증을 통과했다고 표시하지 않는다. 기존 v6의 잘못 생성된 재질은 자동 덮어쓰기 대상이 아니므로 v7 ZIP을 새 영문 폴더에 전체 압축 해제하고 이전 `Content`를 가져오지 않아야 한다.

시작 직후의 `LogAutomationTest: Error: Condition failed` 15건과 Engine 초기화 전 PixelStreaming2RTC 오류는 이후 에셋 생성이 진행된 것과 구별해 기록한다. 해당 로그만으로 프로젝트 자동 테스트 실패 또는 스트리밍 성공·실패 원인을 확정할 수 없다. RTX 5080 CUDA context 생성은 인코더/게임 영상 검증이 아니다.

공식 [UE Python 속성 색인](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/genindex-S)의 `StaticMeshComponent.static_mesh`와 [재질 연결 API](https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/MaterialEditing/ConnectMaterialExpressions?lang=en-US)의 첫 입력 선택·bool 반환을 대조했다. C++ 함수 이름을 Python 노출 메서드로 가정하지 않는다.

실행한 v7 검사:

- 실제 `verify()`·`make_material()` 함수의 제한된 계약 검사 **10개 통과**. `get_static_mesh` 메서드가 없는 컴포넌트 fixture로 전체 검증을 실행했고, 잘못된 메시·Pawn·GameMode·월드·사물·폰트와 6개 재질 연결 중 각 실패를 거부했다. 기존 재질의 보존도 확인했다. [editor-verification-contract-tests.log](Evidence/editor-verification-contract-tests.log). 이 fixture는 Unreal을 구현하거나 셰이더를 컴파일하지 않는다.
- 통합 `TestDemo.ps1 -SourceOnly -RequireArt` 통과: 코어 479 assertions, 콘텐츠 8경로/20오류 주입, 원본 보호 7개, 서사 변환 6개, 위 검증 10개, 한글 450글리프. [source-tests-v7.log](Evidence/source-tests-v7.log).
- 다음 단계 Unreal 자동 테스트의 코어 경로를 실제 테스트 함수에서 추출해 GCC로 실행: **72 checks / 0 errors**. [실행 기록과 재현 명령](Evidence/automation-path-review-v7.json), [재현 코드](Evidence/automation-path-review-v7.cpp). Unreal Automation 프레임워크와 USaveGame API 자체는 실행하지 않았다.
- 변경 Python 파일 전체 구문 검사 통과. 변경한 TestDemo.ps1은 위 통합 실행에서 실제 파싱·실행했다.

v7 제공 당시 실제 Unreal 실행은 미검증이었다. 이후 사용자 실행 보고는 아래에 기록한다. 소스 계약 검사와 공식 API 검토를 Windows 실행 성공으로 취급하지 않는다.

## v7 실행 보고와 v8 시각 개편

사용자는 v7이 실행됐다고 보고했고, 각진 인물·환경과 타이틀·메뉴·일러스트의 품질을 지적했다. 실행 확인은 사용자 보고 범위로 한정한다. 약 5분 플레이, 모든 분기·회귀·이어하기, Pixel Streaming URL 성공을 확인한 것은 아니다.

v8 변경 범위는 타이틀·도입·인물 초상·세 결과의 7종 일러스트, 인물 얼굴·복식의 정적 메시, 호숫가 환경 형태와 소품 배치, UMG 타이틀·대화·결과 구성이다. 새 원본은 `SourceArt/PathOfDawnUnreal/VisualV8` 아래에 분리해 기존 v7 원본을 보존한다. 원화와 Blender 미리보기는 제작 원본 검토 자료이며 실제 Unreal 스크린샷이 아니다.

**v8 실제 엔진 검증은 아직 없다.** 새 `C:\game\PathOfDawn-v8` 폴더에서 `Start-PathOfDawn.cmd`로 빌드·생성·재로드·Cook을 진행하고, 타이틀·대화·결과 이미지와 인물 얼굴·옷, 환경·충돌을 실제 게임에서 확인해야 한다. 기존 v7 `Content`는 복사하지 않는다. 새 테스트 결과는 실행 증거가 확보된 항목만 추가한다.


## GitHub 자동 업데이트 전달 검사

소스 자동 업데이트/보존/경로/압축/모의 세션 롤백 44개 검사, Bootstrap의 고정 커밋·blob 해시·인자 전달·임시 파일 정리·변조 거절 검사, 공식 Windows Node/MinGit ZIP 및 안전한 추출·캐시 31개 검사를 통과했다. `StartHere -BuildOnly`를 추가했으며 기존 자식 프로세스 오류 수집 회귀 검사를 통과했다. `TestDemo -SourceOnly -RequireArt`를 다시 실행해 코어 479개 assertion, 콘텐츠/원화/폰트 검사를 통과했다.

모의 세션 검사와 Linux에서의 Windows ZIP 추출은 Windows 실제 실행이 아니다. Unreal 빌드·게임 플레이·WebRTC 영상은 여기서 실행하지 못했다. 실제 GitHub 게시·다운로드 검증 기록은 `Evidence/github-delivery-verification.json`에 별도로 남긴다.


## Windows 에셋 경로 검사 수정 — 2026-10-24 KST

사용자 PowerShell 로그에서 `4b250f963eaa`의 environment/editor 단계가 끝난 뒤 assets의 원화 사전 검사에서 멈춘 것을 확인했다. `str(path.relative_to(root))`가 Windows에서는 역슬래시를 만들어 `/`로 기록한 AssetManifest의 25개 항목을 잘못 불일치 처리했다. 실제 파일 누락·엔진 설치 오류로 진단한 것이 아니다. 경로를 `.as_posix()`로 통일했다.

실제 원화·FBX·표면 텍스처 파일을 읽되 relative 경로만 PureWindowsPath로 제공한 재현에서 수정 전 25개 동일 오류, 수정 후 25개 통과를 확인했다. 네 회귀 검사에는 OS별 검사 결과 일치와 잘못된 SHA/빠진 manifest 항목의 거절을 포함한다. TestDemo의 원화 검사에도 회귀 검사를 연결했다. 기록: `Evidence/windows-path-validator-fix.json`. Linux에서 경로 처리를 재현한 검사이며, Windows 재실행·Unreal 가져오기·게임·영상 스트리밍 성공을 의미하지 않는다.

한국어 콘솔 출력도 수정했다. StartHere의 UTF-8 바이트를 부모 Windows PowerShell이 CP949로 해석하던 경계에서 양쪽 입출력 인코딩을 맞추고, Python 자식 출력은 프로세스 환경 `PYTHONIOENCODING=utf-8`로 지정한다. 실제 자식 프로세스와 Python의 CP949 불일치를 재현한 뒤 한국어 및 실패 코드 보존을 확인했다. `Evidence/console-encoding-fix-tests.log` 참조. 이는 Linux pwsh7에서의 바이트 경계 검사이며 Windows PowerShell5.1 화면 재시도는 별도다. 기존 updater 44개·Bootstrap·시작 도구 회귀 검사도 통과했다.


## 스트리밍 실행기 출력 파이프 — 2026-10-24 KST

실행 스크립트가 반환해도 6초짜리 자식 프로세스가 native 출력 파이프를 보유하면 상위 Run-Step이 약 6.7초 기다리는 현상을 재현했다. 게임/서버처럼 계속 실행되는 자식이면 자동 브라우저 단계에 도달하지 못할 수 있다. Windows의 지속 프로세스 실행은 전용 stdout/stderr 파일 핸들을 제공하는 Start-Process로 변경했다. 공백·빈 인자·한국어·따옴표·끝 역슬래시·셸 특수문자가 실제 native argv로 유지되는 검사와 소유 프로세스/저장 해시 14개 검사를 통과했다. Windows 분리 실행, 부모 종료 뒤 늦은 로그 기록을 검사하는 통합 테스트는 TestDemo에 연결했으며 Linux에서는 명시적으로 미실행 처리했다. 증거: `Evidence/streaming-launch-handoff.json`.
