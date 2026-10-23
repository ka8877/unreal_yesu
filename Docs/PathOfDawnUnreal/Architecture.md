# 구현 구조와 상태 소유권

이 문서는 **작성된 소스**를 설명한다. 현재 환경에 Unreal Engine이 없어 UHT/UBT 컴파일, 실제 에디터 자산 생성, Cook, 패키지와 그래픽 실행은 아직 검증하지 못했다. 엔진 독립 코어는 같은 소스를 GCC로 컴파일하여 테스트했다.

## 책임과 데이터 흐름

`SourceArt/PathOfDawnUnreal/Narrative/episode.json`은 대사·선택 표시·출처 메타데이터의 제작 원본이다. 에디터 생성기가 `UDawnNarrativeData`의 `FDawnDialogueNode` 배열로 변환한다. 런타임은 Cook된 `/Game/PathOfDawn/Narrative/DA_DawnNarrative`를 로드하며 원본 JSON, Python, 외부 URL을 읽지 않는다. 한국어는 고정 namespace/key를 가진 `FText`을 사용한다.

`UDawnNarrativeSubsystem`은 GameInstance 수명으로 한 개 존재한다. UMG·플레이어·월드 액터는 이 서브시스템에 의도를 전달하고 변경 알림을 구독한다. `Core/DawnState.h`의 `dawn::Session`이 현재 상태의 유일한 소유자다. UI는 별도 진행 상태를 복제하지 않는다. `FDawnDialogueNode` 조회는 표시용 복사본이다.

`Session`은 현재 `World`, 값으로 복사한 `CP01`·`CP02`, 회귀에 영향받지 않는 `Meta`를 보유한다. World에는 레벨, 노드, 단계, 체크포인트·결과 ID, 안정적 액터 ID별 Transform, 조사 집합, 소지품, 관계, 플래그, 선택 이력·적용 집합이 있다. Actor 포인터와 런타임 객체 이름은 저장하지 않는다. `Player`는 플레이어 Pawn, 그 외 액터는 `DawnId:Net` 형식의 태그로 캡처한다.

게임 규모에 맞춰 체크포인트와 저장 어댑터를 하나의 서브시스템에 합쳤다. 설정은 `UDawnPlayerSettings`/`UGameUserSettings`가 별도로 관리하며 회귀와 새 게임이 수정하지 않는다.

## 서사와 효과

대사 `NextNode`는 DataAsset에서 읽는다. 두 선택의 규칙과 세 결과의 매핑은 이번 데모에 한정해 C++ 코어에서 고정한다. JSON의 효과/조건 메타데이터는 편집자가 규칙을 확인하도록 기록하며 콘텐츠 검증기가 고정 규칙과의 불일치를 거부한다. 임의 명령을 실행하지 않는다. `SetFlag`, `AddItem`, `RemoveItem`, `ChangeRelationship`은 타입이 정해진 코어 효과만 처리하고, 전체 효과 묶음이 유효할 때 한 번에 적용한다.

그물 조사로 밧줄 한 개를 얻으며 다시 조사해도 중복 획득하지 않는다. 세 사물을 조사한 뒤 시몬의 도입 대화를 진행한다. CP01은 모든 조사 상태, 밧줄 1개, 관계 0, 초기 그물 상태를 보존한다. 선택1 A는 밧줄을 소비하고 `NetPrepared=true`, 관계 +1, 공동 작업 기억을 만든다. B는 밧줄을 유지하고 `ShoreClueFound=true`, 물가 기억을 만든다. 선택1 뒤에는 Task 단계로 이동을 허용하고 Net/Stone 상호작용으로 대화를 이어간다. 인물 장면 뒤 시몬에게 직접 돌아가 상호작용하면 CP02를 만든다. 선택2 A는 첫 선택에 따라 Together/Witness다. B는 Task_Departure를 저장하며, Village 상호작용 전까지 결과·마을행 플래그·결과 기억을 기록하지 않는다. 결과마다 머무름/마을행 플래그도 달라진다.

선택은 현재 노드·세대 번호·적용 집합을 모두 검사한다. 같은 UI 입력이 중복 도착해도 두 번째 효과 적용을 거부한다. 일반적인 대사 페이지 넘김과 선택 적용은 구분한다.

## 회귀 트랜잭션

1. 서브시스템이 복원 상태를 잠그고 `OnBeforeRestore`를 알린다. 컨트롤러는 입력, 카메라 전환, Sequencer, 타이머와 진행 중 효과를 정리한다.
2. 코어 세대 번호를 증가시켜 이전 비동기 완료를 무효화한다.
3. 선택한 World 값 복사본을 현재 상태로 대입한다. CP01로 복원하면 이전 경로의 CP02를 제거하여 잘못된 분기로 돌아가지 못하게 한다.
4. `OnRestored`에서 안정적 ID의 Transform과 소품 상태를 복원한다. Meta와 사용자 설정은 보존한다.
5. `OnChanged`로 기억에 따른 대사, UI와 입력을 갱신하고 저장한다.

타이머는 캡처한 `GetGeneration()` 값으로 `FinishScene()`을 호출한다. 세대가 달라진 콜백은 상태를 바꿀 수 없다. `FinishScene`은 이미 본 Scene만 건너뛸 수 있다. 도입은 항상 건너뛸 수 있다. `RepeatText`는 한 개 이상의 결과를 본 경우 원문 대신 표시된다.

## 저장과 복구

