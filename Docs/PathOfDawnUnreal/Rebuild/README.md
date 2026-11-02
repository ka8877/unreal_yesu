# 말씀의 여정 — 재구축 작업 현황

2026-11-02 KST. **사용자 PC의 Unreal Editor에서 Editor 컴파일과 환경 에셋 17개의 임포트·저장까지 확인했다. 새 게임의 실제 플레이 빌드는 아니며 그래픽 기준 장면은 BLOCKED다.**

기존 `9ae7fc27c71d` 버전은 복구 기준으로 보존했다. `rebuild/word-journey-luke2`는 새 작업 브랜치다. 현재 시작 맵·GameMode·Cook·Pixel Streaming·자동 업데이트의 main 경로를 바꾸지 않았다. 기존 사용자의 저장과 실행 중인 PC 프로세스에 접근하지 않았다. 과거 로그에서 Windows 패키징과 스트리밍 시작이 끝났지만 실제 브라우저 영상·음성·입력 증거는 없다. 확인된 주소는 사용자 PC의 `http://127.0.0.1:8080/`이며 공개 인터넷 주소가 아니다.

## 실제로 추가한 것

- Poly Haven의 CC0 돌·흙·목재 2K PBR과 스캔 도기 FBX 원본. [자산·사용 조건·원본 검사](AssetAcquisition.md). 실제 파일은 `SourceArt/PathOfDawnUnreal/Rebuild/Environment/`에 있다.
- 추가로 MakeHuman의 CC0 인체·리그 정의와 Donitz 의상 제작 원본 약 34MB를 `CharacterSources/`에 확보했다. OBJ/UV는 Blender에서 읽었지만 조립된 성인·UE 리그·애니메이션이 아니다. 원래 의상은 중세 수도복이므로 1세기 복식으로 그대로 사용하지 않으며 디자인 수정과 검수가 필요하다. 아기·아동의 대체재로 사용하지 않는다.
- 누가복음 2:1–7, 8–20, 41–52의 한국어 요약·사건 메타데이터. [출처와 생략 범위](Narrative.md). 2:21–40은 체험·완료한 사건으로 기록하지 않는다.
- C++ `JourneyJournal.h`: 빈 기록 → 사건 체험 → 기록 해금 → 사용자 기록 확정, 중복/지연 콜백 방지, 체크포인트 복원 검증. 대체 결말·시간 회귀가 없다.
- Unreal `JourneyJournalData`, `JourneyJournalSubsystem`, `JourneySaveGame`, `JourneyJournalWidget`: 런타임 DataAsset, 별도 저장, 미래 내용 비공개, UMG 기록책과 입력 잠금. **Editor C++ 컴파일은 사용자 로그로 확인했고 실제 저장·UMG·화면은 미검증**이다. 기존 게임에는 연결하지 않았다.
- 실제 Editor API를 사용하는 환경 임포터·고품질 원본 World 복제 기반 기준 장면 생성 경로. 필수 인물이 없으면 맵 생성 전에 차단한다. 기존 v8 인물·도형·성인 축소 아동을 대체재로 허용하지 않는다.
- 읽기 전용 PC 에셋 진단과 공식 무료 샘플 준비 도구. Epic 로그인·약관과 유료 구매를 자동 처리하지 않는다.

## 품질 게이트와 막힌 항목

| 단계 | 상태 | 근거 |
| --- | --- | --- |
| 조사·복구 기준 보존 | SOURCE_DONE | 브랜치/기준 커밋, `Evidence/Rebuild/environment.json` |
| 환경 원본과 Unreal 임포트 | USER_LOG_CONFIRMED | 실제 원본 검증 및 사용자 UE에서 12텍스처·4재질·1메시 저장 게이트 통과 |
| 자연스러운 인물·복식·이동·완성 공간 | BLOCKED | 승인된 성인·아기·목자·애니메이션·건축 팩 미확보 |
| Unreal 그래픽 기준 장면 | BLOCKED | PC의 Editor는 실행됐으나 실제 인물·완성 공간·3종 화면 검수 부족. 클라우드의 직접 PC 연결은 없음 |
| 탄생부터 첫 기록까지 플레이 | NOT_IMPLEMENTED | 그래픽 기준 장면 이후 연결할 단계. 독립 기록책 소스만 준비됨 |
| 열두 살 성전 확장 | BLOCKED | 탄생 검수 및 연령에 맞는 아동·성전 에셋 선행 필요 |
| 새 빌드·URL 교체 | NOT_RUN | 새 맵/Cook/패키지/미디어·공개 접속 검증 없음 |

