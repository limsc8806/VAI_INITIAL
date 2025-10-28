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