`UDawnSaveGame`의 명시적 `SchemaVersion`, `ContentVersion`, `Payload`가 저장된다. Payload는 코어의 경계 검증 가능한 값 직렬화 형식이다. UTF-8 문자열, 컬렉션 개수, 유효한 단계·분기·소지품·체크포인트 구조를 검사하며 FNV-1a 체크섬으로 우발적인 손상을 감지한다. 체크섬은 암호학적 인증 기능이 아니다. 버전 불일치와 손상은 구분하고 유효하지 않은 입력은 기존 메모리 상태를 바꾸지 않는다.

현재 SchemaVersion=1, ContentVersion=2다. 이전 콘텐츠 버전은 원본을 보존하며 거부한다. 슬롯 이름은 저장 형식 버전을 뜻하므로 변경하지 않았다. 현재 슬롯은 `PathOfDawn_Progress_v1`, 백업은 `_Backup`, 쓰기 검증용은 `_Pending`이다. 저장 전 기존 슬롯을 검증하고, 새 Pending 쓰기/재로드 검증 → 정상 기존 슬롯의 Backup 보관 → Main 쓰기/재로드 검증 순으로 진행한다. 동기 저장 잠금으로 겹친 저장을 막는다. Main 쓰기 실패 시 기존 정상 객체로 복원을 시도하며, 실패를 UI에 알린다. Unreal SaveGame API를 이용한 다단계 보존이며 OS 수준의 원자적 rename을 보장한다고 주장하지 않는다.

저장 성공·실패 알림은 내부 저장 트랜잭션이 반환하고 `bSaving` 잠금이 해제된 뒤 한 번 발생한다. 자동 저장과 메뉴의 수동 저장 모두 같은 경로를 사용하므로, 디스크 오류가 나도 입력 갱신이 저장 중 상태에 고정되지 않는다. 상태 변경의 첫 알림은 소품·월드를 갱신하며 그 뒤 실제 Transform을 캡처한다. 저장 후 알림은 잠금 해제와 오류 표시를 반영한다. 현재 `OnChanged` 구독자는 월드·UI·입력 갱신만 수행하고 저장을 재호출하지 않는다. 이 생명주기 변경은 소스 검토로 확인했으며 실제 디스크 오류 상황의 Unreal 입력 검증은 미실행이다.

손상·버전 불일치 Main이 있으면 자동 덮어쓰기를 잠근다. 사용자가 명시적으로 백업 복구를 선택하면 기존 Main 바이트를 UTC 시각과 GUID가 있는 `_Rejected_...` 슬롯으로 보관하고 유효한 Backup을 복구한다. 정상 Backup이 없으면 원본은 그대로 두고 오류를 표시한다. 정상 Main에 읽기 권한이 없어 보관할 수 없는 경우 복구를 중단한다.

실제 저장 경로는 실행 시 `FPaths::ProjectSavedDir()/SaveGames`를 로그에 출력한다. Windows 기본 사용자 경로 또는 런처에서 제공한 독립 `-UserDir` 아래에 놓인다. 빌드 폴더를 바꿔도 같은 UserDir를 사용해야 이어하기가 유지된다. Pixel Streaming에서는 게임 호스트 디스크에 저장되며 브라우저 localStorage를 사용하지 않는다. 수동 초기화는 게임을 종료한 뒤 해당 슬롯 파일을 먼저 별도 보관하고 제거한다. 설정 파일은 별개다.

새 게임은 진행·체크포인트를 초기화하고 기존 기억을 유지한다. 기억 초기화는 별도 확인 동작이며 현재 진행을 초기화하지 않는다.

## 실제 검증 범위

동일한 `DawnState.h`에 대해 GCC 14.2, C++17, `-Wall -Wextra -Werror -pedantic`으로 479개 검증을 실행했다. 네 선택 조합, 세 결과, 중복 선택, CP01/CP02 값 복원, Transform, 이전 분기 제거, 세대 무효화, Meta 유지, 확인된 기억 초기화, 디스크 바이트 저장 후 새 Session 로드, 손상·버전·의미상 불가능한 저장 거부를 포함한다. Unreal의 `check(...)` 매크로와 충돌하지 않는 컴파일도 검사한다.

ASan/UBSan 실행은 통과했다. 이 컨테이너의 ptrace 조건에서 LeakSanitizer 자체가 실패해 `ASAN_OPTIONS=detect_leaks=0`으로 재실행했다. 메모리 누수 검증은 포함하지 않는다.

Unreal Automation 테스트 `PathOfDawn.Core.BranchesAndRewind`, `PathOfDawn.SaveGame.MemoryRoundtrip`도 작성했다. USaveGame 메모리 직렬화 경계를 검증하지만 엔진이 없어 실행하지 못했다. Windows 실제 종료·재실행 이어하기, 디스크 저장 실패, UMG 포커스, 월드/Sequencer 정리는 패키지 테스트에서 검증해야 한다.

기억만 초기화할 때는 World 세대 번호를 유지한다. 도입 중 메뉴에서 기억을 지운 뒤에도 이미 예약된 도입 완료/원화 전환 콜백이 유효해야 한다. 실제 World 회귀·새 게임·이어하기는 세대 번호를 갱신한다.

Task에서는 대사 넘기기로 진행할 수 없으며 목표 액터만 200cm 범위·시야 검사 후 E로 상호작용한다. 저장·회귀는 Task 노드와 위치를 함께 복원한다. 그물 외형은 NetPrepared와 현재 Task 완료 여부로부터 표시하고 독립 상태를 갖지 않는다. 이미 본 사건 건너뛰기도 Task_ReturnToSimon으로 돌아온다.
