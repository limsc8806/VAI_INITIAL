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
   - 출력: 요구사항 단위 리스트(각각 `id`, `title`, `description`, `source_pages`, `evidence`, `confidence`)

## 향후 개선 사항
- 청킹 로직에 표/그림 요약 포함 여부 결정.
- `metadata` 내 `kinds`를 더 풍부한 정보(비율, confidence)로 확장.
- 요구사항 스키마를 별도 파일로 정의하고 pydantic 검증을 추가.

## 갱신 규칙
- `Chunk` 구조나 요구사항 YAML 포맷이 변할 경우 `catalog.yaml`, `review.yaml` 관련 문서도 함께 업데이트합니다.
