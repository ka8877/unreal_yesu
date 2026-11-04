# 공유 복음서 여정 · 첫 구현 기록

2026-11-04 (Asia/Seoul). 사용자의 “이어서 작업” 요청에 따라 소스를 구현했다. 실제 Windows/Unreal 빌드와 공개 URL은 아직 없으며, 아래 장면은 진행 검증용 blockout이다. 영화 같은 실사·반실사 최종 아트와 BGM은 이후 제작해야 한다.

## 구현한 내용

- Unity `ka8877/firstgame`의 고정 커밋 `808d8d1e1eeed908d8925398f80c7173653ef364`에서 실제 C# 원본11개를 확보했다. 각 파일의 Git blob·SHA256·바이트를 기록하고 원본을 수정하지 않았다.
- 실제 C# 카탈로그와 진행 클래스를 .NET8에서 컴파일·평가해 `SourceArt/PathOfDawnUnreal/Gospel/Campaign.json`을 생성했다. 23목표(탄생11·성전7·세례5), 19본문, 81이야기 화면(탄생51)을 보존한다. 고정 ID·본문·출처·인용/요약/극화 구분·장면·음악 역할·음성 키를 포함한다. 음악 역할과 음성 키는 데이터이며 실제 새 음원/더빙을 제작했다는 뜻은 아니다.
- 새 `Core/GospelState.h`는 순서 진행과 마지막 이야기 화면에서만 본문 발견, 읽기 전용 책/일지, 콘텐츠 버전·커서·발견 순서가 맞는 저장을 구현한다. 성전 미리보기는 앞의 탄생 본문을 발견한 것으로 처리하지 않으며 성전7목표·4본문에서 끝난다.
- `DawnGospelData/Subsystem/SaveGame`은 cooked DataAsset, 별도 저장 슬롯 `PathOfDawn_Gospel_Progress_v1`, 읽기 검증·백업·실패 rollback·손상 원본 보존과 명시적 복구를 구현한다. 디스크 USaveGame 동작은 아직 Unreal에서 실행하지 않았다.
- 새 `DawnGospelCharacter/Controller/Widget/GameMode`는 독립 이동·목적지 접근·대화, 발견한 말씀·일지, 저장·이어하기 UI를 구현한다. 인물은 개발용 임시 표시이며 실제 최종 인물·보행 애니메이션은 포함하지 않는다.
- 실제 Editor API로 별도 `/Game/PathOfDawnGospel` DataAsset·한국어 폰트·성전 테스트 맵을 만드는 `generate_gospel_assets.py`를 추가했다. 아직 실행하지 않아 생성된 `.uasset/.umap`은 없다. 기존 갈릴리 맵·에셋·슬롯은 변경하지 않는다.
- 에셋별 실제 패키지 해시와 소스 기준을 보존한다. 사용자가 편집한 패키지·불명확한 소유권·고아 bulk 파일·경로 연결을 만나면 멈춘다. 맵 제작법이 바뀌면 기존 맵을 자동 덮어쓰지 않는다. 별도 Editor 프로세스에서 전체 본문·장면·표식·폰트를 다시 열어 확인하도록 구성했다.
- Windows 빌드 후보와 배포 ZIP 준비 도구를 추가했다. `GospelWindows` 산출물은 원본 소스를 컴파일하는 개발 호스트에서 만들고, 테스터는 패키지 실행 파일만 사용한다. 관리형 Pixel Streaming 업로드/URL 생성은 아직 연결하지 않았다.

## 첫 성전 테스트 장면

맵 경로: `/Game/PathOfDawnGospel/Maps/L_GospelTemplePreview`

나사렛 출발 → 샘가의 마리아 → 절기의 성전 뜰 → 선생과 만남 → 선생들 가운데 → 부모와 재회 → 나사렛으로 귀환, Unity의7목표를 동일한 순서로 경험한다. 실제 장소의 거리·건축을 재현한 장면이 아니라 연결된 개발용 공간이다. 이번 단계는 게임 흐름을 확인하는 기반이며 고품질 아트를 시연하는 완성 장면이 아니다.

WASD/마우스 이동, E 대화, Enter/Space 다음 이야기, M 성경책, J 일지, Esc 메뉴를 사용한다. 목표와 NPC 태그가 모두 일치하고 3D 거리225cm 이내이며 벽에 가려지지 않은 표식에서만 상호작용한다. 대화 중에는 이동을 멈춘다. 기존 갈릴리의 가상 선택·기억 회귀를 공유 캠페인에 넣지 않았다.

## 이 클라우드에서 실행하는 소스 검사

실제 실행 결과: 원본 C# 재평가 바이트 일치, 계약/가져오기/패키징77개 검사, C++ 진행2,190개 assertion(ASan/UBSan), 한국어437자 누락0개를 확인했다. 보존한 갈릴리 코어479개 assertion과 기존 콘텐츠/아트 검사도 통과했다. [실제 검사 요약](Evidence/Gospel-20261104/summary.json)과 같은 폴더의 원본 로그를 참고한다. 이는 Windows·Unreal·GPU 실행 결과가 아니다.

