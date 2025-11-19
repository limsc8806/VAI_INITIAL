from __future__ import annotations
import pytest
from vai_plan import processors

def test_build_requirements_schema_normalization():
    """
    요구사항 스키마 검증 및 정규화 테스트
    - 필수/선택 필드가 모두 포함되는지 확인
    - 타입이 올바르게 변환되는지 확인
    """
    chunked_texts = [
        {"text": "CMD_ACTIVATE", "metadata": {"start_page": 1, "kinds": ["text"]}},
        {"text": "CMD_INIT", "metadata": {"start_page": 2, "kinds": ["table"]}},
    ]
    llm_summaries = [
        {"title": "활성화 명령", "description": "DDR5 뱅크 활성화", "source_pages": [1], "confidence": 0.9},
        {"title": "초기화 명령", "description": "DDR5 초기화", "source_pages": [2], "confidence": 0.8},
    ]
    requirements = processors.build_requirements(chunked_texts, llm_summaries)
    assert len(requirements) == 2
    for req in requirements:
        # 필수 필드
        assert isinstance(req["id"], str)
        assert isinstance(req["title"], str)
        assert isinstance(req["description"], str)
        # 선택/권장 필드
        assert isinstance(req["source_pages"], list)
        assert isinstance(req["evidence"], dict)
        assert isinstance(req["confidence"], float)
        # 스키마 정의된 모든 필드가 존재하는지 확인
        for field in [
            "commands", "tags", "dependencies", "validation_status", "notes", "compatibility_matrix"
        ]:
            assert field in req

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    pytest.skip("PyMuPDF(fitz)가 설치되어야 추출기를 테스트할 수 있습니다.", allow_module_level=True)

from vai_plan import extractors


def _make_sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), "Hello DDR5\nCommand Matrix", fontsize=12)

        pix = fitz.Pixmap(fitz.csRGB, fitz.Rect(0, 0, 10, 10), 0)
        pix.set_pixel(0, 0, (255, 0, 0))
        rect = fitz.Rect(100, 150, 120, 170)
        page.insert_image(rect, pixmap=pix)
    finally:
        doc.save(pdf_path)
        doc.close()
    return pdf_path


def test_extract_text_returns_paragraph(tmp_path: Path) -> None:
    pdf_path = _make_sample_pdf(tmp_path)
    segments = extractors.extract_text(pdf_path, min_paragraph_length=5)
    assert segments, "텍스트 세그먼트를 최소 1개 이상 추출해야 합니다."
    content = " ".join(segment["content"] for segment in segments)
    assert "Hello DDR5" in content


def test_extract_tables_with_pdfplumber(tmp_path: Path) -> None:
    pdf_path = _make_sample_pdf(tmp_path)
    tables = extractors.extract_tables(pdf_path, engine="pdfplumber")
    assert isinstance(tables, list)
    # 테스트 PDF에는 표가 없으므로 빈 리스트일 수 있음.
    assert all("content" in table for table in tables)


def test_extract_figures(tmp_path: Path) -> None:
    pdf_path = _make_sample_pdf(tmp_path)
    figures = extractors.extract_figures(pdf_path)
    assert isinstance(figures, list)
    assert figures, "삽입한 PNG 이미지를 최소 1개 이상 식별해야 합니다."
    first = figures[0]
    assert first["source"] == "figure"
    assert "meta" in first
