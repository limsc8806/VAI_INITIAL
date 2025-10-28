from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _normalize_command_entry(entry: Any, index: int) -> Dict[str, Any]:
    """
    내부 유틸: command 항목을 일관된 딕셔너리 형태로 정규화합니다.
    """
    if isinstance(entry, dict):
        name = entry.get("name") or entry.get("command") or f"command_{index + 1}"
        normalized = {"name": name}
        for key, value in entry.items():
            if key not in ("name",):
                normalized[key] = value
        return normalized
    if isinstance(entry, str):
        return {"name": entry}
    return {"name": f"command_{index + 1}", "raw": entry}


def extract_commands_from_catalog(
    catalog_payload: Dict[str, Any],
    target_index: int = 0,
    command_field: str = "commands",
) -> List[Dict[str, Any]]:
    """
    catalog YAML(딕셔너리)에서 첫 번째 requirement unit을 기준으로 command 리스트를 추출합니다.

    Args:
        catalog_payload: `catalog.yaml`을 로드한 딕셔너리.
        target_index: 요구사항 타깃 인덱스(기본값 0).
        command_field: 요구사항 단위 내부에서 command 리스트를 담고 있는 필드명.

    Returns:
        정규화된 command 딕셔너리 리스트.
    """
    units: List[Dict[str, Any]] = catalog_payload.get("requirement_units") or []
    if not units:
        return []
    if target_index < 0 or target_index >= len(units):
        return []

    target = units[target_index]
    commands: Any = target.get(command_field, [])

    if isinstance(commands, dict):
        iterable: Iterable[Any] = list(commands.values())
    elif isinstance(commands, list):
        iterable = commands
    else:
        iterable = [commands]

    normalized: List[Dict[str, Any]] = []
    for idx, entry in enumerate(iterable):
        normalized.append(_normalize_command_entry(entry, idx))
    return normalized


def extract_command_names(
    catalog_payload: Dict[str, Any],
    target_index: int = 0,
    command_field: str = "commands",
) -> List[str]:
    """
    catalog에서 command 이름 문자열만 추출합니다.
    """
    commands = extract_commands_from_catalog(
        catalog_payload=catalog_payload,
        target_index=target_index,
        command_field=command_field,
    )
    return [command["name"] for command in commands]


def extract_compatibility_mapping(
    catalog_payload: Dict[str, Any],
    target_index: int = 0,
    field: str = "compatibility_matrix",
) -> Tuple[Dict[str, Dict[str, Any]], Optional[Any]]:
    """catalog에서 호환성 매핑 정보를 추출합니다."""
    units: List[Dict[str, Any]] = catalog_payload.get("requirement_units") or []
    if not units:
        return {}, None
    if target_index < 0 or target_index >= len(units):
        return {}, None

    raw_matrix = units[target_index].get(field) or {}
    if isinstance(raw_matrix, dict):
        matrix_data = raw_matrix.get("matrix", {})
        default_value = raw_matrix.get("default")
    else:
        matrix_data = {}
        default_value = None

    parsed: Dict[str, Dict[str, Any]] = {}
    if isinstance(matrix_data, dict):
        for row_key, row_map in matrix_data.items():
            if isinstance(row_map, dict):
                parsed[row_key] = dict(row_map)
    return parsed, default_value


def build_sequential_compatibility_table(
    command_names: List[str],
    compatibility_mapping: Dict[str, Dict[str, Any]],
    default_value: Optional[Any] = None,
) -> List[List[str]]:
    """
    커맨드 순차 실행 가능성 테이블(upper triangular)을 생성합니다.
    행: 선행 커맨드, 열: 후속 커맨드.
    """
    header = [""] + command_names
    table: List[List[str]] = [header]

    for i, row_cmd in enumerate(command_names):
        row: List[str] = [row_cmd]
        for j, col_cmd in enumerate(command_names):
            if j <= i:
                row.append("-")
                continue
            value = None
            row_map = compatibility_mapping.get(row_cmd, {})
            if isinstance(row_map, dict):
                value = row_map.get(col_cmd)
            if value is None:
                value = default_value if default_value is not None else "UNKNOWN"
            row.append(str(value))
        table.append(row)
    return table