원격 코드 `0f8be6f…`의 [Gospel 소스 CI](https://github.com/ka8877/unreal_yesu/actions/runs/41785330334)와 [Windows 실행기 CI](https://github.com/ka8877/unreal_yesu/actions/runs/41785283655)도 실제 완료·성공했다. Windows 실행기 검사는 UE/GPU가 없는 runner에서의 기존 프로세스 실행 회귀이며 새 게임의 Windows 빌드 성공을 뜻하지 않는다. 작업은 [초안 PR #2](https://github.com/ka8877/unreal_yesu/pull/2)에 보존했다.

```bash
python3 Tools/PathOfDawnUnreal/Gospel/export_campaign.py --verify-sources-only
# .NET8 SDK가 준비된 경우, 원본을 재평가해 바이트 동일성을 확인한다.
python3 Tools/PathOfDawnUnreal/Gospel/export_campaign.py --dotnet /path/to/dotnet --check
python3 -m unittest discover -s Tools/PathOfDawnUnreal/tests -p 'test_gospel_*.py' -v
python3 Tools/PathOfDawnUnreal/tests/test_gospel_core.py --sanitize
python3 Tools/PathOfDawnUnreal/Gospel/validate_gospel_font.py
```

PowerShell이 있으면 `pwsh -File Tools/PathOfDawnUnreal/TestGospel.ps1 -SourceOnly -CheckExportParity -DotNet /path/to/dotnet`으로 동일 검사를 모을 수 있다. Python3, C++17 컴파일러와 `fonttools`가 필요하며 .NET은 원본 재평가에만 필요하다. 새 GitHub Actions는 이 소스 검사만 수행하고 Unreal/GPU가 있는 것처럼 처리하지 않는다.

## Windows UE 호스트에서 생성·실행

현재 클라우드에는 UE/Windows/GPU가 없다. 설치된 UE5.8과 MSVC를 사용하는 Windows 호스트에서 이 소스를 열고 실행한다. 기존 원본과 사용자 수정은 보존한다. C++17 코어 검사는 VS Developer PowerShell의 `cl.exe` 또는 g++/clang++를 사용한다. .NET8 SDK는 이미 내보낸 데이터를 사용하는 Editor 빌드에 필수가 아니다.

```powershell
$ue = 'C:\Program Files\Epic Games\UE_5.8'
python -m pip install -r .\Tools\PathOfDawnUnreal\requirements-art.txt
pwsh -File .\Tools\PathOfDawnUnreal\GenerateGospelAssets.ps1 -EngineRoot $ue
# 실제 에디터에서 생성된 별도 맵을 열고 Play한다.
# /Game/PathOfDawnGospel/Maps/L_GospelTemplePreview
pwsh -File .\Tools\PathOfDawnUnreal\BuildGospelPreview.ps1 -EngineRoot $ue -BuildId gospel-temple-001
python .\Tools\PathOfDawnUnreal\Gospel\prepare_preview_release.py --build-root .\Builds\PathOfDawnUnreal\GospelWindows\gospel-temple-001 --output .\Builds\PathOfDawnUnreal\GospelReleases\gospel-temple-001 --build-id gospel-temple-001
```

이 명령은 이 클라우드에서 성공한 UE 명령이 아니라 **호스트 재개 절차**다. 최초 실제 엔진 빌드에서 API·Cook 차이를 확인하고 오류 로그에 따라 수정해야 한다. `GenerateGospelAssets`는 환경 기록→Editor 컴파일→실제 생성→별도 프로세스 재로드→해시 검사를 수행한다. `BuildGospelPreview`는 Gospel 맵과 전체 Gospel 디렉터리를 Cook하고 기존 프로젝트 설정을 덮어쓰지 않는다. 기존 AlwaysCook 경로의 갈릴리 에셋이 있으면 패키지에 추가 포함될 수 있으며, 최적화는 실제 Cook 뒤 확인한다.

새 소스가 아직 Git 커밋이 없는 ZIP이라면 빌드 도구에 명시적인 Unreal 원본 커밋이 필요하다. 작업 내용이 커밋과 다르면 `sourceDirty`로 기록하며 깨끗한 빌드로 소개하지 않는다. GitHub에서 자동으로 받은 기존 v8 실행기는 기본적으로 갈릴리 빌드를 실행하므로, 이 새 캠페인은 위 별도 절차를 따른다.

## 배포 준비와 실제 배포의 구분

패키지 도구는 실제 Windows PE·PAK·IoStore 컨테이너와 파일 해시를 확인한 뒤 ZIP·manifest·체크섬·미실행 스모크 양식을 만든다. ZIP의 `PLAY-GOSPEL.cmd`가 새 성전 맵을 명시해 실행하며 사용자에게 UE/VS가 필요 없다. 단순한 파일 검사만으로 맵의 Cook·게임 렌더링 성공을 보증하지 않는다.

실제 GPU 스모크 자료가 없으면 상태는 `candidate-not-graphically-verified`다. 실제 스모크도 사용자가 제출한 관측 근거로 기록하며 URL 배포/스트리밍 성공과 구분한다. 이 도구는 두 경우 모두 `publicReady=false`로 두고 서버나 공개 버전을 바꾸지 않는다. 다중 세션의 저장 격리·서비스 선택·실제 WebRTC 영상/소리/입력·URL 고정/복귀는 다음 배포 단계다.

## 남은 제작과 검증

1. UE5.8 Windows 호스트 연결 후 새 코드 컴파일·에셋 생성/재로드·플레이·패키지 실행.
2. 열두 살 예수님과 주요 인물의 실사·반실사 모델/리그/보행·시선·대화 동작, 성전 공간의 재질·조명·카메라 제작.
3. 실제 BGM·공간음·믹싱과 장면 전환 제작, 한국어 UI를 실제 화면에서 검수.
4. 동일 에피소드의 두 엔진 실제 캡처/동작/플레이 시간 비교 후 탄생과 요단강의 공간으로 확장.
5. 작은 패키지로 UE5.8/PixelStreaming2 호스팅 호환성·한국 접속 지연·독립 세션 저장을 확인하고 고정 테스트 URL 제공.

최신 실제 소스 검사 결과는 `Evidence/Gospel-20261104`에 기록한다. 해당 검사는 Unreal 컴파일·USaveGame·실제 화면·음악 청취·스트리밍을 대신하지 않는다.
