# 말씀의 여정: 누가복음 2장과 기록책

이번 재구축은 기존 갈릴리 창작 분기의 연장이 아니다. 새 서사 원본은 `SourceArt/PathOfDawnUnreal/Rebuild/Narrative/journey.json`이며 기존 `episode.json`은 보존한다. Unreal에 가져올 DataAsset이 생성될 때도 이 JSON이 제작 원본이다. 패키지의 일반 플레이에서 소스 JSON을 읽는 구조로 사용하지 않는다.

## 사건 범위

| 안정 ID | 출처 | 요약하는 사건 | 기록 조건 | 실제 장면 상태 |
|---|---|---|---|---|
| Birth | 누가복음 2:1–7 | 등록을 위해 베들레헴으로 간 요셉과 마리아, 탄생과 구유 | 장면 체험 뒤 사용자가 기록하기 | BLOCKED |
| Shepherds | 누가복음 2:8–20 | 목자들이 들은 소식과 방문, 마리아가 마음에 간직함, 목자들의 귀환 | Birth 기록 후 방문 체험, 사용자가 기록하기 | BLOCKED |
| Temple | 누가복음 2:41–52 | 열두 살 예수, 돌아가 찾은 부모, 성전의 선생들, 나사렛 귀환 | 명시적 시간 전환 뒤 성전 장면 체험, 사용자가 기록하기 | BLOCKED |

2026-11-02에 [USCCB 누가복음 2장](https://bible.usccb.org/bible/luke/2)을 실제로 읽어 사건 순서와 장절을 확인했다. 참조 페이지 응답의 SHA256과 조회 방법은 `SourceArt/PathOfDawnUnreal/Rebuild/Narrative/source-check.json`에 남겼다. 해당 사이트의 영문 번역과 해설을 게임에 복사하지 않았다. 게임 본문은 직접 작성한 한국어 요약(`ScriptureSummary`)이며, 직접 인용(`DirectQuotation`)을 사용하지 않는다. 플레이 안내와 시간 이동 안내는 `GameGuide`로 구분한다. 다른 복음서의 동방박사·별·이집트 피신 등을 같은 장면에 섞지 않는다.

누가복음 2:21–40에 나오는 이름을 지은 일, 성전에 데리고 간 일과 시므온·안나의 만남, 나사렛 귀환·성장은 이번 세 사건 사이에서 **플레이하지 않는 범위**다. 시간 전환 안내에서 생략을 알리며 체험·완료한 기록으로 추가하지 않는다. 본문에 없는 성장 퀘스트·어린 시절 기적·가상 설교·다른 결말은 없다.

구유가 놓인 공간의 건물 형태, 정확한 인물 외모와 인원, 조작 동선은 시각적·게임적 각색이다. 여관 주인이나 동굴·마구간이 누가복음 본문에 명시되었다고 단정하지 않는다. 기록책은 실제 성경 집필 과정을 재현하는 설정이 아니다.

## 상태와 저장 계약

`Core/JourneyJournal.h`가 기록 상태를 소유한다. 기록은 Locked → Available → Written 순서로 변한다. 새 게임의 책은 비어 있고, Locked 항목은 UI의 `VisibleEntries()`에 반환되지 않는다. 체험이 해금만 수행하고 사용자의 별도 `Write()`가 기록을 확정한다.

진행 경로는 Arrival → BirthWitnessed → BirthRecorded → ShepherdsWitnessed → BirthChapterComplete → TempleArrival → TempleWitnessed → TempleRecorded → Complete다. BirthChapterComplete 이전의 시간 전환, TempleArrival만으로 성전 기록 해금, 마지막 기록 전 데모 완료를 거절한다. 건너뛰기와 정상 재생은 같은 `Experience()`를 호출하며 현재 epoch와 사건 순서를 함께 검사한다. 이 때문에 중복 종료 알림과 지난 장면의 지연 콜백이 다음 사건을 완료할 수 없다.

저장용 값 스냅샷에는 SchemaVersion=1, ContentVersion=1, started, 안정 체크포인트 ID, 체험한 사건 ID 집합과 작성한 기록 ID 집합이 들어간다. 각 체크포인트에서 허용되는 집합을 정확히 검사한 뒤 한 번에 복원한다. 버전 불일치·알 수 없는 ID·미래 기록·이전 기록 누락을 거절하면 현재 상태와 epoch를 유지한다. 기존 갈릴리 SaveGame과 별도 슬롯을 사용해야 한다. 이 코어 자체는 디스크 저장이나 사용자별 세션 저장을 구현하지 않는다.

## 실제 실행한 검사

```bash
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -I Games/PathOfDawnUnreal/Source/PathOfDawnUnreal/Core \
  Tools/PathOfDawnUnreal/Rebuild/test_journey_journal.cpp \
  -o /tmp/test_journey_journal
/tmp/test_journey_journal
python3 Tools/PathOfDawnUnreal/Rebuild/validate_journey.py --self-test
```

C++ **132 assertions 통과**. 빈 책, 미래 항목 차단, 명시적 기록, 중복 재생·건너뛰기, 지연 콜백 무효화, 장 전환 조건, 모든 안정 체크포인트의 새 인스턴스 복원, 스냅샷 값 독립성, 손상·버전 불일치 시 현 상태 보존, 새 게임 초기화를 검사했다. 메타데이터 검사는 **24개 오류 주입을 모두 거절**했다.

이 결과는 실행한 순수 C++·JSON 검사다. Unreal 컴파일, USaveGame 파일 저장·프로세스 재실행, 실제 장면 재생, 시각적 품질 검토는 이 검사에 포함되지 않는다. 현재 세 장면은 전부 BLOCKED이며 실제 플레이 완료로 표시할 수 없다. 주요 성인·아기·아동·의상·리깅·애니메이션과 탄생 기준 공간을 확보하고 실제 Unreal 렌더링 검수를 통과해야 다음 단계로 진행할 수 있다.
