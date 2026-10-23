# Windows PC 개발 도구 준비

초기 진단의 누락 도구는 후속 설치로 준비되었다. 사용자 제공 2026-10-23 10:25:39 UTC 로그에서는 UE 5.8.4, Visual Studio Build Tools 2022 17.14.37806.7, MSVC 14.44.35207, Windows SDK 10.0.26100.0이 확인된다. 게임이나 인코더를 실제 실행한 결과는 아니다.

## v7이 실행된 PC에서 v8 시작

사용자는 v7 실행을 보고했다. v8은 타이틀·메뉴·일러스트·3D 인물과 환경을 개편하는 소스 묶음이다. 이미 준비된 Unreal·Visual Studio를 다시 설치할 필요는 없다. v7 실행 보고가 v8의 빌드·화면 검증까지 의미하지는 않는다.

1. 실행 중인 이 프로젝트의 에디터와 실패한 시작 창을 닫는다.
2. `PathOfDawn-Source-20261023-v8.zip` **전체를 새 영문 폴더**에 압축 해제한다. 예: `C:\game\PathOfDawn-v8`. 기존 프로젝트와 사용자 작업은 보존하고 `Content`/`Intermediate`/`Binaries`는 복사하지 않는다. 기존 맵·재질·Blueprint는 자동 덮어쓰지 않으므로 v7의 Content를 가져오면 새 시각 구성이 반영되지 않을 수 있다.
3. 새 폴더 안의 `Start-PathOfDawn.cmd`를 더블클릭한다. `Setup-PathOfDawn-PC.cmd`로 도구를 다시 설치할 필요는 없다.
4. `[environment]`/`[editor]` 로그가 새 폴더 아래에 생성되는지 확인한다. 컴파일 성공 시 에셋 생성·검사·패키징 단계가 이어진다. 각 단계의 성공은 실제 로그로 판단한다.

명령창에서 실행하려면 `C:\game\PathOfDawn-v8\Start-PathOfDawn.cmd`를 사용한다. 새 오류가 발생하면 해당 단계의 전체 `start-here-*-<단계>.log`를 전달한다. v6 이후 실행 도구는 에셋 생성 실패 내용도 그 로그에 출력하고, Evidence에 `asset-generation-report-<시각-ID>.json` 및 전체 `GenerateDemoAssets-<시각-ID>-editor.log`를 남긴다. 현재 v8의 Unreal 컴파일·가져오기·게임 실행은 미검증이다.

PC에서 에이전트가 직접 실행·수정하게 하려면 [Windows 로컬 Codex로 이어가기](LocalCodex.md)에 따라 같은 소스 루트를 로컬 프로젝트로 열고 새 작업을 시작한다. 현재 클라우드 대화에는 PC 연결이 없지만, 로컬 작업은 설치된 Windows 도구를 사용할 수 있다. 비밀번호나 원격 접속 코드를 채팅에 보낼 필요는 없다.

## v4의 C1083와 깨진 한글 경로

사용자 제공 10:36:13 UTC 로그에서는 V5 공유 설정 충돌을 통과하고 MSVC 컴파일의 첫 SharedPCH 작업까지 진행했다. 이때 `바탕 화면`이 깨진 문자로 표시된 `.pch` 경로에 대해 C1083 / `No such file or directory`가 발생했다. 빌드 도구 체인 안의 경로 문자 처리 문제로 판단하며, UBA/MSVC 중 어느 단계에서 변환됐는지는 아직 확정하지 못했다. OneDrive 동기화 자체가 실패 원인이라는 증거는 없다.

1. 실패한 시작 창을 닫고, 실행 중인 이 프로젝트의 에디터가 있다면 닫는다.
2. 기존 프로젝트 폴더는 그대로 둔다. 최신 v8 ZIP을 `C:\game\PathOfDawn-v8` 같은 **아직 사용하지 않은 영문 폴더**에 새로 전체 압축 해제한다. 사용 중인 폴더에 덮어쓰지 않는다.
3. 새 폴더에 `Games`, `SourceArt`, `Tools`, `Streaming` 및 `Start-PathOfDawn.cmd`가 함께 있는지 확인한다. 이전 실행 폴더의 `Intermediate`/`Binaries`는 복사하지 않는다. 이전 절대 경로를 담은 생성 파일을 새 위치로 가져오지 않기 위해서다.
4. 새 폴더의 `Start-PathOfDawn.cmd`를 실행한다. 새 `[environment]`/`[editor]` 로그 위치가 영문 경로로 시작하는지 확인한다.

