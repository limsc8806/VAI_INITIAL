from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from .models import PageBlock, TableStruct, FigureAsset, Chunk as SchemaChunk

LOGGER = logging.getLogger(__name__)


@dataclass
class LegacyChunk:
    page: int
    kind: str
    content: str
    metadata: Dict[str, Any]


def merge_artifacts(
    texts: Iterable[Dict[str, Any]],
    tables: Iterable[Dict[str, Any]],
    figures: Iterable[Dict[str, Any]],
) -> List[LegacyChunk]:
    """텍스트/표/그림 아티팩트를 단일 시퀀스로 병합합니다."""
    merged: List[LegacyChunk] = []
    for item in texts:
        merged.append(
            LegacyChunk(
                page=item.get("page", 0),
                kind=item.get("source", "text"),
                content=item.get("content", ""),
                metadata=item,
            )
        )
    for item in tables:
        merged.append(
            LegacyChunk(
                page=item.get("page", 0),
                kind=item.get("source", "table"),
                content="\n".join(
                    " | ".join("" if cell is None else str(cell) for cell in row)
                    for row in item.get("content", [])
                ),
                metadata=item,
            )
        )
    for item in figures:
        merged.append(
            LegacyChunk(
                page=item.get("page", 0),
                kind=item.get("source", "figure"),
                content=item.get("caption", ""),
                metadata=item,
            )
        )
    merged.sort(key=lambda chunk: (chunk.page, chunk.kind))
    LOGGER.debug("병합된 아티팩트 수: %d", len(merged))
    return merged


def chunk_text(
    chunks: Iterable[LegacyChunk],
    max_characters: int,
    overlap_characters: int,
) -> List[Dict[str, Any]]:
    """요구사항 후보 생성을 위한 청크 단위를 만듭니다."""
    chunked: List[Dict[str, Any]] = []
    buffer = ""
    buffer_meta: Dict[str, Any] = {}

    for chunk in chunks:
        if len(buffer) + len(chunk.content) > max_characters:
            chunked.append(
                {
                    "text": buffer.strip(),
                    "metadata": buffer_meta,
                }
            )
            buffer = buffer[-overlap_characters :] if overlap_characters else ""
            buffer_meta = {}

        if not buffer:
            buffer_meta = {
                "start_page": chunk.page,
                "kinds": [chunk.kind],
            }
        else:
            kinds = buffer_meta.setdefault("kinds", [])
            if chunk.kind not in kinds:
                kinds.append(chunk.kind)
        buffer += f"\n{chunk.content}"

    if buffer:
        chunked.append(
            {
                "text": buffer.strip(),
                "metadata": buffer_meta,
            }
        )
    LOGGER.debug("생성된 청크 수: %d", len(chunked))
    return chunked


