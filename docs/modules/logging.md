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
