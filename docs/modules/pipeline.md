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

# pipeline.py 모듈 메모

## 핵심 역할
- 설정을 로드하고 실행 컨텍스트(`run_id`, 캐시 디렉터리 등)를 구성합니다.
- 추출 → 청킹 → LLM 요약 → 요구사항 생성 → 산출물 출력까지 전체 파이프라인을 오케스트레이션합니다.
- 각 단계에서 `StageLogger`로 JSON/Markdown 스냅샷을 남기고, `data/processed/<run_id>/`에 중간 데이터를 캐시합니다.

## 주요 함수
- `run_pipeline(config_path, pdf_path)` : 엔드투엔드 실행 진입점.
- `ensure_pdf_path(...)` : 명령행/설정값을 조합해 PDF 경로 확정.
- `build_run_context(...)` : 실행별 캐시 폴더와 ID 생성.
- `cache_json(...)` : 단계 출력물을 JSON으로 저장.
- `main()` : CLI 진입점 (`scripts/run_pipeline.py` 재사용).

## 단계별 로그 정책
1. **01_extraction** – PyMuPDF/pdfplumber/Camelot으로 텍스트·표·그림 추출.
2. **02_chunking** – 추출 아티팩트를 병합하고 청킹 결과 기록.
3. **03_llm_summarization** – LLM 요약 결과 저장(민감 필드 마스킹 가능).
4. **04_requirements** – 요구사항 단위를 생성하고 패턴 기반 command 탐지 및 호환성 매트릭스 자동 추정.
5. **05_outputs** – 최종 산출물(`catalog.yaml`, `review.yaml`, `compatibility_matrix.csv`) 경로와 메타데이터 기록.

## command 처리 흐름
- `commands.patterns` 설정에 따라 청크 텍스트에서 command 토큰을 감지합니다.
- 감지된 command는 요구사항의 `commands` 필드에 채워지고, 텍스트 순서를 분석해 호환성 매트릭스(`compatibility_matrix`)를 추정합니다.
- 추정된 매트릭스는 `catalog.yaml` 및 CSV 산출물로 기록됩니다.

## 업데이트 시 주의
- 단계 이름이나 로그 구조가 변경되면 `docs/modules/logging.md`와 TODO 목록도 함께 수정하세요.
- 새로운 파이프라인 단계가 추가될 경우 이 문서를 즉시 업데이트하고 `StageLogger` 사용 여부를 명시하세요.