목표 8–12분은 플레이 시간 목표이며 측정 결과가 아니다. 실제 게임 캡처와 새 Windows ZIP은 없다. 환경 원본 검사표와 Blender 로드 보고서는 게임 캡처로 제출하지 않는다. 구체적인 필수 역할은 [AssetRequirements.json](AssetRequirements.json), 미입력 바인딩은 `Tools/PathOfDawnUnreal/Rebuild/asset-bindings.example.json`에 있다. 미확보 경로는 의도적으로 `null`이다.

## 재현한 소스 검사

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\TestRebuild.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1
```

첫 명령은 Linux GCC 또는 Windows Developer PowerShell의 MSVC와 Python/Pillow를 사용한다. C++ 132 assertions, 서사 오류 주입 24개, 환경 변조 검사 7개, 인체/의상 원본 변조 검사 5개, 임포트·에셋 정책·Python 격리·샘플 조사 계약 27개를 통과했다. 두 번째는 준비 상태를 검사하며 현재 **정상적으로 BLOCKED/종료 코드 2**가 된다. 성공으로 무시하지 않는다. 로그와 JSON은 `Docs/PathOfDawnUnreal/Evidence/Rebuild/`에 있다. 이 검사는 Unreal 컴파일·저장 파일 I/O·셰이더·UMG·그래픽 품질을 검증하지 않는다.

GitHub의 [소스 검사](https://github.com/ka8877/unreal_yesu/actions/runs/41472781994)와 [실제 Windows 실행기 검사](https://github.com/ka8877/unreal_yesu/actions/runs/41472782103)도 통과했다. 후자는 PowerShell 7/Windows PowerShell 5.1 부모 실행기의 파일 핸들·프로세스 유지·로그 수집 검증이며 Unreal 게임 실행이 아니다. 소스 검사 workflow의 Windows job에서는 별도 샘플 실행기 17개 검사도 통과했다. 결과는 `Evidence/Rebuild/ci.json`에 있다.

## Windows PC에서 다음 작업

현재 클라우드에서 사용자 PC를 직접 조작할 수 없다. PC에 준비된 Unreal/GPU를 실제로 사용할 수 있는 로컬 작업 환경이 필요하다. [기존 로컬 작업 안내](../LocalCodex.md)의 재구축 우선 지시를 따른다. 이미 실행된 엔진을 다시 설치할 필요는 없다.

Windows PowerShell 5.1에서 `& 'C:\PathOfDawn\Bootstrap.ps1'`를 직접 실행하면 기본 실행 정책에 막힐 수 있다. 이미 설치된 `.cmd` 실행기는 `powershell.exe -ExecutionPolicy Bypass -File`을 통해 해당 프로세스에서만 실행하므로 다음 명령을 사용한다. PC 전체 정책이나 관리자 권한은 변경하지 않는다. 두 번째 단계는 다운로드 성공 시에만 실행한다.

```powershell
& 'C:\PathOfDawn\Update-PathOfDawn.cmd' -CommitSha 'bb928a4ca5436f5ccbac8217a09ee366d6216d28' -DownloadOnly
if ($LASTEXITCODE -eq 0) {
    & 'C:\PathOfDawn\versions\source-bb928a4ca543\Prepare-WordJourney-Art.cmd'
}
```

이 명령은 준비용 원본과 진단·공식 페이지를 여는 경로다. 기존 게임을 빌드하거나 실행 중인 세션을 교체하지 않는다. 다운로드 실패 후 준비 파일을 찾을 수 없다는 메시지는 별도의 설치 실패가 아니므로 첫 오류부터 확인한다.

이 브랜치의 소스를 받은 뒤 `Prepare-WordJourney-Art.cmd`를 실행하면 공식 Game Animation Sample과 MetaHuman 문서를 열고 기본 프로젝트 폴더를 읽기 전용으로 조사한다. 다른 에셋 위치가 있으면 다음처럼 지정한다.

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareArtOnPC.ps1 -AssetRoots 'D:\Unreal Projects' -OpenOfficialPages
```

본인 Epic 계정으로 무료 샘플을 라이브러리에 추가하고 UE 5.8용 별도 샘플 프로젝트를 만드는 과정은 계정/약관 확인이 필요하다. 성인 MetaHuman만으로 아기·아동·복식이 확보되는 것은 아니다. 라이선스 제한 원본과 개인 근거 파일은 공개 저장소에 커밋하지 않는다. 로컬 파일은 `.local/`에 보관한다.

