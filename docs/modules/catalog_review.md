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

# catalog.py & review.py 모듈 메모

## catalog.py
- `build_catalog(requirements, schema_version)`  
  - 요구사항 리스트를 받아 `schema_version`, `requirement_units`, `metadata.total_units`로 구성된 딕셔너리를 반환합니다.
- `write_catalog(catalog, output_path)`  
  - YAML 파일(`artifacts/catalog.yaml` 기본)을 생성하며 UTF-8로 저장합니다.

### 향후 과제
- 스키마 정의(JSON Schema/pydantic)를 도입해 구조 검증 강화.
- 요구사항 필드 확장 시 `metadata`에 confidence 분포 등 집계 정보 추가.

## review.py
- `build_review_document(requirements, include_traceability=True, metadata=None)`  
  - DV 리뷰어 및 확장 시스템이 활용할 수 있도록 `metadata`, `summary`, `requirements` 섹션을 갖춘 YAML 문서를 생성합니다.
- `write_review(review_payload, output_path)`  
  - YAML 파일(`artifacts/review.yaml`)로 직렬화합니다.

### 향후 과제
- 도메인별 섹션/템플릿 (`## Interface`, `## Timing` 등) 자동 구성.
- 요구사항별 체크리스트, 리뷰 상태 컬럼 등 부가 정보 추가.
- 리뷰 YAML을 소비하는 외부 시스템 사양과 정합성을 검증할 자동 테스트 작성.

## 갱신 규칙
- 출력 YAML 스키마가 바뀌면 `docs/usage.md`, `README.md`, `docs/schemas/requirement_unit.md`를 함께 업데이트합니다.
- `catalog.yaml`/`review.yaml`에 command 또는 호환성 정보가 추가되면 `commands.py` 메모도 갱신해야 합니다.
