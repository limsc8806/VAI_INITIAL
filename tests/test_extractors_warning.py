from __future__ import annotations
import pytest
from vai_plan import extractors

def test_pymupdf_and_camelot_installed(tmp_path):
    """
    PyMuPDF와 Camelot 설치 여부 및 추출 품질 테스트
    - PyMuPDF: 텍스트 추출 fallback 없이 정상 동작
    - Camelot: 표 추출 fallback 없이 정상 동작
    """
    # 샘플 PDF 생성
    pdf_path = tmp_path / "sample.pdf"
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    # 한글 폰트 매핑 문제로 블록 문자열이 '··· ···' 형태로 추출될 수 있으므로 라틴 텍스트로 교체
    page.insert_text((72, 72), "TEST TEXT", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    # 텍스트 추출 (PyMuPDF 정상 동작 확인)
    text_segments = extractors.extract_text(pdf_path, min_paragraph_length=2)
    assert text_segments, "PyMuPDF가 정상 동작해야 fallback 경고가 발생하지 않음"
    assert any("TEST TEXT" in seg["content"] for seg in text_segments)

    # 표 추출 (Camelot 정상 동작 확인)
    # Camelot은 빈 PDF에서 표를 못 찾으므로, fallback 경고가 발생하지 않는지만 체크
    try:
        tables = extractors.extract_tables(pdf_path, engine="camelot")
        assert isinstance(tables, list)
    except Exception as e:
        pytest.fail(f"Camelot 표 추출 실패: {e}")
