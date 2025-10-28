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

```bash
PYTHONPATH=src python -m vai_plan.pipeline --config configs/default.yaml --pdf data/raw/JESD79-5.pdf
```

Windows PowerShell에서는 다음과 같이 실행할 수 있습니다.

```powershell
$env:PYTHONPATH='src'; python -m vai_plan.pipeline --config configs/default.yaml --pdf data/raw/JESD79-5.pdf
```

## 중간 산출물 및 로그

- `logs/01_extraction/`, `02_chunking/` 등 단계별 디렉터리에 JSON/Markdown 스냅샷이 저장됩니다.
- `data/processed/run_<timestamp>/` 에서는 각 단계 출력이 JSON으로 캐시됩니다.
- LLM 프롬프트/응답은 `logging.redact_fields` 설정에 따라 자동 마스킹됩니다.

## 설계 문서

- `docs/modules/` : 모듈별 메모 (`pipeline`, `logging`, `extractors`, `processors`, `llm`, `catalog_review`, `commands`).
- `docs/schemas/requirement_unit.md` : `catalog.yaml`에 기록되는 요구사항 단위 스키마 정의.
- 시스템 설계 관련 문서는 모두 한글로 작성하며, 변경 시 해당 문서를 우선적으로 업데이트합니다.
- `configs/default.yaml`의 `commands.patterns`를 수정하면 파이프라인이 텍스트 청크에서 command 토큰을 자동 탐지해 각 요구사항의 `commands` 필드를 채웁니다.
- OpenAI 기반 요약을 사용하려면 환경 변수 `OPENAI_API_KEY`(또는 `llm.api_key_env`에 지정한 이름)에 API 키를 설정한 뒤 파이프라인을 실행하세요. 키가 없으면 스텁 요약으로 자동 대체됩니다.

## 주요 산출물

- `catalog.yaml` : `requirement_units` 및 메타데이터를 담은 커버리지 초안.
- `review.yaml` : 확장 시스템이 ingest할 검증 테스트 플랜 입력. YAML 스키마 유지 필수.
- `compatibility_matrix.csv` : command 순차 실행 가능 여부 테이블(행=선행, 열=후속).

## 향후 작업

- PDF 추출기 실제 구현 및 테스트 케이스 보강
- 요구사항 스키마(pydantic/JSON Schema) 검증 로직 추가
- LLM 연동, 프롬프트 템플릿, 재시도 정책 설계
- command 호환성 판단 로직 고도화 및 UI/리포트 연계
- CI 파이프라인과 코드 스타일 도구(e.g., black, flake8) 적용