def write_compatibility_csv(table: List[List[str]], output_path: Path) -> Path:
    """호환성 테이블을 CSV 파일로 저장합니다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row in table:
            writer.writerow(row)
    return output_path


def find_command_tokens(
    text: str,
    patterns: Sequence[str],
    *,
    deduplicate: bool = False,
    with_span: bool = False,
) -> List[Any]:
    compiled = [re.compile(pattern) for pattern in patterns or []]
    matches: List[Tuple[int, int, str]] = []
    for regex in compiled:
        for match in regex.finditer(text or ""):
            matches.append((match.start(), match.end(), match.group(0)))
    matches.sort(key=lambda item: item[0])

    tokens: List[Any] = []
    seen: set[str] = set()
    for start, end, token in matches:
        if deduplicate and token in seen:
            continue
        seen.add(token)
        if with_span:
            tokens.append({"token": token, "start": start, "end": end})
        else:
            tokens.append(token)
    return tokens


def find_commands_in_text(
    text: str,
    patterns: Sequence[str],
) -> List[str]:
    """
    주어진 텍스트에서 패턴에 해당하는 command 토큰을 추출합니다.
    """
    return find_command_tokens(text, patterns, deduplicate=True, with_span=False)


def annotate_requirements_with_commands(
    requirements: List[Dict[str, Any]],
    chunked_texts: List[Dict[str, Any]],
    patterns: Optional[Sequence[str]] = None,
    max_per_requirement: int = 10,
) -> None:
    """
    청크 텍스트를 기준으로 요구사항에 관련 command 리스트를 채웁니다.
    """
    if not patterns:
        patterns = [r"\bCMD_[A-Z0-9]+\b"]

    for idx, requirement in enumerate(requirements):
        text = ""
        if idx < len(chunked_texts):
            text = chunked_texts[idx].get("text", "") or ""
        found = find_command_tokens(
            text,
            patterns,
            deduplicate=True,
            with_span=False,
        )[:max_per_requirement]
        if found:
            requirement["commands"] = [{"name": name} for name in found]


def infer_compatibility_from_chunks(
    chunked_texts: List[Dict[str, Any]],
    patterns: Sequence[str],
    *,
    command_whitelist: Optional[Iterable[str]] = None,
    positive_keywords: Optional[Sequence[str]] = None,
    negative_keywords: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, str]]:
    """
    청크 텍스트에서 command 순서를 분석하여 호환성 매트릭스를 추정합니다.
    """
    whitelist = set(command_whitelist) if command_whitelist else None
    positives = [kw.lower() for kw in (positive_keywords or ["->", "→", "⇒", "then", "after", "followed by"])]
    negatives = [kw.lower() for kw in (negative_keywords or ["must not follow", "cannot follow", "not followed by", "should not follow"])]

    matrix: Dict[str, Dict[str, str]] = {}

    for chunk in chunked_texts:
        text = chunk.get("text", "") or ""
        if not text:
            continue
        tokens = find_command_tokens(
            text,
            patterns,
            deduplicate=False,
            with_span=True,
        )
        if len(tokens) < 2:
            continue

        lower_text = text.lower()
        for idx in range(len(tokens) - 1):
            first = tokens[idx]
            second = tokens[idx + 1]
            src = first["token"]
            dst = second["token"]

            if src == dst:
                continue
            if whitelist and (src not in whitelist or dst not in whitelist):
                continue

            between = lower_text[first["end"]:second["start"]]
            neg_hit = any(keyword in between for keyword in negatives if keyword)
            pos_hit = any(keyword in between for keyword in positives if keyword)

            matrix.setdefault(src, {})
            current = matrix[src].get(dst)
            if neg_hit:
                matrix[src][dst] = "N"
            else:
                if current == "N":
                    continue
                if pos_hit or not positives:
                    matrix[src][dst] = "Y"
                else:
                    matrix[src].setdefault(dst, "Y")

    return matrix
