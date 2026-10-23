# v8 에셋 목록

실제 활성 원본 33개를 파일·용도·출처·사용 조건·수정 이력·임시 여부·런타임 경로·SHA256와 함께 [AssetManifest.json](AssetManifest.json)에 기록했다. 이 경로는 에디터 가져오기 대상이며 v8 Cook/게임 실행 성공을 뜻하지 않는다.

| ID | 용도 | 임시 |
|---|---|---|
| `IL_Title_Dawn` | 타이틀 배경 | 아니오 |
| `IL_Arrival` | 도입 장면 | 아니오 |
| `IL_Portrait_Jesus` | 예수님 대화 초상 | 아니오 |
| `IL_Portrait_Simon` | 시몬 대화 초상 | 아니오 |
| `IL_Ending_Together` | 함께한 아침 결과 | 아니오 |
| `IL_Ending_Witness` | 호숫가의 증인 결과 | 아니오 |
| `IL_Ending_Departure` | 아직 걷지 않은 길 결과 | 아니오 |
| `SM_Jesus` | 중거리 3D 인물 | 예 |
| `SM_Simon` | 중거리 3D 인물 | 예 |
| `SM_Traveler` | 중거리 3D 인물 | 예 |
| `SM_Boat` | 호숫가 3D 환경 | 아니오 |
| `SM_Net` | 호숫가 3D 환경 | 아니오 |
| `SM_NetPrepared` | 호숫가 3D 환경 | 아니오 |
| `SM_Jar` | 호숫가 3D 환경 | 아니오 |
| `SM_StoneWall` | 호숫가 3D 환경 | 아니오 |
| `SM_Canopy` | 호숫가 3D 환경 | 아니오 |
| `SM_ShoreRock` | 호숫가 3D 환경 | 아니오 |
| `SM_OliveTree` | 호숫가 3D 환경 | 아니오 |
| `SM_ReedClump` | 호숫가 3D 환경 | 아니오 |
| `SM_PathSlab` | 호숫가 3D 환경 | 아니오 |
| `SM_ShoreGround` | 호숫가 3D 환경 | 아니오 |
| `SM_DistantRidge` | 호숫가 3D 환경 | 아니오 |
| `T_LakeNormal` | 잔물결 노멀 | 아니오 |
| `T_ShoreAlbedo` | 모래 표면 색/노멀 | 아니오 |
| `T_ShoreNormal` | 모래 표면 색/노멀 | 아니오 |
| `A_Water` | 환경·효과음 | 예 |
| `A_Wind` | 환경·효과음 | 예 |
| `A_Footstep` | 환경·효과음 | 예 |
| `A_NetRustle` | 환경·효과음 | 예 |
| `F_Korean` | 한국어 UI·자막 | 아니오 |
| `Episode_Galilee` | 서사 제작 원본 | 아니오 |
| `CharactersV8` | 인물 제작 원본 | 예 |
| `EnvironmentV8` | 환경 제작 원본 | 아니오 |

신규 원화·모델·표면 텍스처는 `SourceArt/PathOfDawnUnreal/VisualV8/`를 사용한다. 기존 27개 원본은 v7 ZIP과 해시 비교하여 보존했다. 이전 출처 기록은 [AssetManifestV7.json](AssetManifestV7.json)에 있다.

원화 참조 연속성·시각 검수는 [IllustrationManifestV8.json](IllustrationManifestV8.json), 모델 제작/검사와 남은 품질 범위는 [ArtDirection.md](ArtDirection.md)를 따른다. 생성 이미지 서비스 이용 조건을 적용하며 독점 저작권/CC0를 주장하지 않는다. 알려진 배우나 영화 초상을 참조하지 않았다. 모델과 음향은 직접 제작했다.

한국어 Noto Sans KR는 SIL OFL 1.1이며 기존 `Fonts/LICENSE-Debian-Noto.txt`를 유지한다. 큰 이미지·FBX·blend·WAV·OTF·uasset/umap은 Git LFS 대상이다. 소스 ZIP에는 LFS 포인터가 아닌 실제 파일을 넣는다.

가로 원화는 1672×941로 목표 1920×1080보다 작다. 3D 인물은 양식화된 정적 조형이며 자연스러운 골격 보행·얼굴 리그가 없다. 환경 자산은 새 데모용으로 제작했지만 Unreal 외관·충돌·성능 확인과 사용자 품질 승인은 남아 있다.
