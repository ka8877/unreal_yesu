# 말씀의 여정 — 실제 에셋 확보 기록

2026-11-02 KST. **환경 원본은 사용자 Unreal Editor에서 12텍스처·4재질·1메시 임포트·저장까지 확인했다. 의상·인체 원본은 미조립 상태이며 그래픽 기준 장면은 BLOCKED**다. 아래 원본은 기존 목각형 v8 캐릭터와 별개다. 완성된 탄생 공간·인물·애니메이션을 확보한 것으로 표시하지 않는다. 원본 manifest의 `unreal_import_verified=false`는 취득 당시 동결 기록이며 이후 PC 실행 결과는 [별도 근거](../Evidence/Rebuild/windows-source-import-f7da4aa.json)에 남긴다. 스무딩·재질 외관과 새 프로세스의 참조 재로드 검수는 미완료다.

## 확보한 파일

원본 루트: `SourceArt/PathOfDawnUnreal/Rebuild/Environment/`. 정확한 파일·용도·사용조건·원본 URL·provider MD5·SHA256·이미지 색공간은 `manifest.json`이 관리한다. 메타데이터 응답은 `provenance/*.files.json`, `*.info.json`에 보관했다.

| 실제 확보한 자산 | 출처/저작자 | 포함 파일 | 사용 후보와 확인 상태 |
| --- | --- | --- | --- |
| Stone Wall 05 | [Poly Haven](https://polyhaven.com/a/stone_wall_05), Charlotte Baglioni | 2048² Base Color JPG, DirectX Normal PNG, Roughness JPG | 작은 석조 공간의 표면 후보. 원본 디코딩·체크섬 확인. 건축 메시가 아니다. |
| Brown Mud Dry | [Poly Haven](https://polyhaven.com/a/brown_mud_dry), Rob Tuytel | 동일한 3개 PBR 채널 | 마당 흙바닥 후보. 원본 디코딩·체크섬 확인. 지형 메시가 아니다. |
| Rough Wood | [Poly Haven](https://polyhaven.com/a/rough_wood), Rob Tuytel | 동일한 3개 PBR 채널 | 목재 표면 후보. 원본 디코딩·체크섬 확인. 구유 메시가 아니다. |
| Ceramic Pot | [Poly Haven](https://polyhaven.com/a/ceramic_pot), Aron Łyczek | 원본 FBX와 위 3개 PBR 채널 | 실제 도기 소품. Blender 4.3.2에서 FBX 파싱·UV 확인. 특정 시대의 도기라는 고증 검수는 미완료. |

원본 13개(텍스처 12장·FBX 1개)와 provenance 9개를 합해 **61,740,075 bytes**. 최대 단일 파일은 23,440,260 bytes다. 기존 Git 소스 아카이브에는 실제 파일이 들어가며 LFS 포인터로 제공하지 않는다. 이 수치는 검증 보고서가 포함하지 않는 원본/증거 응답 22개 기준이다.

모든 **자산 자체는 CC0-1.0**이다. [제공자 사용조건](https://polyhaven.com/license)은 자산의 상업적 이용·수정·원본 재배포도 허용한다. 웹사이트 자체의 저작권은 별도이므로 전체 라이선스 HTML은 저장소에 재배포하지 않고 검토한 URL과 원본 응답 SHA256을 `provenance/license-review.json`에 남겼다. Epic/Fab 자료에는 이 CC0 허용을 적용하지 않는다.

Base Color만 sRGB로, Normal/Roughness는 선형으로 설정해야 한다. 노멀은 DirectX 규약이므로 Unreal에서 불필요하게 녹색 채널을 다시 뒤집지 않는다. FBX에는 제공자가 사용하는 EXR 파일 참조가 남아 있을 수 있다. 위에 실제 내려받은 Base Color/Normal/Roughness를 명시적으로 재연결해야 하며, 없는 EXR 경로에 의존해서는 안 된다. 색공간·노멀 압축·스무딩·재질 연결은 실제 Editor에서 아직 확인하지 못했다.

Ceramic Pot 원본을 Blender에서 읽은 결과: 메시 1개, 정점 1,794개, 삼각형 3,592개, UV 레이어 1개, 경계 크기 약 0.656 × 0.502 × 0.372 m. `verification/ceramic-pot-blender-load.json` 참조. 이 파싱은 Unreal에서의 로드·콜리전·외관 성공을 뜻하지 않는다.

## 실행한 검사와 재현

```bash
python3 Tools/PathOfDawnUnreal/Rebuild/fetch_environment.py
python3 Tools/PathOfDawnUnreal/Rebuild/fetch_environment.py --verify-only
python3 Tools/PathOfDawnUnreal/Rebuild/fetch_environment.py --self-test
blender -b --factory-startup --python SourceArt/PathOfDawnUnreal/Rebuild/Environment/verification/validate_source_model.py -- /absolute/path/to/SourceArt/PathOfDawnUnreal/Rebuild/Environment
```

Windows에서는 같은 Python 명령의 `python3`를 실제 설치된 `python`으로 바꾼다. 표준 라이브러리와 기존 art 도구 의존성 Pillow를 사용한다. 초기 실행만 HTTPS 다운로드를 수행한다. 이후 실행은 고정 receipt를 오프라인 검사하며 변경된 사용자 파일은 덮어쓰지 않는다. 새 다운로드는 HTTPS 호스트·파일당 30 MB/총 80 MB 제한·제공자 크기/MD5를 확인한다. 12장 모두 Pillow로 실제 디코딩하고 2048²인지 확인했다.

반복 실행 2회와 `--verify-only` 통과. 실제 원본 복제본에서 정상 원본 허용, 변조 파일 거부, 파일 누락 거부, PBR 채널 누락 거부, 경로 이탈 거부, 미검토 라이선스 거부, 에셋 세트 누락 거부의 **7개 회귀 검사**를 통과했다. 자세한 결과는 `verification/source-integrity-report.json`, `acquisition-regression-report.json`에 있다. `verification/PBR_SourceInspection.jpg`는 내려받은 PBR 채널의 원본 검사표이며 게임 화면이 아니다.

## 실제 확인한 공식 후보와 필요한 사용자 조치

아래 페이지의 제목·응답을 실제 확인했다. 다운로드·라이선스 동의·Editor 로드는 수행하지 않았다. `verification/official-candidates-review.json`에 URL과 확인한 응답 SHA256을 기록했다. 없는 Fab 제품이나 미확인 상품명을 대안으로 지정하지 않는다.

| 확인한 공식 후보 | 사용자 PC에서의 구체적인 확보 방법 | 필요한 이유·제한 |
| --- | --- | --- |
| [Game Animation Sample — Epic Games](https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016) / [UE 5.8 공식 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine) | 본인 Epic 계정으로 Fab의 해당 페이지에 로그인하고 적용 라이선스를 직접 확인한 뒤 라이브러리에 추가한다. Epic Games Launcher의 Fab 라이브러리에서 **UE 5.8용 별도 샘플 프로젝트**를 만든다. 기존 PathOfDawn 프로젝트 폴더를 덮어쓰지 않는다. | 실제 페이지에서 0 KRW 제안 및 UE 5.8 업데이트 항목을 확인했다. 걷기·정지·회전의 기반 후보이며 시대 복식이나 최종 인물을 제공한 것으로 취급하지 않는다. 가져온 후 스켈레톤·플러그인·리타기팅 결과를 먼저 검증해야 한다. 원본 샘플을 공개 GitHub에 복제할 권한은 추정하지 않는다. |
| [MetaHuman Creator in Unreal Engine](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-creator) | Epic Games Launcher → 설치된 UE 5.8의 옵션에서 공식 문서가 요구하는 **MetaHuman Creator Core Data** 여부를 확인한다. 설치·다운로드·필요한 로그인/약관은 본인이 진행한다. 별도 제작 프로젝트에서 MetaHuman Creator를 확인하고 성인 인물을 만든다. | 요셉·마리아의 얼굴·피부·헤어 후보. 현재 에이전트는 사용자 PC/Creator에 연결되지 않았다. Core Data 설치만으로 시대에 맞는 의상과 애니메이션이 해결되지는 않는다. 해당 버전의 공식 지원·조건과 렌더 비용을 실제 PC에서 확인해야 한다. |

마이그레이션할 최종 캐릭터와 애니메이션의 **예정 목적지**는 `/Game/WordJourney/Characters/`와 `/Game/WordJourney/Animations/`다. 현재 존재하거나 로드한 경로라는 뜻이 아니다. 실제 마이그레이션 도구의 Asset Report에서 정확한 오브젝트 경로를 확인한 뒤 benchmark 바인딩에 등록한다.

## 아직 확보되지 않아 막힌 항목

| 차단된 장면 | 실제 필요한 것 | 현 상태 |
| --- | --- | --- |
| 탄생 기준 장면 | 요셉·마리아의 자연스러운 성인 인물, 시대 복식·헤어·스킨, 걷기/정지/회전/대화 대기, 구유 및 목적에 맞는 작은 석조 건축 세트 | **BLOCKED.** 현재 CC0 텍스처와 도기만으로 완성할 수 없다. 적합한 완성 건축 팩·인물 팩의 무료 사용권/파일은 확인되지 않았다. 기존 정적 v8 인물이나 도형으로 대체하지 않는다. |
| 탄생과 목자 방문 | 존중감 있게 연출할 연령에 맞는 아기 에셋, 최소 목자 인물·복식·대기/시선 애니메이션 | **BLOCKED.** 성인 MetaHuman을 축소해서 아기로 만들지 않는다. |
| 열두 살 성전 장면 | 실제 아동 비율의 인물·복식·움직임, 성전 공간과 선생들 최소 인물 | **BLOCKED.** MetaHuman 성인이나 이동 샘플 확보가 아동 확보를 뜻하지 않는다. 탄생 품질 게이트 통과 전 장면 확장도 보류한다. |
| 전체 그래픽 검수 | Unreal 5.8 Editor, 실제 호스트의 라이선스 보유 콘텐츠, GPU 렌더/화면 캡처 연결 | **BLOCKED.** 현재 Linux 클라우드에는 Unreal/GPU/사용자 PC 연결이 없다. |

한국어 폰트와 직접 제작된 기존 환경음은 별도로 존재한다. 품질·맥락을 검수한 항목만 재사용한다. 이 문서는 실제 확보 내용을 기록하며 라이선스 취득, 모델 제작 또는 그래픽 검증을 사용자에게 대신 완료했다고 주장하지 않는다.

## 추가 승인 후 확보한 인물 제작 원본

사용자가 필요한 무료 자산의 직접 확보를 요청해, 계정·결제·약관 대리 동의 없이 공개 배포되는 원본을 추가 조사했다. **최종 성인 캐릭터를 확보한 것은 아니다.** 새 루트는 `SourceArt/PathOfDawnUnreal/Rebuild/CharacterSources/`, 명세는 해당 폴더의 `manifest.json`이다.

| 실제 확보 | 출처·사용조건 | 현 상태와 필요한 수정 |
| --- | --- | --- |
| Donitz의 Monks Robe | [MakeHuman 공식 커뮤니티 팩](https://static.makehumancommunity.org/assets/assetpacks/suits02.html), CC0. `.mhclo`와 `.mhmat` 원본에도 author Donitz / license CC0 명시 | 원본 OBJ, 피팅 데이터, 재질 정의, 4K 기본색/노멀, thumbnail 확보. **저자가 중세 수도복으로 설명하는 원본**이므로 그대로 성경 시대 복식으로 채택하면 안 된다. 디자인 수정·인체 피팅·천 재질·변형 검수에 쓸 수 있는 제작 입력이다. |
| MakeHuman 기본 인체 토폴로지 | [고정 커밋 a8bc2d54](https://github.com/makehumancommunity/makehuman/tree/a8bc2d54ff0ac92e78ff71431b1023eda42bf482), `LICENSE.ASSETS.md`의 CC0 | `base.obj`와 라이선스 원문 확보. **나체 제작용 베이스이며 최종 화면에 노출하지 않는다.** 최종 얼굴·헤어·피부·적절한 의상·검수는 별도다. 성인 완성으로 표시하지 않는다. |
| MakeHuman 기본 리그 정의와 가중치 원본 | 동일한 MakeHuman CC0 자산 규칙. 원본 JSON에 명시된 라이선스 확인 | `default.mhskel`과 `default_weights.mhw` 확보. 리그 정의/가중치 데이터이며 **바인딩된 Unreal SkeletalMesh 또는 플레이 가능한 애니메이션이 아니다.** |

추가 원본 11개 **33,513,725 bytes**, 최대 파일 16,959,094 bytes. 192,511,027-byte 팩 전체를 다운로드하지 않았다. 공식 팩의 정확한 HTTP 206/Content-Range와 ZIP directory를 확인하고 선택한 의상 파일만 부분 수신했다. 성공한 획득 실행의 전송량은 32,272,173 bytes다. 첫 공식 미러가 느려 동일한 ZIP directory 바이트를 반환하는 두 번째 공식 미러로 전환했다. 부분 수신·source checksum 검증을 하지 못하면 전체 팩을 자동으로 내려받지 않고 실패한다.

반복 오프라인 검사와 실제 복제본을 이용한 정상 원본 허용·변조 거부·지원되지 않는 최종 캐릭터 완료 주장 거부·경로 이탈 거부·원본 누락 거부 **5개 검사**를 통과했다. PNG 2장은 실제 4096² 디코딩을 확인했다. Blender 4.3.2에서 의상 OBJ 10,233정점/19,820삼각형, 베이스 OBJ 19,158정점/36,972삼각형과 UV를 실제 읽었다. 리그 정의 163개 bone 및 가중치 JSON을 파싱했다. 인체·의상 조립, 스킨 바인딩·변형, 얼굴·눈·헤어, 발 미끄러짐, UE 리타기팅·애니메이션, 그래픽 검수는 수행하지 않았다.

```bash
python3 Tools/PathOfDawnUnreal/Rebuild/fetch_character_sources.py --verify-only
python3 Tools/PathOfDawnUnreal/Rebuild/fetch_character_sources.py --self-test
blender -b --factory-startup --python SourceArt/PathOfDawnUnreal/Rebuild/CharacterSources/verify_mesh_sources.py
```

제작 데이터만 포함했고 MakeHuman/MPFB addon이나 GPL/AGPL 프로그램 코드를 프로젝트에 복사하지 않았다. MakeHuman의 프로그램 라이선스와 그래픽 자산의 CC0 구분은 함께 보관한 원본 라이선스를 따른다. 공개 GitHub의 원본 재배포 허용은 각 원본의 CC0 근거로 확인했다. 의상 노멀은 **OpenGL**이다. 향후 Unreal용으로 변환한다면 DirectX 규약에 맞게 녹색 채널 처리를 명시적으로 수행해야 하며, 앞서 확보한 Poly Haven DirectX 노멀과 혼동하면 안 된다.

## 추가 검토했지만 완성 인물로 채택하지 않은 후보

| 직접 검토한 후보 | 실제 확인 | 완성 인물 미확보 이유 |
| --- | --- | --- |
| [MakeHuman/MPFB2](https://github.com/makehumancommunity/mpfb2) | [공식 라이선스](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md)가 코드 GPL과 그래픽/출력 CC0를 분리한다. 실제 CC0 기반 메시·리그·의상 원본은 위와 같이 개별 확보했다. | 설치만으로 시대에 맞는 얼굴·헤어·복식·움직임이 자동 완성되는 제품이 아니다. 이번에는 원본 단계까지만 확보했으며, 베이스를 최종 인물처럼 보여 주지 않는다. |
| [MB-Lab](https://github.com/animate1978/MB-Lab) | 실제 [license.txt](https://github.com/animate1978/MB-Lab/blob/master/license.txt)에 코드 GPL3, 데이터베이스와 생성 모델 기본 라이선스 AGPL3가 명시된다. | 상업 이용 금지라는 뜻은 아니지만 CC0로 취급할 수 없다. 배포 조건 검토 없이 데이터베이스나 출력 모델을 기존 프로젝트에 편입하지 않았다. |
| [Adobe Mixamo](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) | 공식 FAQ에서 Adobe ID가 있으면 무료이며 프로젝트에서 캐릭터·애니메이션 사용이 가능하다고 확인했다. | 인증된 계정 세션이 없고 시대에 맞는 완성 인물도 선택·검증하지 못했다. 로그인 대행이나 모델 viewer 추출로 확보하지 않는다. 캐릭터 원본 공개 재배포 권한도 추정하지 않는다. |

검토 응답의 URL·SHA256와 결론은 `CharacterSources/candidate-and-license-review.json`에 남겼다.

### MetaHuman Core Data 자동 설치 확인 결과

[실제 확인한 공식 설치 자료](https://dev.epicgames.com/documentation/en-us/metahuman/getting-started-with-metahuman-creator-in-unreal-engine)는 Launcher의 설치 버전 타일에서 **Launch → Options → MetaHuman Creator Core Data**를 선택하고 프로젝트의 Creator plugin을 활성화하도록 안내한다. 검토한 공식 자료에서 이 컴포넌트를 설치하는 지원 CLI는 확인하지 못했다. 따라서 추측한 엔진 설치 명령·비공식 다운로드 도구·계정 대리 로그인은 만들지 않았다. 현재 클라우드에는 사용자 Windows PC나 Epic Launcher에 접근할 연결도 없다. 실제 Launcher 작업과 필요한 계정 동의는 그 PC에서 수행해야 한다.

추가로 확보한 제작 원본은 위의 탄생·아기·목자·성전 품질 게이트를 자동 통과시키지 않는다. 특히 중세 수도복을 그대로 적용하거나 베이스를 축소해 아기·아동을 만드는 대체는 금지한다.
