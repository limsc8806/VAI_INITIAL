from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LOGGER = logging.getLogger(__name__)


def _pdfplumber_text(
    pdf_path: Path,
    min_paragraph_length: int,
) -> List[Dict[str, Any]]:
    import pdfplumber  # type: ignore

    segments: List[Dict[str, Any]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            paragraphs = [para.strip() for para in text.split("\n") if para.strip()]
            for block_index, paragraph in enumerate(paragraphs):
                if len(paragraph) < min_paragraph_length:
                    continue
                segments.append(
                    {
                        "page": page_index,
                        "source": "text",
                        "content": paragraph,
                        "bbox": None,
                        "block_index": block_index,
                    }
                )
    return segments


def extract_text(
    pdf_path: Path,
    min_paragraph_length: int = 20,
) -> List[Dict[str, Any]]:
    """
    PyMuPDF 기반으로 텍스트 블록을 추출합니다.

    Returns:
        각 항목은 페이지 번호, 좌표(bbox), 블록 인덱스, 내용 등을 포함합니다.
    """
    try:
        import fitz  # type: ignore
    except ImportError as err:
        LOGGER.warning("PyMuPDF 미설치로 pdfplumber 텍스트 추출 fallback 수행 (%s)", pdf_path)
        return _pdfplumber_text(pdf_path, min_paragraph_length)

    doc = fitz.open(pdf_path)
    segments: List[Dict[str, Any]] = []

    try:
        for page_index, page in enumerate(doc, start=1):
            try:
                blocks: Iterable[Any] = page.get_text("blocks")
            except RuntimeError:
                LOGGER.warning("페이지 %s 텍스트 블록 추출 실패", page_index, exc_info=True)
                continue

            for block_index, block in enumerate(blocks):
                if not block:
                    continue
                # PyMuPDF block tuple: (x0, y0, x1, y1, text, block_no, ...)
                block_tuple = tuple(block)
                coords = block_tuple[:4] if len(block_tuple) >= 4 else ()
                text = block_tuple[4] if len(block_tuple) >= 5 else block_tuple[-1]
                content = str(text).strip()
                if len(content) < min_paragraph_length:
                    continue

                bbox = [float(coords[i]) for i in range(4)] if len(coords) == 4 else None
                segments.append(
                    {
                        "page": page_index,
                        "source": "text",
                        "content": content,
                        "bbox": bbox,
                        "block_index": block_index,
                    }
                )
    finally:
        doc.close()

    LOGGER.debug("텍스트 블록 %d개 추출 (%s)", len(segments), pdf_path)
    if not segments:
        LOGGER.warning("PyMuPDF 기반 텍스트 추출 결과가 비어 fallback(pdfplumber)을 시도합니다: %s", pdf_path)
        return _pdfplumber_text(pdf_path, min_paragraph_length)
    return segments


def _camelot_tables(
    pdf_path: Path,
    pages: str,
    flavor: str,
) -> List[Dict[str, Any]]:
    import camelot  # type: ignore

    tables: List[Dict[str, Any]] = []
    camelot_tables = camelot.read_pdf(str(pdf_path), pages=pages, flavor=flavor)
    for table in camelot_tables:
        try:
            data = table.df.fillna("").values.tolist()
        except AttributeError:
            data = table.df.values.tolist()
        tables.append(
            {
                "page": int(table.page) if table.page is not None else None,
                "source": "table",
                "content": data,
                "meta": {
                    "rows": len(data),
                    "cols": len(data[0]) if data else 0,
                    "flavor": flavor,
                    "accuracy": getattr(table, "accuracy", None),
                },
            }
        )
    return tables


def _pdfplumber_tables(pdf_path: Path) -> List[Dict[str, Any]]:
    import pdfplumber  # type: ignore

    tables: List[Dict[str, Any]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            extracted = page.extract_tables()
            for table_index, table in enumerate(extracted):
                tables.append(
                    {
                        "page": page_index,
                        "source": "table",
                        "content": table,
                        "table_index": table_index,
                        "meta": {
                            "rows": len(table),
                            "cols": len(table[0]) if table else 0,
                            "engine": "pdfplumber",
                        },
                    }
                )
    return tables


def extract_tables(
    pdf_path: Path,
    engine: str = "camelot",
    flavor: str = "stream",
) -> List[Dict[str, Any]]:
    """
    Camelot(기본) 혹은 pdfplumber를 이용해 표를 추출합니다.
    """
    tables: List[Dict[str, Any]] = []
    if engine == "camelot":
        try:
            tables = _camelot_tables(pdf_path, pages="all", flavor=flavor)
            LOGGER.debug("Camelot으로 표 %d개 추출 (%s)", len(tables), pdf_path)
            return tables
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.warning("Camelot 표 추출 실패, pdfplumber로 fallback (%s): %s", pdf_path, err)

    try:
        tables = _pdfplumber_tables(pdf_path)
        LOGGER.debug("pdfplumber로 표 %d개 추출 (%s)", len(tables), pdf_path)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.warning("pdfplumber 표 추출 실패 (%s): %s", pdf_path, err)

    return tables


def extract_figures(
    pdf_path: Path,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    PyMuPDF로 이미지(그림) 메타데이터를 추출합니다.

    Args:
        limit: 추출할 최대 이미지 수 (None이면 전체).
    """
    try:
        import fitz  # type: ignore
    except ImportError as err:
        LOGGER.debug("PyMuPDF 미설치로 그림 추출 생략")
        return []

    doc = fitz.open(pdf_path)
    figures: List[Dict[str, Any]] = []

    try:
        for page_index, page in enumerate(doc, start=1):
            images = page.get_images(full=True)
            for image_index, image in enumerate(images):
                xref = image[0]
                width = image[2]
                height = image[3]
                bpc = image[4]
                colorspace = image[5]
                meta = {
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "bpc": bpc,
                    "colorspace": colorspace,
                }
                figures.append(
                    {
                        "page": page_index,
                        "source": "figure",
                        "image_index": image_index,
                        "meta": meta,
                    }
                )
                if limit is not None and len(figures) >= limit:
                    LOGGER.debug("그림 추출 제한(%s)에 도달", limit)
                    return figures
    finally:
        doc.close()

    LOGGER.debug("그림 %d개 추출 (%s)", len(figures), pdf_path)
    return figures
