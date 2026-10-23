# 새벽의 길: 갈릴리의 첫 아침

Unreal Engine 5.8 기반 한국어 3인칭 서사 어드벤처의 제작 소스입니다. 최신 원화·인물·호숫가·타이틀 UI 개선분(v8)을 포함합니다. 플레이 시간 목표는 약 5분이며, 현재 버전의 실제 플레이 시간과 Windows 빌드·스트리밍은 아직 검증되지 않았습니다.

**ZIP을 매번 직접 내려받을 필요 없이 아래 실행기로 최신 공개 버전을 가져올 수 있습니다.** GitHub는 소스를 배포하며, 실제 게임의 컴파일·렌더링은 Unreal과 개발 도구를 설치한 Windows PC에서 수행합니다. 이 저장소 주소 자체가 게임 플레이 URL은 아닙니다.

## Windows에서 한 번만 준비

Windows 터미널의 **PowerShell** 탭에 다음을 붙여 넣습니다. 관리자 권한은 필요하지 않습니다. 엔진 재설치·방화벽 변경·유료 서비스 생성은 하지 않습니다.

```powershell
$file = Join-Path $env:TEMP 'PathOfDawn-Bootstrap.ps1'
Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/ka8877/unreal_yesu/main/Tools/PathOfDawnUnreal/Bootstrap.ps1' -OutFile $file
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $file -Streaming
```

소스는 `C:\PathOfDawn\versions\source-<커밋 앞 12자리>`에 자동으로 준비합니다. 최초 실행과 새 버전은 Editor 컴파일, 에셋 생성, 검사, Windows 패키징을 진행하므로 시간이 필요합니다. 이미 설치한 UE 5.8과 C++ 도구를 사용합니다. 브라우저 도구는 `-Streaming`을 선택했을 때만 로컬 폴더에 준비합니다.

이후에는 **`C:\PathOfDawn\Play-in-Browser.cmd`를 더블클릭**하면 갱신 후 브라우저 테스트를 시작합니다. Windows 게임 창으로 실행할 때는 `Update-PathOfDawn.cmd`, 종료할 때는 `Stop-PathOfDawn.cmd`를 사용합니다. 같은 동작을 명령으로 실행할 수도 있습니다.

```cmd
C:\PathOfDawn\Update-PathOfDawn.cmd -Streaming
```

새 소스가 없고 기존 Windows 빌드가 있으면 그 빌드를 사용합니다. 새 소스는 별도 폴더에서 준비하므로 예전 ZIP 폴더와 사용자가 수정한 파일을 덮어쓰지 않습니다. 새 코드가 곧바로 게임에 반영되는 것은 아니며, 컴파일과 패키징이 필요합니다.

## 브라우저 접속 범위

스트리밍이 해당 PC에서 성공하면 열리는 주소는 **http://127.0.0.1:8080/** 입니다. 같은 PC용 주소이며 공개 인터넷 주소가 아닙니다. 화면·음성·이동·대화·회귀를 직접 확인해야 합니다. GitHub Pages에는 Unreal 실행 파일을 올려서 실행할 수 없습니다.

공개 플레이 URL에는 GPU PC 상시 실행, 접근 제한, HTTPS/WSS, WebRTC 연결과 필요 시 STUN/TURN 설정 및 외부망 검증이 추가로 필요합니다. 현재 공개 플레이 URL은 없습니다. 소스 다운로드나 HTTP 응답 성공을 Unreal 실행 성공으로 기록하지 않습니다.

## 현재 자료

- [자동 업데이트와 실행 안내](Docs/PathOfDawnUnreal/GitHubUpdates.md)
- [게임 제작·빌드 안내](Docs/PathOfDawnUnreal/README.md)
- [검증 결과](Docs/PathOfDawnUnreal/TestReport.md), [미완료 항목](Docs/PathOfDawnUnreal/KnownIssues.md)
- [아트 출처·한계](Docs/PathOfDawnUnreal/AssetManifest.md), [서사 출처와 창작 구분](Docs/PathOfDawnUnreal/Narrative.md)

이미지와 모델 원본은 일반 Git 파일로 포함되어 자동 다운로드에 LFS 설치가 필요하지 않습니다. 생성된 Unreal `.uasset`·`.umap`은 실제 Editor에서 생성해야 하며, 엔진 본체·사용자 저장·빌드 캐시·인증 정보는 이 저장소에 포함하지 않습니다.
