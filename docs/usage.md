# VAI_PLAN 사용 가이드

## 실행 준비
1. Python 3.10 이상 가상환경을 활성화합니다.
2. `pip install -r requirements.txt`로 의존성을 설치합니다.
3. 분석 대상 DDR5 PDF를 `data/raw/`에 복사합니다.
4. 필요 시 `configs/default.yaml`을 복사하여 사용자 정의 설정을 만듭니다.

## 기본 실행

```bash
python -m vai_plan.pipeline --config configs/default.yaml --pdf data/raw/JESD79-5.pdf
```

또는 스크립트를 사용할 경우:

```bash
python scripts/run_pipeline.py --config configs/default.yaml --pdf data/raw/JESD79-5.pdf
```

## 로그와 산출물
- `logs/`: 단계별 JSON/Markdown 스냅샷, `pipeline.log` 포함
- `data/processed/<run_id>/`: 각 단계의 중간 산출물(JSON)
- `artifacts/`: 최종 `catalog.yaml`, `review.yaml`

실행 컨텍스트 ID(`run_<timestamp>`)는 로그 파일과 디렉터리 이름에 사용되므로, 동일한 PDF에 대한 반복 실행에서도 결과를 구분할 수 있습니다.

## 구성 키 참고
- `extraction.tables.engine`: `camelot` 또는 `pdfplumber` 등 원하는 파서로 수정
- `llm.model`: 연결할 LLM 식별자
- `logging.redact_fields`: 로그에 남기지 않을 필드를 지정

## 문제 해결
- PDF 경로가 잘못될 경우 `FileNotFoundError`가 발생하니, 명령행 `--pdf` 옵션 또는 설정 파일을 확인하세요.
- Camelot 사용 시 Ghostscript가 필요할 수 있습니다. OS에 맞게 사전 설치하세요.
- 로그가 과다할 경우 `logging.level`을 `WARNING` 이상으로 조정하면 저장 용량을 줄일 수 있습니다.
