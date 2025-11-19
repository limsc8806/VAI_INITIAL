from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml


def build_catalog(
    requirements: List[Dict[str, object]],
    schema_version: str,
    chunks: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    """커버리지 카탈로그 YAML 페이로드를 구성합니다.

    확장:
      - structured_chunks: 텍스트/표/그림 청크 스키마 (models.Chunk 기반)
      - requirements와 별도로 원시/구조 청크를 참조하여 추후 재처리 또는 리치 UI에 활용
    """
    structured = []
    for c in (chunks or []):
        # Pydantic 객체 혹은 dict 모두 수용
        if hasattr(c, "dict"):
            structured.append(c.dict())  # type: ignore[attr-defined]
        else:
            structured.append(dict(c))
    return {
        "schema_version": schema_version,
        "requirement_units": requirements,
        "structured_chunks": structured,
        "metadata": {
            "total_units": len(requirements),
            "total_chunks": len(structured),
        },
    }


def write_catalog(catalog: Dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            catalog,
            handle,
            sort_keys=False,
            allow_unicode=True,
        )
    return output_path
