from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

LOGGER = logging.getLogger(__name__)


@dataclass
class Chunk:
    page: int
    kind: str
    content: str
    metadata: Dict[str, Any]


def merge_artifacts(
    texts: Iterable[Dict[str, Any]],
    tables: Iterable[Dict[str, Any]],
    figures: Iterable[Dict[str, Any]],
) -> List[Chunk]:
    """텍스트/표/그림 아티팩트를 단일 시퀀스로 병합합니다."""
    merged: List[Chunk] = []
    for item in texts:
        merged.append(
            Chunk(
                page=item.get("page", 0),
                kind=item.get("source", "text"),
                content=item.get("content", ""),
                metadata=item,
            )
        )
    for item in tables:
        merged.append(
            Chunk(
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
            Chunk(
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
    chunks: Iterable[Chunk],
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
    for idx, (chunk, summary) in enumerate(zip(chunked_texts, llm_summaries), start=1):
        requirements.append(
            {
                "id": f"REQ-{idx:04d}",
                "title": summary.get("title", f"Requirement {idx}"),
                "description": summary.get("description", ""),
                "source_pages": summary.get("source_pages", []),
                "evidence": chunk.get("metadata", {}),
                "confidence": summary.get("confidence", 0.5),
            }
        )
    LOGGER.debug("요구사항 단위 %d개 생성", len(requirements))
    return requirements
