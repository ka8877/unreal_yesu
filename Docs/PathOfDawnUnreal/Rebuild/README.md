# 말씀의 여정 — 재구축 작업 현황

2026-11-02 KST. **현재는 제작 원본·독립 시스템 준비 단계이며, 새 게임의 실제 플레이 빌드가 아니다. 그래픽 기준 장면은 BLOCKED다.**

기존 `9ae7fc27c71d` 버전은 복구 기준으로 보존했다. `rebuild/word-journey-luke2`는 새 작업 브랜치다. 현재 시작 맵·GameMode·Cook·Pixel Streaming·자동 업데이트의 main 경로를 바꾸지 않았다. 기존 사용자의 저장과 실행 중인 PC 프로세스에 접근하지 않았다. 과거 로그에서 Windows 패키징과 스트리밍 시작이 끝났지만 실제 브라우저 영상·음성·입력 증거는 없다. 확인된 주소는 사용자 PC의 `http://127.0.0.1:8080/`이며 공개 인터넷 주소가 아니다.

## 실제로 추가한 것

- Poly Haven의 CC0 돌·흙·목재 2K PBR과 스캔 도기 FBX 원본. [자산·사용 조건·원본 검사](AssetAcquisition.md). 실제 파일은 `SourceArt/PathOfDawnUnreal/Rebuild/Environment/`에 있다.
- 추가로 MakeHuman의 CC0 인체·리그 정의와 Donitz 의상 제작 원본 약 34MB를 `CharacterSources/`에 확보했다. OBJ/UV는 Blender에서 읽었지만 조립된 성인·UE 리그·애니메이션이 아니다. 원래 의상은 중세 수도복이므로 1세기 복식으로 그대로 사용하지 않으며 디자인 수정과 검수가 필요하다. 아기·아동의 대체재로 사용하지 않는다.
- 누가복음 2:1–7, 8–20, 41–52의 한국어 요약·사건 메타데이터. [출처와 생략 범위](Narrative.md). 2:21–40은 체험·완료한 사건으로 기록하지 않는다.
- C++ `JourneyJournal.h`: 빈 기록 → 사건 체험 → 기록 해금 → 사용자 기록 확정, 중복/지연 콜백 방지, 체크포인트 복원 검증. 대체 결말·시간 회귀가 없다.
- Unreal `JourneyJournalData`, `JourneyJournalSubsystem`, `JourneySaveGame`, `JourneyJournalWidget`: 런타임 DataAsset, 별도 저장, 미래 내용 비공개, UMG 기록책과 입력 잠금. **UHT/Unreal 컴파일과 화면은 미검증**이다. 기존 게임에는 연결하지 않았다.
- 실제 Editor API를 사용하는 환경 임포터·고품질 원본 World 복제 기반 기준 장면 생성 경로. 필수 인물이 없으면 맵 생성 전에 차단한다. 기존 v8 인물·도형·성인 축소 아동을 대체재로 허용하지 않는다.
- 읽기 전용 PC 에셋 진단과 공식 무료 샘플 준비 도구. Epic 로그인·약관과 유료 구매를 자동 처리하지 않는다.

## 품질 게이트와 막힌 항목

| 단계 | 상태 | 근거 |
| --- | --- | --- |
| 조사·복구 기준 보존 | SOURCE_DONE | 브랜치/기준 커밋, `Evidence/Rebuild/environment.json` |
| 원본 환경 확보 | SOURCE_VERIFIED | 실제 13개 원본·체크섬·12장 디코딩, 도기 Blender 로드 |
| 자연스러운 인물·복식·이동·완성 공간 | BLOCKED | 승인된 성인·아기·목자·애니메이션·건축 팩 미확보 |
| Unreal 그래픽 기준 장면 | BLOCKED | 이 작업 환경에 Unreal/GPU/Windows PC 연결 없음 |
| 탄생부터 첫 기록까지 플레이 | NOT_IMPLEMENTED | 그래픽 기준 장면 이후 연결할 단계. 독립 기록책 소스만 준비됨 |
| 열두 살 성전 확장 | BLOCKED | 탄생 검수 및 연령에 맞는 아동·성전 에셋 선행 필요 |
| 새 빌드·URL 교체 | NOT_RUN | 새 맵/Cook/패키지/미디어·공개 접속 검증 없음 |

