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
