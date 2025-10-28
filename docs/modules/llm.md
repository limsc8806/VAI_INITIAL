# llm.py 모듈 메모

## 핵심 역할
- 청킹된 텍스트를 요약하기 위해 LLM을 호출하고, 결과를 요구사항 단위에 맞는 구조로 변환합니다.
- OpenAI Chat Completions API를 기본 타겟으로 하며, 환경 변수에 API 키가 없거나 라이브러리가 설치되지 않은 경우 스텁 요약으로 자동 대체합니다.
- 요약 결과에는 `title`, `description`, `source_pages`, `confidence`, `evidence`, `llm_prompt`, `llm_response` 등을 포함합니다.

## 주요 함수
- `summarize_chunks(chunked_texts, config)`  
  - LLM 호출 여부를 판단하고 실제 요약 또는 스텁 요약을 수행합니다.
- `_summarize_with_openai(...)`  
  - `openai` 패키지를 이용해 Chat Completions API를 호출합니다.  
  - `config.api_key_env`(기본 `OPENAI_API_KEY`)에 지정된 환경 변수에서 키를 읽습니다.
- `_parse_llm_response(...)`  
  - LLM 응답을 JSON으로 파싱하고, 실패 시 텍스트를 그대로 설명으로 사용합니다.
- `_fallback_summaries(...)`  
  - 외부 호출이 불가할 때 기존 스텁 요약을 생성합니다.
- `redact_terms(text, terms)`  
  - 민감 단어를 `[REDACTED]`로 치환하기 위한 유틸리티.

## 설정 키 (`configs/default.yaml`)
- `provider`: 기본 `openai`. 다른 값은 현재 스텁 동작.
- `model`: 예) `gpt-4o-mini`.
- `api_key_env`: API 키가 저장된 환경 변수명 (기본 `OPENAI_API_KEY`).
- `api_base`: 필요 시 OpenAI 호환 엔드포인트 URL.
- `system_prompt`, `user_prompt_template`: 프롬프트 커스터마이징 문자열.
- `temperature`, `max_tokens`: 생성 파라미터.
- `enable_summary`: `false`로 설정하면 스텁 요약만 수행.

## 사용 시 주의
- 테스트나 CI에서는 API 키가 없을 가능성이 높으므로 스텁 경로가 항상 동작해야 합니다.
- LLM 호출 실패 시 전체 파이프라인이 중단되지 않도록 예외를 잡고 스텁으로 대체합니다.
- `logging.redact_fields`에 `llm_prompt`, `llm_response`가 포함되어 있으면 StageLogger가 자동 마스킹합니다.

## 향후 확장 아이디어
- Azure OpenAI나 사내 모델 등 추가 provider 지원.
- 요약 결과에 대한 JSON Schema/Pydantic 검증 추가.
- LLM 재시도, 요청 병렬화, 비용 추적 등 운영 기능 강화.