`Prepare-WordJourney-Art.cmd`가 공식 페이지를 열었다고 샘플 설치가 끝난 것은 아니다. Game Animation Sample은 다음 순서로 확보한다. 여기서 **프로젝트 생성**은 Epic이 제공하는 샘플 파일을 PC에 받는 버튼 이름이다.

1. [Game Animation Sample](https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016) 페이지에서 Launcher와 같은 Epic 계정으로 로그인한다.
2. 가격이 무료/₩0인 것을 확인하고 **내 라이브러리에 추가** 또는 **받기**를 누른다. 표시되는 사용 조건은 본인 계정에서 확인한다.
3. Epic Games Launcher → **언리얼 엔진 → 라이브러리 → Fab 라이브러리**에서 새로고침한다.
4. Game Animation Sample의 **프로젝트 생성**을 누르고 UE **5.8**을 선택한다. 최종 프로젝트 폴더가 `C:\PathOfDawn\Samples\GameAnimationSample`이 되도록 지정한다. 이 경로는 새로 선택할 저장 위치이며 현재 확보된 파일 경로라는 뜻이 아니다.

이 샘플은 걷기·정지·회전의 기반 후보다. 생성 후 실제 프로젝트 파일·스켈레톤·리타기팅을 검사해야 하며 현대 의상/기본 인물이 최종 성경 인물로 승인되는 것은 아니다.

사용자가 샘플 다운로드를 보고한 이후에는 전체 소스를 다시 받을 필요가 없다. `Tools/PathOfDawnUnreal/Rebuild/InspectSample.ps1`과 고정 SHA-256의 `inspect_sample.py`만 사용하는 작은 조사 도구를 추가했다. 이미 임포트한 `f7da4aa` 프로젝트를 그대로 유지한다. 저장소 파일을 사용할 때의 명령은 다음과 같다. `-Revision`에는 이 도구가 포함된 **40자리 커밋 SHA**를 지정한다.

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\InspectSample.ps1 -Revision '<40자리 커밋 SHA>' -SampleRoot 'C:\PathOfDawn\Samples\GameAnimationSample'
```

Windows PowerShell 5.1에서도 실행하며 PC 전체 실행 정책을 바꾸지 않는다. 단독으로 내려받은 실행기는 같은 고정 커밋의 작은 Python 파일만 HTTPS로 받아 SHA-256을 확인한다. 원본 `.uproject`는 변경하지 않고 같은 폴더에 임시 설명자를 만들어 Editor Python만 활성화한 뒤 자기 파일을 정리한다. `/Game` 레지스트리를 읽고 최대 6개 메시·12개 애니메이션을 로드해 실제 스켈레톤 참조를 확인한다. 에셋·맵 저장/마이그레이션·리타기팅·빌드·서비스 교체는 수행하지 않는다. Editor가 내부 캐시를 작성할 수는 있다.

각 실행 결과는 기본적으로 `C:\PathOfDawn\Reports\GameAnimationSample\<실행 ID>\sample-inventory.json`과 같은 폴더의 로그에만 남는다. 자동 업로드하지 않는다. 동일 스켈레톤이나 이름에 `Walk`가 있다는 사실은 시각적 품질·복식·리타기팅 승인 근거가 아니다. 이 조사는 `NullRHI`를 사용한 메타데이터 검사이며 **그래픽·애니메이션 재생·게임 실행 성공으로 기록하지 않는다**. Python 계약 검사와 Windows PowerShell 5.1 실행기 검사는 별도의 테스트이며 실제 Unreal 검증은 PC 보고서를 받은 후 구분해 기록한다.

확보한 CC0 환경만 실제 Editor로 가져오는 명령은 다음과 같다. 먼저 Editor 타깃을 컴파일하며, 기존 맵·게임모드·배포를 바꾸지 않는다. **ImportSourcesOnly는 사용자 PC 로그로 성공을 확인했고, ImportJournalData는 아직 미실행**이다.

```powershell
& '.\Import-WordJourney-Sources.cmd' -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -ImportSourcesOnly
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -ImportJournalData
```

`-ImportJournalData`는 직접 작성한 한국어 요약을 `/Game/WordJourney/Narrative/DA_JourneyJournal`로 변환하는 준비 경로다. 모든 `scene_ready`는 false이며 장면을 해금하지 않는다. 기록책 DataAsset 임포트·에셋 재로드·Cook은 미검증이다.

`Import-WordJourney-Sources.cmd`는 바로 아래의 `-ImportSourcesOnly` 명령과 같은 동작이므로 둘 중 하나만 실행한다. `SOURCE_IMPORT_COMPLETE`는 원본 임포트의 성공 상태이며 전체 장면의 `graphicsGate`는 인물/움직임/실제 화면 검수 전까지 BLOCKED다. 독립 원본 임포트에는 미확보 인물 바인딩을 검사해 오류 목록으로 출력하지 않는다.

Unreal 내장 Python과 시스템 Python의 패키지 환경은 분리되어 있다. 현재 임포터는 `WORD_JOURNEY_HOST_PYTHON`으로 지정된 작성 도구용 Python 자식 프로세스에서 Pillow 이미지·캡처 검사를 실행한다. PrepareRebuild가 실제 preflight에 사용한 인터프리터를 에디터 프로세스에만 전달하고 종료 후 복구한다. 엔진 Python에 Pillow를 설치하거나 배포 런타임에 Python 의존성을 추가하지 않는다. 에디터에서 직접 실행할 때 호스트 Python 경로가 없으면 검사를 생략하지 않고 명시적으로 실패한다.

실제 라이선스·인물·애니메이션·팩이 확보되면 템플릿을 `.local/asset-bindings.json`으로 복사해 **실제 조회한** 오브젝트 경로·스켈레톤·애니메이션·실측 배치와 사용 조건 근거를 등록한다. 그 뒤:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Bindings '.\Tools\PathOfDawnUnreal\Rebuild\.local\asset-bindings.json' -GenerateBenchmark
```

