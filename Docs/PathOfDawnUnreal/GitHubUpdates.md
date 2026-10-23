# GitHub에서 자동 갱신

공개 소스 저장소: https://github.com/ka8877/unreal_yesu

이전 대화의 `/workspace/...zip` 경로는 클라우드 작업 파일 경로이며 사용자의 Windows 다운로드 주소가 아니다. 이제 소스는 실제 GitHub HTTPS 주소에서 받는다. GitHub는 제작 소스를 제공하고 Windows PC는 Unreal 게임을 빌드·실행한다.

## 첫 실행과 다음 업데이트

루트 [README](../../README.md)의 PowerShell 명령을 한 번 실행한다. `-Streaming`을 빼면 Windows 게임 창으로 실행하고, 붙이면 첫 localhost 브라우저 테스트를 시도한다. 현재 설치된 Unreal/Visual Studio/SDK/Python/PowerShell을 재사용한다. 설치되지 않은 엔진·C++ 도구는 기존 진단 절차로 안내한다.

이후 `C:\PathOfDawn\Play-in-Browser.cmd`를 더블클릭하면 최신 main 커밋을 확인하고 브라우저 모드로 실행한다. `Update-PathOfDawn.cmd`는 Windows 게임 창, `Stop-PathOfDawn.cmd`는 소유 세션 종료용이다. 설치 루트는 `-InstallRoot`로 정할 수 있으나 한글·OneDrive 바탕 화면 경로는 피한다. 기본값은 `C:\PathOfDawn`이다.

```powershell
# 소스만 먼저 받기: Windows 빌드나 실행을 시작하지 않는다.
pwsh -File C:\PathOfDawn\Bootstrap.ps1 -DownloadOnly

# 특정 공개 커밋으로 되돌아가 재실행하기(40자리 실제 커밋 SHA 사용).
pwsh -File C:\PathOfDawn\Bootstrap.ps1 -CommitSha <40자리-SHA> -Streaming
```

사용자가 이미 실행 중인 예전 ZIP 폴더의 게임은 첫 전환 전에 게임 메뉴로 종료한다. 관리형 실행기는 자신이 기록한 버전의 프로세스만 정리하며, 임의로 모든 Unreal 프로세스를 종료하지 않는다.

## 동작과 데이터 보존

1. GitHub API로 main의 커밋 SHA를 확인한다. 같은 SHA의 업데이트 스크립트를 받아 Git blob 해시와 문법을 확인한다.
2. 그 SHA로 고정된 소스 아카이브를 임시 폴더에 받고 구조를 검증한다. 완료된 버전 폴더만 사용한다. Git/LFS 계정 설정은 소스 갱신에 필요하지 않다.
3. 새 버전은 `versions/source-<커밋 앞 12자리>`에 만든다. 기존 버전과 사용자 파일을 덮어쓰지 않는다. 새 소스가 없으면 기존 빌드 manifest를 찾아 재사용한다.
4. 새 Windows 빌드가 준비된 뒤, 이전 소스 폴더에 기록된 소유 프로세스를 종료하고 새 후보를 실행한다. 빌드 실패 시 이전 게임을 중단하지 않는다.
5. 브라우저 실행은 미검증 후보 테스트이며 그래픽 검증 완료나 정식 서비스 승격으로 기록하지 않는다. 검증을 마친 패키지 교체는 기존 `UpdateDemo.ps1`의 smoke-report 절차를 사용한다.

이 실행기는 ZIP 수동 다운로드를 없애지만 **새 커밋의 파일 전송과 Unreal 빌드는 여전히 필요하다.** 서로 다른 버전 폴더를 보존하므로 디스크 사용량이 증가한다. 자동으로 이전 소스나 빌드 폴더를 삭제하지 않는다. 소스 에셋의 현재 최대 파일은 17 MB 미만이며, LFS 포인터 대신 실제 파일을 Git에 넣어 GitHub 아카이브를 그대로 사용할 수 있게 했다.

게임 저장은 기존 `USaveGame`과 `%LOCALAPPDATA%\PathOfDawnUnreal\Host` 아래의 안정적인 호스트 경로를 계속 사용한다. 소스 버전 폴더와 브라우저 localStorage에 저장하는 구조가 아니다. 최신 업데이트를 확인하려면 인터넷이 필요하며, GitHub 오류/요청 제한 시 이전 소스를 지우지 않고 중단한다.

브라우저 모드에서는 기존 호환 도구를 우선 사용하며, 없으면 Node 22.14.0/npm 10.9.2 및 MinGit 2.56.0.3 x64를 공식 ZIP에서 SHA256 검증 후 `tools` 폴더에 준비한다. 시스템 PATH·방화벽·관리자 설정은 변경하지 않는다. 공식 Pixel Streaming 인프라는 기존 lock 파일의 커밋을 유지한다. 프런트엔드 준비가 전환 중 수행될 수 있으므로 무중단·즉시 교체가 아니다.

## URL과 종료

브라우저 주소는 같은 Windows 호스트의 `http://127.0.0.1:8080/`이다. 주소는 버전을 바꿔도 같지만 새 패키지 실행·재연결이 필요하다. 게임 화면의 빌드 ID와 웹 상태의 빌드 ID를 비교한다. 공개 인터넷/LAN 주소는 이번 변경으로 생성하지 않았다.

스트리밍 중에는 GPU PC, Unreal 게임 프로세스, Node 시그널링 프로세스가 켜져 있어야 한다. 게임 메뉴에서 저장한 뒤 `C:\PathOfDawn\Stop-PathOfDawn.cmd`로 종료한다. 수동으로 실행했다면 **그 버전 폴더**의 아래 명령으로 종료한다.

```powershell
pwsh -File .\Tools\PathOfDawnUnreal\StopStreaming.ps1 -IncludeLocalGame
```

같은 PC에 이미 실행 중인 다른 복사본이 있으면 종료하고 시작한다. 에디터·MCP·원격 콘솔·임의 파일 제어 포트는 공개하지 않는다.

## 검증의 한계

자동화 스크립트·다운로드·압축 해제·소스 무결성은 클라우드에서 확인할 수 있다. 이 환경은 Linux이며 Windows UE/GPU가 없어 현재 소스의 Editor 컴파일, 패키징, 실제 게임 화면과 Pixel Streaming 미디어는 실행하지 못한다. 최초 Windows 실행 결과와 공개망 미디어 검증을 별도로 기록해야 한다.
