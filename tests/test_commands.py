from __future__ import annotations

import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vai_plan.commands import (
    extract_command_names,
    extract_commands_from_catalog,
    extract_compatibility_mapping,
    build_sequential_compatibility_table,
    write_compatibility_csv,
    find_commands_in_text,
    annotate_requirements_with_commands,
    infer_compatibility_from_chunks,
)


def test_extract_commands_from_catalog_basic() -> None:
    catalog_payload = {
        "schema_version": "0.1.0",
        "requirement_units": [
            {
                "id": "REQ-0001",
                "title": "Command execution",
                "commands": [
                    {"name": "CMD_INIT", "description": "Initialize module"},
                    {"command": "CMD_START", "timeout": 5},
                    "CMD_STOP",
                ],
            },
            {
                "id": "REQ-0002",
                "title": "Other requirement",
            },
        ],
    }

    commands = extract_commands_from_catalog(catalog_payload)

    assert len(commands) == 3
    assert commands[0]["name"] == "CMD_INIT"
    assert commands[1]["name"] == "CMD_START"
    assert commands[1]["timeout"] == 5
    assert commands[2]["name"] == "CMD_STOP"


def test_extract_command_names_empty_catalog_returns_empty_list() -> None:
    catalog_payload = {
        "schema_version": "0.1.0",
        "requirement_units": [],
    }
    assert extract_command_names(catalog_payload) == []


def test_extract_commands_invalid_index_returns_empty_list() -> None:
    catalog_payload = {
        "schema_version": "0.1.0",
        "requirement_units": [
            {
                "id": "REQ-0001",
            }
        ],
    }
    assert extract_commands_from_catalog(catalog_payload, target_index=5) == []


def test_extract_compatibility_mapping_and_table(tmp_path) -> None:
    catalog_payload = {
        "requirement_units": [
            {
                "commands": [
                    {"name": "CMD_A"},
                    {"name": "CMD_B"},
                    {"name": "CMD_C"},
                ],
                "compatibility_matrix": {
                    "matrix": {
                        "CMD_A": {"CMD_B": "Y", "CMD_C": "N"},
                        "CMD_B": {"CMD_C": "Y"},
                    },
                    "default": "UNKNOWN",
                },
            }
        ]
    }

    command_names = extract_command_names(catalog_payload)
    mapping, default_value = extract_compatibility_mapping(catalog_payload)
    table = build_sequential_compatibility_table(command_names, mapping, default_value)

    assert table[0] == ["", "CMD_A", "CMD_B", "CMD_C"]
    # Row CMD_A
    assert table[1] == ["CMD_A", "-", "Y", "N"]
    # Row CMD_B (CMD_C is after CMD_B)
    assert table[2] == ["CMD_B", "-", "-", "Y"]
    # Row CMD_C (no later commands)
    assert table[3] == ["CMD_C", "-", "-", "-"]

    csv_path = tmp_path / "compatibility.csv"
    write_compatibility_csv(table, csv_path)

    with csv_path.open("r", encoding="utf-8") as handle:
        reader = list(csv.reader(handle))
    assert reader == [
        ["", "CMD_A", "CMD_B", "CMD_C"],
        ["CMD_A", "-", "Y", "N"],
        ["CMD_B", "-", "-", "Y"],
        ["CMD_C", "-", "-", "-"],
    ]


def test_find_commands_and_annotation():
    text = "Sequence: CMD_INIT -> CMD_START -> CMD_STOP. Timing per MRR command."
    patterns = [r"\bCMD_[A-Z0-9]+\b", r"\bMRR\b"]
    found = find_commands_in_text(text, patterns)
    assert found == ["CMD_INIT", "CMD_START", "CMD_STOP", "MRR"]

    requirements = [
        {"id": "REQ-0001", "description": "Sample"},
        {"id": "REQ-0002", "description": "No command"},
    ]
    chunked = [
        {"text": text},
        {"text": "Just prose"},
    ]
    annotate_requirements_with_commands(requirements, chunked, patterns, max_per_requirement=3)

    assert "commands" in requirements[0]
    assert requirements[0]["commands"][0]["name"] == "CMD_INIT"
    assert "commands" not in requirements[1]


def test_infer_compatibility_from_chunks():
    chunked = [
        {
            "text": "CMD_INIT -> CMD_START then CMD_STOP. CMD_STOP must not follow CMD_INIT.",
        }
    ]
    patterns = [r"\bCMD_[A-Z0-9]+\b"]
    mapping = infer_compatibility_from_chunks(
        chunked,
        patterns,
        command_whitelist=["CMD_INIT", "CMD_START", "CMD_STOP"],
        positive_keywords=["->", "then"],
        negative_keywords=["must not follow"],
    )
    assert mapping["CMD_INIT"]["CMD_START"] == "Y"
    assert mapping["CMD_START"]["CMD_STOP"] == "Y"
    assert mapping["CMD_STOP"]["CMD_INIT"] == "N"