목표 8–12분은 플레이 시간 목표이며 측정 결과가 아니다. 실제 게임 캡처와 새 Windows ZIP은 없다. 환경 원본 검사표와 Blender 로드 보고서는 게임 캡처로 제출하지 않는다. 구체적인 필수 역할은 [AssetRequirements.json](AssetRequirements.json), 미입력 바인딩은 `Tools/PathOfDawnUnreal/Rebuild/asset-bindings.example.json`에 있다. 미확보 경로는 의도적으로 `null`이다.

## 재현한 소스 검사

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\TestRebuild.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1
```

첫 명령은 Linux GCC 또는 Windows Developer PowerShell의 MSVC와 Python/Pillow를 사용한다. C++ 132 assertions, 서사 오류 주입 24개, 환경 변조 검사 7개, 인체/의상 원본 변조 검사 5개, 임포트·에셋 정책 17개를 통과했다. 두 번째는 준비 상태를 검사하며 현재 **정상적으로 BLOCKED/종료 코드 2**가 된다. 성공으로 무시하지 않는다. 로그와 JSON은 `Docs/PathOfDawnUnreal/Evidence/Rebuild/`에 있다. 이 검사는 Unreal 컴파일·저장 파일 I/O·셰이더·UMG·그래픽 품질을 검증하지 않는다.

GitHub의 [소스 검사](https://github.com/ka8877/unreal_yesu/actions/runs/41394929229)와 [실제 Windows 실행기 검사](https://github.com/ka8877/unreal_yesu/actions/runs/41394929081)도 통과했다. 후자는 PowerShell 7/Windows PowerShell 5.1 부모 실행기의 파일 핸들·프로세스 유지·로그 수집 검증이며 Unreal 게임 실행이 아니다. 결과는 `Evidence/Rebuild/ci.json`에 있다.

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

확보한 CC0 환경만 실제 Editor로 가져오는 명령은 다음과 같다. 먼저 Editor 타깃을 컴파일하며, 기존 맵·게임모드·배포를 바꾸지 않는다. **현재 클라우드에서는 실행하지 못한 명령**이다.

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -ImportSourcesOnly
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -ImportJournalData
```

두 번째는 직접 작성한 한국어 요약을 `/Game/WordJourney/Narrative/DA_JourneyJournal`로 변환하는 준비 경로다. 모든 `scene_ready`는 false이며 장면을 해금하지 않는다. 실제 임포트·에셋 재로드·Cook은 미검증이다.

실제 라이선스·인물·애니메이션·팩이 확보되면 템플릿을 `.local/asset-bindings.json`으로 복사해 **실제 조회한** 오브젝트 경로·스켈레톤·애니메이션·실측 배치와 사용 조건 근거를 등록한다. 그 뒤:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\PathOfDawnUnreal\Rebuild\PrepareRebuild.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Bindings '.\Tools\PathOfDawnUnreal\Rebuild\.local\asset-bindings.json' -GenerateBenchmark
```

이 경로도 생성 결과만으로 통과시키지 않는다. 새 Editor 프로세스에서 실제 환경 전경·인물 근접·플레이 구도와 이동/애니메이션을 검수한다. 생성된 카메라는 구도 확인용이며 아직 플레이 Pawn/AnimBP를 구현한 것이 아니다. 실제 렌더 캡처와 기명 검수 전 상태는 계속 BLOCKED다. 현재 작업에는 도입 컷신, 새 타이틀, 요셉 이동과 실제 장면 연결이 완료되어 있지 않다.

## 배포와 복구

기존 `C:\PathOfDawn\Play-in-Browser.cmd`는 main의 이전 게임을 계속 사용한다. 이 재구축 브랜치를 main에 병합하거나 실행 중인 폴더에 덮어쓰지 않았다. 원래 소스는 기준 커밋 `9ae7fc27c71da0d80941c0acfe4868c28970d81e`로 다시 받을 수 있고 호스트 저장은 버전 폴더 밖에 있다.

새 게임의 실제 그래픽·패키지·소리·입력·저장/재접속 검증 후 기존 BuildDemo/UpdateDemo의 후보 빌드 → 검증 → 서비스 전환 경로를 재사용한다. 현재는 이전 서비스 전환·신규 공개 URL·멀티 사용자 저장을 구현했다고 주장하지 않는다. 새 기록 저장은 호스트의 `WordJourney_v1` 단일 테스트 슬롯이며, 공유 호스트 다중 이용자 운영에는 세션별 UserDir/저장 분리가 추가로 필요하다.
