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

# 요구사항 단위 스키마 명세

`catalog.yaml`의 `requirement_units` 배열에 포함되는 객체 구조를 정의합니다. 필드는 모두 한글 설명과 함께 데이터 타입, 필수 여부를 명시합니다.

## 최상위 구조

```yaml
requirement_units:
  - id: REQ-0001
    title: DDR5 초기화 커맨드 정의
    ...
```

## 필드 목록

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `id` | string | 예 | 요구사항 고유 식별자 (`REQ-0001` 등). |
| `title` | string | 예 | 요구사항 요약 제목. |
| `description` | string | 예 | 요구사항 본문 설명(멀티라인 허용). |
| `source_pages` | list\<int\> | 권장 | 근거가 된 PDF 페이지 번호. |
| `evidence` | map | 선택 | 추출 근거 메타데이터(`start_page`, `kinds`, `snippets`, `extraction_hash` 등). |
| `commands` | list\<map\> | 선택 | 관련 command 목록. `commands.py`가 텍스트 패턴을 이용해 자동 채우며, 각 항목은 최소 `name`을 포함. 추가로 `description`, `preconditions`, `postconditions`, `params`, `references` 등을 확장 가능. |
| `tags` | list\<string\> | 선택 | 인터페이스/전력/타이밍 등 카테고리 라벨. |
| `dependencies` | list\<string\> | 선택 | 선행해야 하는 다른 요구사항 ID. |
| `confidence` | float (0~1) | 권장 | 추정 신뢰도. |
| `validation_status` | string | 선택 | `pending`, `in_review`, `approved` 등 검증 단계. |
| `notes` | string | 선택 | 리뷰 메모, 보완 요청 등. |
| `compatibility_matrix` | map | 선택 | command 연속 실행 가능 여부를 명시한 행렬. |

### evidence 예시

```yaml
evidence:
  start_page: 12
  kinds: ["text", "table"]
  snippets:
    - "표 3-2: Command Timing Parameters"
  extraction_hash: "sha256:..."
```

### commands 예시

```yaml
commands:
  - name: CMD_ACTIVATE
    description: 뱅크 활성화 시퀀스
    params:
      ca: 0x03
      ck: 0x1
    preconditions:
      - "전력 상태: POWER-UP COMPLETE"
    postconditions:
      - "SR1 = 0x1"
```

### compatibility_matrix 예시

```yaml
compatibility_matrix:
  description: "command 연속 실행 가능 여부 (Y: 가능, N: 불가)"
  matrix:
    CMD_INIT:
      CMD_START: Y
      CMD_STOP: N
    CMD_START:
      CMD_STOP: Y
      CMD_RESET: N
  default: N
```

- `matrix`는 행=선행 command, 열=후속 command 구조입니다.
- `default` 값은 명시되지 않은 조합의 기본 상태입니다.
- 파이프라인은 이 정보를 이용해 `artifacts/compatibility_matrix.csv`를 생성합니다.

## 검증 규칙

1. `id`, `title`, `description` 생략 시 파이프라인에서 경고 후 해당 요구사항을 제외하거나 수동 검증 목록에 추가합니다.
2. 숫자/리스트 등 타입이 어긋나면 pydantic 검증(향후 도입 예정)에서 실패 처리합니다.
3. `id` 중복은 실행 중단 사유이며, 로그에 상세 이유를 남깁니다.
4. `compatibility_matrix`에 정의된 command가 `commands` 목록에 없을 경우 경고를 출력해 동기화를 요구합니다.

## 향후 개선 사항

- `validation_status`를 워크플로우(`draft` → `review` → `approved`)와 연동.
- `commands`에 파라미터/사이드이펙트/지연 시간 등 도메인별 속성 자동 생성.
- `compatibility_matrix`를 외부 그래프 또는 별도 YAML로 분리해 재사용성 향상.
- pydantic 모델과 스키마 테스트를 추가해 구조 변경 시 자동 검증.
