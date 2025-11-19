# 문서/스키마/출력 구조 변경 시 규칙

1. 코드, 스키마, 산출물 구조가 변경될 때는 반드시 아래 문서들을 함께 수정해야 합니다.
  - README.md
  - docs/usage.md
  - docs/schemas/requirement_unit.md
  - docs/modules/pipeline.md, processors.md, llm.md, extractors.md, catalog_review.md, commands.md, logging.md 등
  - TODO.md, project_report.md
2. 산출물(`catalog.yaml`, `review.yaml`, `compatibility_matrix.csv`) 구조가 바뀌면 관련 스키마 문서와 테스트 코드도 동기화해야 합니다.
3. 요구사항 단위 스키마(pydantic/JSON Schema)는 항상 docs/schemas/requirement_unit.md에 최신 상태로 유지합니다.
4. 파이프라인 단계, 로그 구조, 민감 필드 처리 방식이 바뀌면 logging.md와 관련 모듈 문서도 즉시 갱신합니다.
5. CI/테스트/자동화 정책이 바뀌면 TODO.md와 project_report.md에 반영합니다.
6. 모든 문서는 한글로 작성하며, 변경 시 반드시 변경 이력을 남깁니다.

# VAI_PLAN

VAI_PLAN은 JEDEC DDR5 사양서(JESD79-5 등)에 포함된 텍스트·표·그림을 추출하여 DV 엔지니어용 커버리지 초안(`catalog.yaml`)과 검증 테스트 플랜 입력(`review.yaml`)을 생성하는 로컬 파이프라인입니다. LLM 요약을 결합하되, 모든 중간 산출물을 기록해 검증 가능성과 추적성을 확보하는 데 목적을 둡니다.

## 구성 요소

- `src/`
  - `vai_plan/pipeline.py`: 파이프라인 엔진, 단계별 조립과 로그 기록
  - `vai_plan/extractors.py`: PDF 텍스트·표·이미지 추출 래퍼(현재 스텁)
  - `vai_plan/processors.py`: 추출 데이터를 요구사항 단위로 병합/청킹
  - `vai_plan/llm.py`: LLM 요약 호출 스텁 및 마스킹 유틸
  - `vai_plan/catalog.py`: `catalog.yaml` 생성기
  - `vai_plan/review.py`: `review.yaml` 생성기
  - `vai_plan/commands.py`: command 리스트 및 호환성 CSV 추출 유틸
  - `vai_plan/logging_utils.py`: 단계별 로깅/스냅샷 지원
- `configs/`: 파이프라인 설정 (`configs/default.yaml` 등)
- `data/raw/`: 입력 DDR5 PDF
- `data/processed/`: 실행별 중간 산출물(JSON 캐시)
- `artifacts/`: 최종 결과 (`catalog.yaml`, `review.yaml`, `compatibility_matrix.csv`)
- `logs/`: `pipeline.log`와 단계별 JSON/Markdown 로그
- `docs/`: 설계 문서, 모듈 메모, 스키마 정의
- `tests/`: 단위 테스트 모음

## 빠른 시작

1. Python 3.10 이상 가상환경을 준비합니다.
2. `pip install -r requirements.txt`
3. 분석할 DDR5 PDF를 `data/raw/`에 배치합니다.
4. 아래 명령으로 파이프라인을 실행합니다.
