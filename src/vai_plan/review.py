from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def build_review_document(
    requirements: List[Dict[str, object]],
    include_traceability: bool = True,
    metadata: Optional[Dict[str, object]] = None,
    chunks: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    metadata = metadata or {}
    generated_at = metadata.get("generated_at", datetime.utcnow().isoformat(timespec="seconds") + "Z")

    document: Dict[str, object] = {
        "metadata": {
            "schema_version": metadata.get("schema_version", "0.1.0"),
            "generated_at": generated_at,
            "run_id": metadata.get("run_id", "unknown"),
            "source_pdf": metadata.get("source_pdf", "unknown"),
        },
        "summary": {
            "total_requirements": len(requirements),
        },
        "requirements": [],
    }

    for req in requirements:
        entry: Dict[str, object] = {
            "id": req["id"],
            "title": req.get("title", "제목 없음"),
            "description": req.get("description", ""),
            "confidence": req.get("confidence", "N/A"),
        }
        if include_traceability:
            pages = req.get("source_pages") or req.get("evidence", {}).get("source_pages")
            entry["source_pages"] = pages
        if "evidence" in req:
            entry["evidence"] = req["evidence"]
        document["requirements"].append(entry)
    # 부록: 청크 요약 섹션(선택)
    if chunks:
        try:
            sample = []
            for c in chunks[:20]:  # 상위 20개만 요약 표기
                if hasattr(c, "get"):
                    sample.append({
                        "type": c.get("type"),
                        "page": c.get("source", {}).get("page"),
                        "id": c.get("id"),
                    })
            document["chunks_overview"] = {
                "count": len(chunks),
                "sample": sample,
            }
        except Exception:
            pass
    return document


def write_review(review_payload: Dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            review_payload,
            handle,
            sort_keys=False,
            allow_unicode=True,
        )
    return output_path
