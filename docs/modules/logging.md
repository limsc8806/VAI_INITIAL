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

# logging_utils.py 모듈 메모

## 핵심 구성요소
- `setup_logging(base_dir, level)`: 루트 로거 초기화, 파일 핸들러(`logs/pipeline.log`) 설정.
- `StageLogger`: 단계 이름별 서브 디렉터리를 생성하고 JSON/Markdown 스냅샷을 저장.
- `stage_logging` 컨텍스트 매니저: 단계 시작/종료 로그와 함께 `StageLogger` 인스턴스를 제공.

## 출력 구조
- `logs/<stage_name>/<timestamp>_<label>.json|md`
- 민감 필드는 `StageLogger.redact_fields`에 따라 `<redacted>`로 치환.
- Stage별로 자동 생성된 로그와 추가 캐시(JSON)는 `data/processed/<run_id>/`에 보관.

## 향후 확장 아이디어
- 로그 압축/보존 주기 설정.
- `stage_logging` 내부 예외 처리에서 실패 스냅샷 자동 저장.
- JSON Schema 기반 검증을 도입해 로그 형식 일관성 확보.

## 갱신 규칙
- 로깅 포맷, 파일명 규칙, 민감 필드 처리 방식 변경 시 반드시 이 문서를 업데이트한다.
