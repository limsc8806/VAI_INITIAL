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

# commands.py 모듈 메모

## 핵심 역할
- `catalog.yaml`에 기록된 요구사항의 `commands` 리스트를 추출·정규화합니다.
- 텍스트 청크에서 command 토큰을 찾아 요구사항 객체에 자동으로 주입합니다.
- 텍스트 흐름을 분석해 command 연속 실행 호환성(`compatibility_matrix`)을 추정하고 CSV로 내보냅니다.

## 주요 함수
- `extract_commands_from_catalog(...)`, `_normalize_command_entry(...)`  
  `catalog.yaml`에 이미 정의된 command 항목을 표준 딕셔너리 형태로 변환합니다.
- `find_command_tokens(...)`, `find_commands_in_text(...)`  
  정규식 패턴 목록을 기반으로 텍스트 안의 command 토큰을 탐지합니다.
- `annotate_requirements_with_commands(requirements, chunked_texts, patterns, max_per_requirement)`  
  청크 텍스트에 등장한 command를 요구사항의 `commands` 필드에 채웁니다.
- `infer_compatibility_from_chunks(chunked_texts, patterns, ...)`  
  command 토큰 순서를 바탕으로 선행→후속 관계를 추정하고 `Y/N` 상태를 기록합니다.
- `extract_compatibility_mapping(...)`, `build_sequential_compatibility_table(...)`, `write_compatibility_csv(...)`  
  catalog에 포함된 호환성 정보를 읽어 상삼각 테이블을 만들고 CSV 파일로 직렬화합니다.

## 설정 항목
`configs/default.yaml` 하위 `commands` 블록으로 제어합니다.

- `patterns`: command를 인식할 정규식 목록  
  기본값에는 `CMD_*` 외에 DDR5 명령으로 자주 쓰이는 `MRW/MRR`, `ACT`, `PRE`, `REF*`, `READ/WRITE/RD/WR`, `NOP`, 전력/리프레시 관련 `PDE/PDX/SRE/SRX/RFM`, `MPC`, `ZQ*` 등이 포함되어 있습니다.
- `max_per_requirement`: 요구사항당 저장할 최대 command 수
- `sequence_positive_keywords`: 긍정적 순차 관계를 암시하는 연결어(예: `->`, `then`, `after`)
- `sequence_negative_keywords`: 금지 관계를 나타내는 표현(예: `must not follow`)
- `compatibility_default`: 명시되지 않은 조합의 기본 상태 (`UNKNOWN` 등)
- `compatibility_description`: 자동 생성되는 호환성 매트릭스의 설명 문구
- `target_requirement_index`: 호환성 매트릭스를 저장할 요구사항 인덱스(기본 0)
- `compatibility_csv_path`: CSV 산출물 경로

## 향후 확장 아이디어
- command 탐지 시 도메인 사전이나 LLM 보조를 결합해 오탐/누락을 줄이기.
- command 항목에 파라미터, 프리컨디션 등 구조화 필드를 자동으로 채우는 규칙 추가.
- 호환성 그래프를 시각화하여 리뷰 리포트나 대시보드에 연동.