이 경로도 생성 결과만으로 통과시키지 않는다. 새 Editor 프로세스에서 실제 환경 전경·인물 근접·플레이 구도와 이동/애니메이션을 검수한다. 생성된 카메라는 구도 확인용이며 아직 플레이 Pawn/AnimBP를 구현한 것이 아니다. 실제 렌더 캡처와 기명 검수 전 상태는 계속 BLOCKED다. 현재 작업에는 도입 컷신, 새 타이틀, 요셉 이동과 실제 장면 연결이 완료되어 있지 않다.

## 배포와 복구

기존 `C:\PathOfDawn\Play-in-Browser.cmd`는 main의 이전 게임을 계속 사용한다. 이 재구축 브랜치를 main에 병합하거나 실행 중인 폴더에 덮어쓰지 않았다. 원래 소스는 기준 커밋 `9ae7fc27c71da0d80941c0acfe4868c28970d81e`로 다시 받을 수 있고 호스트 저장은 버전 폴더 밖에 있다.

새 게임의 실제 그래픽·패키지·소리·입력·저장/재접속 검증 후 기존 BuildDemo/UpdateDemo의 후보 빌드 → 검증 → 서비스 전환 경로를 재사용한다. 현재는 이전 서비스 전환·신규 공개 URL·멀티 사용자 저장을 구현했다고 주장하지 않는다. 새 기록 저장은 호스트의 `WordJourney_v1` 단일 테스트 슬롯이며, 공유 호스트 다중 이용자 운영에는 세션별 UserDir/저장 분리가 추가로 필요하다.

## 사용자 PC에서 확인한 첫 실제 Editor 실행

`f7da4aa9aa85`의 Windows 로그에서 Editor 타깃이 성공했다. JourneyJournalData/Subsystem/Widget 및 Automation 테스트 소스가 실제로 컴파일됐고 Runtime/Editor DLL이 링크됐다. 이어서 12개 텍스처의 Interchange 임포트, 도기 메시 빌드, 총 17개 에셋 저장 후 정상 반환을 확인했다. Source-only 성공 상태는 허용 상태를 검사한 래퍼의 마지막 `Editor report:` 출력으로 확인하며 별도 JSON 자체는 아직 제공받지 않았다. [선별 근거](../Evidence/Rebuild/windows-source-import-f7da4aa.json).

도기 FBX의 스무딩 그룹 경고는 실제 외관 검수 대상이다. 시작 시의 Automation `Condition failed` 15줄과 Pixel Streaming 초기화 오류는 이 실행에서 프로젝트 테스트나 스트리밍을 검증했다는 근거가 아니며 미해결 메시지로 남긴다. 다른 플랫폼의 SDK 안내만으로 Windows 도구를 다시 설치하지 않는다. 전체 장면·UI·패키지·공개 접속은 여전히 미검증이다.
