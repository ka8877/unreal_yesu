# Windows PC에서 Codex로 제작 이어가기

Windows 로컬 Codex 작업에서는 이 PC의 프로젝트 파일과 설치된 Unreal/MSVC를 사용해 오류 확인 → 수정 → 재빌드를 진행할 수 있다. 현재 대화의 실행 환경은 별도 Debian 클라우드이며, 사용자 PC의 파일·터미널·화면에 연결되어 있지 않다. 접근을 허용한다고 채팅에 적는 것만으로 기존 작업이 Windows 실행 환경으로 전환되지는 않는다.

## 앱에서 열기

1. [OpenAI 공식 Windows 앱 안내](https://learn.chatgpt.com/docs/windows/windows-app)의 다운로드 링크로 Windows용 ChatGPT 데스크톱 앱을 설치하거나 업데이트하고, 자신의 ChatGPT 계정으로 로그인한다. 최신 안내에서 Codex는 이 앱 안의 개발 작업 모드다.
2. 앱에서 Codex를 선택하고 **Add new project / 폴더 열기**로 최신 수정본의 루트 폴더를 연다. 예: `C:\game\PathOfDawn-v8`. `Start-PathOfDawn.cmd`, `Games`, `Tools`, `SourceArt`가 함께 있는 폴더를 선택한다. 실제 압축 해제한 이름이 다르면 그 위치를 사용한다.
3. 설정의 **Agent environment**가 **Windows native**인지 확인한다. 터미널은 PowerShell을 사용한다. 이 프로젝트는 설치된 Windows Unreal/MSVC를 실행하므로 Windows 로컬 작업으로 진행한다. 터미널 선택과 에이전트 실행 환경 선택은 별개다.
4. 이 로컬 프로젝트에서 새 Codex 작업을 시작하고 아래 요청을 붙여 넣는다. 프로젝트 밖의 Unreal 설치·사용자 캐시에 접근이 필요하면 로컬 앱이 표시하는 해당 작업의 권한 요청을 확인한다. 모든 PC 권한을 일괄 해제하거나 엔진을 다시 설치할 필요는 없다.

앱의 프로젝트 선택·Codex 시작 순서는 [공식 시작 안내](https://learn.chatgpt.com/docs/quickstart?setup=app)에 따른다. 로그인은 앱에서 완료한다. 비밀번호·API 키·페어링 코드를 이 대화에 붙여 넣지 않는다.

```text
이 Windows PC의 실제 Unreal 도구를 사용해 PathOfDawnUnreal 데모가 실행될 때까지 수정과 검증을 이어가라.

먼저 현재 디렉터리, Git 상태, 루트와 게임의 AGENTS.md, Docs/PathOfDawnUnreal/README.md, DeliveryStatus.json, TestReport.md, KnownIssues.md를 읽어라. 사용자 파일·기존 Unity 프로젝트·생성된 에셋을 보존하라. 프로젝트를 처음부터 다시 만들지 마라.

이전 PC 로그에는 UE 5.8.4, MSVC 14.44, SDK 10.0.26100.0, RTX 5080이 있었다. 지금 설치 파일과 명령으로 다시 확인하라. 원격 Debian 환경을 설명하는 과거 문서를 현재 Windows 도구 부재의 근거로 삼지 마라.

사용자는 v7이 실행됐다고 보고했지만 인물·환경이 각진 블록처럼 보이고 타이틀·메뉴·일러스트가 기대에 못 미친다고 지적했다. v8은 VisualV8/Illustrations의 7종 원화와 VisualV8/Models의 얼굴·복식 형상을 갖춘 정적 캐릭터, 개선한 환경 메시·소품 배치, UMG 타이틀·대화·결과를 적용하는 변경이다. 이전 원본은 보존한다. 정적 모델을 골격·표정 애니메이션이 있는 완성 캐릭터라고 설명하지 마라. 아직 v8 컴파일·가져오기·실행은 확인되지 않았다.

v8은 새 영문 폴더에서 생성하라. 기존 v7의 Content/Intermediate/Binaries를 복사하지 마라. 생성기는 기존 사용자 맵·재질·Blueprint를 자동 덮어쓰지 않으므로 이전 Content를 가져오면 새 시각 구성이 반영되지 않을 수 있다. 사용자 작업이 있는 기존 폴더는 보존하고 필요한 변경은 에디터에서 별도로 검토하라. v7을 실행한 PC에서 엔진이나 Visual Studio를 다시 설치할 필요는 없다.

새 실행 전에 Saved/PathOfDawn/asset-generation-report.json과 관련 Saved/Logs, Docs/PathOfDawnUnreal/Evidence를 보존·확인하라. 이전 v5/v6/v7 폴더에 보고서가 있으면 읽기 전용으로 참고하라. Mac/Android/Linux SDK INVALID 메시지만 보고 Win64에 불필요한 SDK를 설치하지 마라.

설치된 Engine의 헤더·Python API·CLI와 실제 로그를 우선해 BuildEditor → GenerateDemoAssets → 에셋 재로드 검사 → TestDemo → Development BuildCookRun → Windows 실행까지 진행하라. 한 에디터의 변경 작업은 직렬화하고, 실패하면 첫 실제 오류를 읽어 수정한 뒤 해당 단계부터 재개하라. 기존 사용자 수정 에셋을 일괄 삭제하거나 덮어쓰지 마라.

게임 실행 후 새 타이틀·메뉴·대화·결과 이미지와 한국어 가독성, 3D 예수님·시몬의 얼굴·옷, 환경과 충돌을 실제 화면으로 확인하라. 원본 미리보기를 게임 캡처로 보고하지 마라. 이어서 3인칭 이동, 조사, 인물 대화, 두 선택·세 결말, 회귀, 종료 후 이어하기를 확인하라. 실제 캡처와 약 5분 플레이 시간을 기록하라. UI 조작 도구가 없다면 화면 검증을 했다고 주장하지 말고 필요한 사용자 확인을 구체적으로 남겨라.

로컬 게임 검증 다음 실제 Unreal Pixel Streaming을 localhost에서 연결하라. HTML 게임으로 대체하지 마라. 외부 URL은 기존 권한과 연결 가능한 네트워크 범위에서만 진행하고 새 과금 자원이나 방화벽·라우터 공개 변경은 임의로 수행하지 마라. 실제 영상·음성·입력 검증 없이 URL 배포 완료라고 하지 마라.
```

## 이미 Codex CLI를 사용 중인 경우

Windows PowerShell에서 해당 소스 루트로 이동한 뒤 `codex`를 실행하고 같은 요청을 입력할 수 있다. 최초 로그인·설치는 [공식 CLI 안내](https://learn.chatgpt.com/docs/codex/cli)를 따른다. 앱과 CLI를 모두 설치할 필요는 없다.

```powershell
Set-Location -LiteralPath 'C:\game\PathOfDawn-v8'
codex
```

로컬 Codex가 빌드 명령을 실행할 수 있다는 사실은 게임 화면 자동 조작까지 제공된다는 뜻은 아니다. 실제 세션의 화면 조작 도구와 권한을 확인하고 그래픽 테스트 증거를 별도로 남긴다. 이 안내를 작성한 클라우드 세션에서 위 Windows 실행을 완료한 것은 아니다.

## 현재 대화와 연결의 구분

[공식 원격 연결 안내](https://learn.chatgpt.com/docs/remote-connections)는 연결된 PC의 로컬 자원을 사용하는 기능을 설명한다. 기능 제공 범위는 계정·앱·작업 종류에 따라 다르며, Work Cloud 로컬 접근은 동기화 활성화 이후 만든 새 작업에 적용된다. 기존 클라우드 작업이 자동 전환된다고 가정하지 않는다. 이 프로젝트는 먼저 위 방법으로 Windows 로컬 Codex 작업을 만드는 경로를 사용한다.

이 문서는 2026-10-23 공식 문서 확인을 바탕으로 작성했다. 로컬 앱 설치, 로그인, 연결 및 실제 Unreal 실행은 이 클라우드 작업에서 수행하지 않았다.