후속 10:52:18 UTC 로그에서 영문 `C:\game` 경로의 SharedPCH 작업이 통과하고 프로젝트 C++ 파일 컴파일로 진행한 것을 확인했다. 당시 C++ 오류는 v5에서 수정했고, 다음 시도는 에셋 생성 단계로 진행했다. 엔진·Visual Studio 재설치, 시스템 로캘 변경, 임의 PCH 파일 생성이나 다른 프로젝트의 캐시 삭제가 필요하지 않다.

## 도구가 없는 다른 PC의 최초 설치

1. `PathOfDawn-Source-20261023-v8.zip`을 내려받아 **새 영문 폴더**에 전체 압축 해제한다. 기존 프로젝트 폴더는 그대로 보관한다.
2. `Setup-PathOfDawn-PC.cmd`를 **마우스 오른쪽 버튼으로 클릭 → 관리자 권한으로 실행**한다. PC 전체에 설치하는 개발 도구에 필요한 권한이며, Windows 권한 요청과 설치 약관은 직접 확인한다.
3. 안내된 도구 설치가 끝나면 Epic Games Launcher에서 로그인하고 **Unreal Engine → 라이브러리 → 엔진 버전 추가 → 5.8 정식 버전 설치**를 진행한다. Launcher 설치와 Unreal Engine 설치는 별개다.
4. Unreal 설치 완료 후, 새 v8 폴더의 `Start-PathOfDawn.cmd`를 실행한다.

설치 도우미는 필요한 도구만 순서대로 준비한다. Windows 기본 PowerShell로 실행되므로 PowerShell 7이 아직 없어도 시작할 수 있다. winget이 없으면 Microsoft의 App Installer 설치 주소를 안내하고 멈춘다. 재부팅이 필요한 설치 결과는 표시하고 중단하며, 재부팅 후 같은 파일을 다시 실행할 수 있다.

기존 Visual Studio가 있으나 필요한 C++ 구성 요소가 빠져 있으면 별도의 Visual Studio를 중복 설치하는 대신 설치 관리자에서 수정하도록 안내한다. 기존 설치를 제거하거나 무관한 도구를 업데이트하지 않는다. Python에는 프로젝트 검사에 필요한 Pillow와 fontTools를 사용자 범위로 설치한다.

명령만 먼저 보려면 압축을 푼 폴더에서 `Setup-PathOfDawn-PC.cmd -PlanOnly`를 실행한다. 진단·설치 결과는 같은 폴더 아래 `Docs/PathOfDawnUnreal/Evidence`에 남긴다. 이 파일은 게임 설치 파일이 아니며 Unreal을 대신 로그인·설치하거나 공개 게임 URL을 만드는 도구도 아니다.

## 확인한 공식 자료

- [winget install](https://learn.microsoft.com/windows/package-manager/winget/install)
- [Visual Studio Build Tools 구성 요소](https://learn.microsoft.com/visualstudio/install/workload-component-id-vs-build-tools?view=vs-2022)
- [Visual Studio 설치 명령](https://learn.microsoft.com/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022)
- [UE5.8 공식 발표](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available)
- 정확한 패키지 ID·버전·공식 설치 URL 조회 기록: `Evidence/setup-official-sources.json`

현재 검증 범위는 공식 자료 확인과 스크립트 구문·로직 검사다. 새 설치 도우미를 실제 Windows에서 실행한 결과와 Unreal 빌드·그래픽·브라우저 조작은 아직 확인하지 못했다.

별도 소형 설치 도우미 `PathOfDawn-PC-Setup-20261023.zip`도 동일한 설치 도구만 담고 있다. 이 소형 ZIP은 게임 프로젝트를 포함하지 않는다. v3에는 Store 설치 PowerShell 탐색 수정도 포함하므로 새 프로젝트 묶음을 사용하는 경로를 권장한다.

`0x8A150019` / `-1978335207`은 winget이 관리자 권한을 요구한 결과다. 기존 v3 파일도 관리자 권한으로 다시 실행하면 이 차단을 넘길 수 있다. 후속 소스에는 설치 전 권한 확인과 해당 오류의 구체적인 재실행 안내를 추가했다. Python만 사용자 범위에 설치하거나 `-PlanOnly`로 확인할 때는 관리자 권한을 강제하지 않는다.
