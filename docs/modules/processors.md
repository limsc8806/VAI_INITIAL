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

# processors.py 모듈 메모

## 책임
- 추출된 텍스트/표/그림 데이터를 `Chunk` 데이터클래스로 래핑하여 페이지/타입 기준으로 정렬합니다.
- 청킹(`chunk_text`)을 통해 요구사항 후보 텍스트 블록을 생성합니다.
- LLM 요약 결과와 결합해 최종 요구사항 단위(`build_requirements`)를 구성합니다.

## 주요 데이터 흐름
1. `merge_artifacts`  
   - 입력: 추출 결과 리스트  
   - 출력: `Chunk` 리스트 (정렬된 페이지 순)
2. `chunk_text`  
   - 입력: `Chunk` 시퀀스, `max_characters`, `overlap_characters`  
   - 출력: `{"text": str, "metadata": {...}}` 딕셔너리 리스트
3. `build_requirements`  
    - 입력: 청크 리스트, LLM 요약 리스트  
    - 출력: 요구사항 단위 리스트(스키마 필수/선택 필드 모두 포함)
    - 모든 요구사항 객체는 docs/schemas/requirement_unit.md에 정의된 스키마에 따라 정규화/검증됨
    - 필수(`id`, `title`, `description`) 및 선택(`source_pages`, `evidence`, `commands`, `tags`, `dependencies`, `confidence`, `validation_status`, `notes`, `compatibility_matrix`) 필드가 누락 시 기본값으로 채워짐
    - 타입 불일치 시 자동 변환(예: float, list, dict 등)
    - 스키마 변경 시 반드시 이 로직과 문서 동기화 필요

## 향후 개선 사항
- 청킹 로직에 표/그림 요약 포함 여부 결정.
- `metadata` 내 `kinds`를 더 풍부한 정보(비율, confidence)로 확장.
- 요구사항 스키마를 별도 파일로 정의하고 pydantic 검증을 추가.

## 갱신 규칙
- `Chunk` 구조나 요구사항 YAML 포맷이 변할 경우 `catalog.yaml`, `review.yaml` 관련 문서도 함께 업데이트합니다.
