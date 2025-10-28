from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml


def build_catalog(
    requirements: List[Dict[str, object]],
    schema_version: str,
) -> Dict[str, object]:
    """커버리지 카탈로그 YAML 페이로드를 구성합니다."""
    return {
        "schema_version": schema_version,
        "requirement_units": requirements,
        "metadata": {
            "total_units": len(requirements),
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
