from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import PageBlock, TableStruct, TableCell, FigureAsset, BBox

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
    try:
        camelot_tables = camelot.read_pdf(str(pdf_path), pages=pages, flavor=flavor)
    except UserWarning as uw:
        # 'No tables found in table area' 경고 발생 시 명확한 안내 로그
        LOGGER.warning("Camelot에서 테이블을 찾지 못했습니다. PDF 구조 또는 table_area 파라미터를 확인하세요: %s", uw)
        return []
    except Exception as err:
        raise err

    if not camelot_tables:
        LOGGER.warning("Camelot에서 테이블을 찾지 못했습니다. PDF 구조 또는 table_area 파라미터를 확인하세요.")
        return []

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


# === New 2-Stage Extractor API ===
def extract_layout(pdf_path: str | Path, cfg: Dict[str, Any]) -> List[PageBlock]:
    """
    Stage A: 페이지 레이아웃에서 text/table/figure 후보 bbox를 검출합니다.
    - 우선 순위: layoutparser 설정이지만, 미설치/모델 부재 시 PyMuPDF+pdfplumber 복합 fallback
    - PageBlock.meta에 score, model 등을 기록
    """
    backend = (
        (cfg or {}).get("extract", {}).get("backend", {}).get("layout", "layoutparser")
    )
    blocks: List[PageBlock] = []
    pdfp = Path(pdf_path)

    # Fallback: PyMuPDF+pdfplumber 복합 검출
    try:
        import fitz  # type: ignore
        import pdfplumber  # type: ignore
        
        doc = fitz.open(str(pdfp))
        try:
            with pdfplumber.open(str(pdfp)) as plumber_pdf:
                for page_idx, (fitz_page, plumber_page) in enumerate(zip(doc, plumber_pdf.pages), start=1):
                    # 1. 텍스트 블록 (PyMuPDF)
                    for bidx, block in enumerate(fitz_page.get_text("blocks")):
                        x0, y0, x1, y1, text, *_ = block if len(block) >= 5 else (*block, "")
                        text_s = (str(text) or "").strip()
                        if not text_s:
                            continue
                        pb = PageBlock(
                            page_no=page_idx,
                            type="text",
                            bbox=(float(x0), float(y0), float(x1), float(y1)),
                            text=text_s,
                            meta={"score": 0.5, "model": backend or "fallback"},
                        )
                        blocks.append(pb)
                    
                    # 2. 테이블 후보 (pdfplumber)
                    try:
                        tables = plumber_page.find_tables()
                        for tidx, table in enumerate(tables):
                            if table.bbox:
                                x0, y0, x1, y1 = table.bbox
                                blocks.append(
                                    PageBlock(
                                        page_no=page_idx,
                                        type="table",
                                        bbox=(float(x0), float(y0), float(x1), float(y1)),
                                        text=None,
                                        meta={"score": 0.6, "model": "pdfplumber_table_detection", "table_index": tidx},
                                    )
                                )
                    except Exception as e:
                        LOGGER.debug("pdfplumber table detection 실패 (page %d): %s", page_idx, e)
                    
                    # 3. 이미지(figure) 후보 (PyMuPDF image extraction + bbox 추정)
                    try:
                        images = fitz_page.get_images(full=True)
                        for img_idx, img in enumerate(images):
                            xref = img[0]
                            # 이미지 xref로 실제 bbox 찾기 시도
                            img_rects = fitz_page.get_image_rects(xref)
                            if img_rects:
                                for rect in img_rects:
                                    blocks.append(
                                        PageBlock(
                                            page_no=page_idx,
                                            type="figure",
                                            bbox=(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
                                            text=None,
                                            meta={"score": 0.5, "model": "pymupdf_image_rect", "xref": xref},
                                        )
                                    )
                    except Exception as e:
                        LOGGER.debug("이미지 bbox 추출 실패 (page %d): %s", page_idx, e)
        finally:
            doc.close()
    except Exception:  # pragma: no cover
        LOGGER.warning("extract_layout fallback 실패", exc_info=True)

    return blocks


def extract_table(pdf_path: str | Path, block: PageBlock, cfg: Dict[str, Any]) -> TableStruct:
    """
    Stage B (table): bbox 크롭 후 표 구조 복원. 기본은 Table Transformer 지향, 현재는 pdfplumber 백업 구현.
    """
    pdfp = Path(pdf_path)
    # 기본 값
    cells: List[TableCell] = []
    n_rows = 0
    n_cols = 0
    csv_path: Optional[str] = None

    # pdfplumber 기반 간단 추출 (페이지 전체에서 가장 큰 표 하나를 고르는 식으로 대체)
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(str(pdfp)) as pdf:
            page = pdf.pages[block.page_no - 1]
            tables = page.extract_tables()
            table = max(tables, key=lambda t: (len(t), len(t[0]) if t else 0)) if tables else []
            n_rows = len(table)
            n_cols = len(table[0]) if table else 0
            for r_idx, row in enumerate(table):
                for c_idx, txt in enumerate(row):
                    cells.append(TableCell(row=r_idx, col=c_idx, text=str(txt or "")))
    except Exception:
        LOGGER.warning("pdfplumber 표 추출 실패", exc_info=True)

    return TableStruct(
        page_no=block.page_no,
        bbox=block.bbox,
        cells=cells,
        n_rows=n_rows,
        n_cols=n_cols,
        csv_path=csv_path,
        caption=None,
        id=None,
    )


def extract_figure(pdf_path: str | Path, block: PageBlock, cfg: Dict[str, Any]) -> FigureAsset:
    """
    Stage B (figure): PyMuPDF로 영역 크롭 파일을 생성. 실패 시 페이지 전체 스냅샷.
    """
    pdfp = Path(pdf_path)
    out_dir = Path((cfg or {}).get("paths", {}).get("artifacts_dir", "artifacts")) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    image_path = out_dir / f"p{block.page_no:04d}_{int(block.bbox[0])}_{int(block.bbox[1])}_{int(block.bbox[2])}_{int(block.bbox[3])}.png"

    try:
        import fitz  # type: ignore
        doc = fitz.open(str(pdfp))
        try:
            page = doc[block.page_no - 1]
            rect = fitz.Rect(*block.bbox)
            pix = page.get_pixmap(clip=rect, dpi=(cfg or {}).get("extract", {}).get("dpi", {}).get("crop_export", 300))
            pix.save(str(image_path))
        finally:
            doc.close()
    except Exception:
        LOGGER.warning("figure 크롭 실패, 페이지 전체로 대체", exc_info=True)
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(str(pdfp)) as pdf:
                page = pdf.pages[block.page_no - 1]
                im = page.to_image(resolution=(cfg or {}).get("extract", {}).get("dpi", {}).get("crop_export", 300))
                im.save(str(image_path), format="PNG")
        except Exception:
            LOGGER.error("페이지 스냅샷 저장 실패", exc_info=True)

    return FigureAsset(
        page_no=block.page_no,
        bbox=block.bbox,
        image_path=str(image_path),
        caption=None,
        id=None,
    )


# ============================================================================
# Docling-based extractors
# ============================================================================

def extract_with_docling(
    pdf_path: Path,
    artifacts_dir: Path,
    do_ocr: bool = False,
    do_table_structure: bool = True,
) -> Tuple[List[PageBlock], List[TableStruct], List[FigureAsset]]:
    """
    Docling을 사용하여 PDF에서 layout, table, figure를 추출합니다.
    
    Args:
        pdf_path: PDF 파일 경로
        artifacts_dir: 추출된 그림을 저장할 디렉토리
        do_ocr: OCR 수행 여부
        do_table_structure: 테이블 구조 인식 여부
        
    Returns:
        (layout_blocks, tables, figures) 튜플
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    from docling_core.types.doc import PictureItem, TableItem, TextItem
    
    LOGGER.info(f"Docling으로 PDF 추출 시작: {pdf_path}")
    
    # Docling 파이프라인 옵션 설정
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = do_table_structure
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.generate_picture_images = True  # 그림 이미지 생성 활성화
    pipeline_options.images_scale = 2.0  # 고해상도 이미지
    
    # Converter 생성
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
            )
        }
    )
    
    # PDF 변환
    result = converter.convert(pdf_path)
    doc = result.document
    
    # Layout blocks 변환
    layout_blocks: List[PageBlock] = []
    for item, _level in doc.iterate_items():
        if isinstance(item, TextItem) and item.prov:
            prov = item.prov[0]
            layout_blocks.append(PageBlock(
                page_no=prov.page_no,
                type="text",
                bbox=[prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b],
                text=item.text,
                meta={"source": "docling", "label": item.label if hasattr(item, 'label') else None}
            ))
    
    # Tables 변환
    tables: List[TableStruct] = []
    for table_item in doc.tables:
        if not table_item.prov:
            continue
        
        prov = table_item.prov[0]
        cells: List[TableCell] = []
        
        for cell in table_item.data.table_cells:
            cells.append(TableCell(
                row=cell.start_row_offset_idx,
                col=cell.start_col_offset_idx,
                text=cell.text,
                rowspan=cell.row_span,
                colspan=cell.col_span
            ))
        
        tables.append(TableStruct(
            page_no=prov.page_no,
            bbox=[prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b],
            cells=cells,
            n_rows=table_item.data.num_rows,
            n_cols=table_item.data.num_cols,
            caption=None,
            csv_path=None,
            id=None
        ))
    
    # Figures 변환
    figures: List[FigureAsset] = []
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem) and item.prov:
            prov = item.prov[0]
            
            # Caption 추출 (있는 경우)
            caption_text = None
            if hasattr(item, 'captions') and item.captions:
                caption_items = [doc.get_item(ref) for ref in item.captions]
                caption_text = " ".join(c.text for c in caption_items if hasattr(c, 'text'))
            
            # 이미지가 있는 경우에만 저장
            if item.image:
                # 그림 저장
                bbox_int = [
                    int(prov.bbox.l),
                    int(prov.bbox.t),
                    int(prov.bbox.r),
                    int(prov.bbox.b)
                ]
                image_filename = f"p{prov.page_no:04d}_{bbox_int[0]}_{bbox_int[1]}_{bbox_int[2]}_{bbox_int[3]}.png"
                image_path = artifacts_dir / image_filename
                
                try:
                    # Docling ImageRef를 PIL Image로 변환하여 저장
                    pil_image = item.image.pil_image
                    pil_image.save(image_path, format="PNG")
                    
                    figures.append(FigureAsset(
                        page_no=prov.page_no,
                        bbox=[prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b],
                        image_path=str(image_path),
                        caption=caption_text,
                        id=None
                    ))
                except Exception as e:
                    LOGGER.error(f"그림 저장 실패 ({image_path}): {e}", exc_info=True)
            else:
                # 이미지가 없어도 메타데이터는 기록 (PDF에서 직접 추출 필요)
                LOGGER.warning(f"PictureItem에 이미지 데이터 없음: page={prov.page_no}, "
                              f"bbox=({prov.bbox.l:.1f},{prov.bbox.t:.1f},{prov.bbox.r:.1f},{prov.bbox.b:.1f})")
                
                # PyMuPDF를 사용해서 직접 이미지 추출 시도
                try:
                    import fitz
                    doc_pdf = fitz.open(pdf_path)
                    page = doc_pdf[prov.page_no - 1]  # 0-indexed
                    
                    # Bbox를 PyMuPDF 좌표계로 변환
                    bbox_rect = fitz.Rect(prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b)
                    pix = page.get_pixmap(clip=bbox_rect, matrix=fitz.Matrix(2, 2))  # 2x scale
                    
                    bbox_int = [
                        int(prov.bbox.l),
                        int(prov.bbox.t),
                        int(prov.bbox.r),
                        int(prov.bbox.b)
                    ]
                    image_filename = f"p{prov.page_no:04d}_{bbox_int[0]}_{bbox_int[1]}_{bbox_int[2]}_{bbox_int[3]}.png"
                    image_path = artifacts_dir / image_filename
                    
                    pix.save(str(image_path))
                    doc_pdf.close()
                    
                    figures.append(FigureAsset(
                        page_no=prov.page_no,
                        bbox=[prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b],
                        image_path=str(image_path),
                        caption=caption_text,
                        id=None
                    ))
                    LOGGER.info(f"PyMuPDF로 그림 추출 성공: {image_filename}")
                except Exception as e:
                    LOGGER.error(f"PyMuPDF 그림 추출 실패: {e}", exc_info=True)
    
    LOGGER.info(f"Docling 추출 완료: layout_blocks={len(layout_blocks)}, "
                f"tables={len(tables)}, figures={len(figures)}")
    
    return layout_blocks, tables, figures