def build_requirements(
    chunked_texts: Iterable[Dict[str, Any]],
    llm_summaries: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """LLM 요약 결과와 추출 데이터를 결합해 요구사항 단위를 구성합니다."""
    requirements = []
    # 요구사항 단위 스키마 정의 (docs/schemas/requirement_unit.md 기준)
    SCHEMA_FIELDS = {
        "id": (str, True),
        "title": (str, True),
        "description": (str, True),
        "source_pages": (list, False),
        "evidence": (dict, False),
        "commands": (list, False),
        "tags": (list, False),
        "dependencies": (list, False),
        "confidence": (float, False),
        "validation_status": (str, False),
        "notes": (str, False),
        "compatibility_matrix": (dict, False),
    }

    def normalize_field(value, typ):
        if typ == str:
            return str(value) if value is not None else ""
        if typ == float:
            try:
                return float(value)
            except Exception:
                return 0.0
        if typ == list:
            return list(value) if value is not None else []
        if typ == dict:
            return dict(value) if value is not None else {}
        return value

    for idx, (chunk, summary) in enumerate(zip(chunked_texts, llm_summaries), start=1):
        req = {}
        # 필수 필드
        req["id"] = f"REQ-{idx:04d}"
        req["title"] = normalize_field(summary.get("title", f"Requirement {idx}"), str)
        req["description"] = normalize_field(summary.get("description", ""), str)
        # 선택/권장 필드
        req["source_pages"] = normalize_field(summary.get("source_pages", []), list)
        req["evidence"] = normalize_field(chunk.get("metadata", {}), dict)
        req["confidence"] = normalize_field(summary.get("confidence", 0.5), float)
        # commands/tags/dependencies/validation_status/notes/compatibility_matrix 등은 후처리에서 추가됨
        # 스키마에 없는 필드는 무시
        # 스키마 필드 누락 시 기본값 채움
        for field, (typ, required) in SCHEMA_FIELDS.items():
            if field not in req:
                req[field] = normalize_field(None, typ)
        requirements.append(req)
    LOGGER.debug("요구사항 단위 %d개 생성 (스키마 검증/정규화 포함)", len(requirements))
    return requirements


# === New processors for 2-stage pipeline ===
def associate_captions(blocks: List[PageBlock], cfg: Dict[str, Any]) -> List[PageBlock]:
    """
    같은 페이지 내에서 캡션 패턴과의 거리/같은 컬럼 우선으로 table/figure에 caption 매핑.
    간단 휴리스틱: caption 패턴에 매칭되는 텍스트 블록 중 가장 가까운 것을 선택.
    """
    import re

    pat_fig = (cfg or {}).get("extract", {}).get("caption", {}).get("pattern_figure") or r"^(Figure|Fig\.)\s*\d+"
    pat_tbl = (cfg or {}).get("extract", {}).get("caption", {}).get("pattern_table") or r"^(Table|표)\s*\d+"
    r_fig = re.compile(pat_fig)
    r_tbl = re.compile(pat_tbl)

    # 페이지별로 텍스트 캡션 후보 수집
    page_text: Dict[int, List[PageBlock]] = {}
    for b in blocks:
        if b.type == "text" and (b.text or "").strip():
            page_text.setdefault(b.page_no, []).append(b)

    def center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x0, y0, x1, y1 = bbox
        return (0.5 * (x0 + x1), 0.5 * (y0 + y1))

    def dist(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5

    out: List[PageBlock] = []
    for b in blocks:
        if b.type not in ("table", "figure"):
            out.append(b)
            continue
        candidates = page_text.get(b.page_no, [])
        best = None
        best_d = 1e18
        c_b = center(b.bbox)
        pattern = r_tbl if b.type == "table" else r_fig
        for t in candidates:
            if not pattern.search(t.text or ""):
                continue
            d = dist(c_b, center(t.bbox))
            if d < best_d:
                best = t
                best_d = d
        new_meta = dict(b.meta)
        if best is not None:
            new_meta["caption"] = best.text
        out.append(PageBlock(page_no=b.page_no, type=b.type, bbox=b.bbox, text=b.text, meta=new_meta))
    return out


def normalize_tables(tbls: List[TableStruct]) -> List[TableStruct]:
    """헤더/단위/공백 정리 등 간단 정규화 자리 채우기."""
    norm: List[TableStruct] = []
    for t in tbls:
        # 공백 정리
        cells = [
            type(c)(row=c.row, col=c.col, text=(c.text or "").strip(), rowspan=c.rowspan, colspan=c.colspan)
            for c in t.cells
        ]
        norm.append(TableStruct(page_no=t.page_no, bbox=t.bbox, cells=cells, n_rows=t.n_rows, n_cols=t.n_cols, csv_path=t.csv_path, caption=t.caption, id=t.id))
    return norm


def to_chunks(blocks: List[PageBlock], tables: List[TableStruct], figures: List[FigureAsset], pdf_path: str, cfg: Dict[str, Any]) -> List[SchemaChunk]:
    chunks: List[SchemaChunk] = []
    include = (cfg or {}).get("chunk", {}).get("include_types", ["text", "table", "figure"])
    # 텍스트
    for b in blocks:
        if b.type == "text" and "text" in include and (b.text or "").strip():
            chunks.append(
                SchemaChunk(
                    type="text",
                    id=None,
                    source={"pdf": str(pdf_path), "page": b.page_no, "bbox": list(b.bbox)},
                    payload={"text": b.text},
                )
            )
    # 표
    for t in tables:
        if "table" in include:
            chunks.append(
                SchemaChunk(
                    type="table",
                    id=t.id,
                    source={"pdf": str(pdf_path), "page": t.page_no, "bbox": list(t.bbox)},
                    payload={
                        "csv": t.csv_path,
                        "n_rows": t.n_rows,
                        "n_cols": t.n_cols,
                        "caption": t.caption,
                    },
                )
            )
    # 그림
    for f in figures:
        if "figure" in include:
            chunks.append(
                SchemaChunk(
                    type="figure",
                    id=f.id,
                    source={"pdf": str(pdf_path), "page": f.page_no, "bbox": list(f.bbox)},
                    payload={"image": f.image_path, "caption": f.caption},
                )
            )
    return chunks
