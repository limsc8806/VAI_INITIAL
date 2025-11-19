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

# extractors.py 모듈 메모

## 핵심 역할
- PyMuPDF(fitz)를 이용해 페이지별 텍스트 블록 및 좌표를 추출합니다.
- Camelot ⇒ pdfplumber 순으로 표를 추출하고, 실패 시 graceful fallback을 수행합니다.
- PyMuPDF 이미지 메타데이터를 수집하여 그림 정보를 제공합니다.

## 반환 구조
- 텍스트: `{ "page": int, "content": str, "bbox": [x0, y0, x1, y1], "source": "text", "block_index": int }`
- 표: `{ "page": int, "content": List[List[str]], "source": "table", "meta": {...} }`
- 그림: `{ "page": int, "source": "figure", "image_index": int, "meta": {...} }`

## 주요 구현 포인트
- 텍스트 블록은 `page.get_text("blocks")` 결과를 필터링하고 최소 길이 조건(`min_paragraph_length`)을 적용합니다.
- 표 추출은 Camelot(`flavor` 설정 가능)을 우선 시도하고, 예외 발생 시 pdfplumber의 `extract_tables`로 대체합니다.
- 그림 추출은 이미지의 xref, 크기, 색 공간 등의 메타데이터만 반환하며, 파일 저장은 추후 확장 포인트입니다.

## 향후 개선 아이디어
- 추출된 텍스트/표/그림을 좌표 기반으로 연계하여 캡션 매칭.
- Camelot/Camelot 실패 시 Tabula 또는 OCR 기반 fallback 추가.
- 이미지 추출 시 파일로 저장하고 경로를 metadata에 포함.
- 추출 성능/정확도에 대한 벤치마크 및 회귀 테스트 강화.
