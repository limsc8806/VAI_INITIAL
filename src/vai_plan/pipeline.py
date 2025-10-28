from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from . import catalog, commands, extractors, llm, processors, review
from .logging_utils import setup_logging, stage_logging

LOGGER = logging.getLogger(__name__)


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_pdf_path(requested: Optional[str], config: Dict[str, Any]) -> Path:
    pdf_override = Path(requested) if requested else None
    default_path = Path(config.get("inputs", {}).get("pdf_path", ""))
    pdf_path = pdf_override or default_path
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    return pdf_path


def build_run_context(config: Dict[str, Any]) -> Dict[str, Any]:
    run_id = datetime.utcnow().strftime("run_%Y%m%dT%H%M%SZ")
    processed_dir = Path(config.get("inputs", {}).get("processed_dir", "data/processed"))
    run_processed_dir = processed_dir / run_id
    run_processed_dir.mkdir(parents=True, exist_ok=True)
    return {
        "id": run_id,
        "processed_dir": run_processed_dir,
    }


def cache_json(run_context: Dict[str, Any], name: str, payload: Dict[str, Any]) -> Path:
    target = run_context["processed_dir"] / f"{name}.json"
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def run_pipeline(
    config_path: Path,
    pdf_path: Optional[str] = None,
) -> Dict[str, Any]:
    config = load_config(config_path)
    logging_cfg = config.get("logging", {})
    log_dir = setup_logging(
        base_dir=logging_cfg.get("base_dir", "logs"),
        level=logging_cfg.get("level", "INFO"),
    )
    commands_cfg = config.get("commands", {})

    context = build_run_context(config)
    LOGGER.info("실행 컨텍스트: %s", context["id"])

    target_pdf = ensure_pdf_path(pdf_path, config)
    LOGGER.info("대상 PDF: %s", target_pdf)

    # Extraction Stage
    with stage_logging("01_extraction", log_dir, logging_cfg.get("redact_fields")) as s_log:
        text_segments = extractors.extract_text(
            target_pdf,
            min_paragraph_length=config.get("extraction", {})
            .get("text", {})
            .get("min_paragraph_length", 20),
        )
        table_segments = extractors.extract_tables(
            target_pdf,
            engine=config.get("extraction", {}).get("tables", {}).get("engine", "camelot"),
            flavor=config.get("extraction", {}).get("tables", {}).get("flavor", "stream"),
        )
        figure_segments = extractors.extract_figures(target_pdf)

        s_log.log_json("text_segments", {"items": text_segments})
        s_log.log_json("table_segments", {"items": table_segments})
        s_log.log_json("figure_segments", {"items": figure_segments})
        cache_json(context, "text_segments", {"items": text_segments})
        cache_json(context, "table_segments", {"items": table_segments})
        cache_json(context, "figure_segments", {"items": figure_segments})

    # Chunking Stage
    with stage_logging("02_chunking", log_dir) as s_log:
        merged_chunks = processors.merge_artifacts(text_segments, table_segments, figure_segments)
        chunked_texts = processors.chunk_text(
            merged_chunks,
            max_characters=config.get("chunking", {}).get("max_characters", 2000),
            overlap_characters=config.get("chunking", {}).get("overlap_characters", 200),
        )
        s_log.log_json("merged_chunks", {"items": [c.__dict__ for c in merged_chunks]})
        s_log.log_json("chunked_texts", {"items": chunked_texts})
        cache_json(context, "merged_chunks", {"items": [c.__dict__ for c in merged_chunks]})
        cache_json(context, "chunked_texts", {"items": chunked_texts})

    # LLM Stage
    llm_cfg = config.get("llm", {})
    with stage_logging("03_llm_summarization", log_dir, logging_cfg.get("redact_fields")) as s_log:
        summarized = llm.summarize_chunks(
            chunked_texts,
            llm_cfg,
        )
        s_log.log_json("summaries", {"items": summarized})
        cache_json(context, "summaries", {"items": summarized})

    # Requirement Assembly
    with stage_logging("04_requirements", log_dir) as s_log:
        requirements = processors.build_requirements(chunked_texts, summarized)
        command_patterns = commands_cfg.get("patterns", [])
        commands.annotate_requirements_with_commands(
            requirements,
            chunked_texts,
            patterns=command_patterns,
            max_per_requirement=commands_cfg.get("max_per_requirement", 10),
        )
        whitelist_list = [
            cmd.get("name")
            for requirement in requirements
            for cmd in requirement.get("commands", [])
            if isinstance(cmd, dict)
        ]
        whitelist = whitelist_list or None
        inferred_matrix = commands.infer_compatibility_from_chunks(
            chunked_texts,
            command_patterns,
            command_whitelist=whitelist,
            positive_keywords=commands_cfg.get("sequence_positive_keywords"),
            negative_keywords=commands_cfg.get("sequence_negative_keywords"),
        )
        target_index = commands_cfg.get("target_requirement_index", 0)
        if inferred_matrix and 0 <= target_index < len(requirements):
            compatibility_payload = {
                "description": commands_cfg.get(
                    "compatibility_description", "Auto-inferred command transitions"
                ),
                "matrix": inferred_matrix,
                "default": commands_cfg.get("compatibility_default", "UNKNOWN"),
            }
            requirements[target_index]["compatibility_matrix"] = compatibility_payload
            if not requirements[target_index].get("commands"):
                inferred_names = set(inferred_matrix.keys())
                for mapping in inferred_matrix.values():
                    inferred_names.update(mapping.keys())
                sorted_names = sorted(inferred_names)
                max_count = commands_cfg.get("max_per_requirement", len(sorted_names))
                requirements[target_index]["commands"] = [
                    {"name": name} for name in sorted_names[:max_count]
                ]
        s_log.log_json("requirements", {"items": requirements})
        cache_json(context, "requirements", {"items": requirements})

    # Catalog & Review Output
    catalog_cfg = config.get("catalog", {})
    review_cfg = config.get("review", {})

    with stage_logging("05_outputs", log_dir) as s_log:
        generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        catalog_payload = catalog.build_catalog(
            requirements=requirements,
            schema_version=catalog_cfg.get("schema_version", "0.1.0"),
        )
        catalog_path = catalog.write_catalog(
            catalog_payload,
            Path(catalog_cfg.get("output_path", "artifacts/catalog.yaml")),
        )
        cache_json(context, "catalog_payload", catalog_payload)
        s_log.log_json("catalog_payload", catalog_payload)
        review_payload = review.build_review_document(
            requirements=requirements,
            include_traceability=review_cfg.get("include_traceability", True),
            metadata={
                "schema_version": review_cfg.get("schema_version", "review-0.1.0"),
                "generated_at": generated_at,
                "run_id": context["id"],
                "source_pdf": str(target_pdf.resolve()),
            },
        )
        review_path = review.write_review(
            review_payload,
            Path(review_cfg.get("output_path", "artifacts/review.yaml")),
        )
        command_names = commands.extract_command_names(
            catalog_payload,
            target_index=0,
        )
        compatibility_mapping, default_state = commands.extract_compatibility_mapping(
            catalog_payload,
            target_index=0,
        )
        compatibility_table = commands.build_sequential_compatibility_table(
            command_names,
            compatibility_mapping,
            default_state,
        )
        compatibility_csv_path = commands.write_compatibility_csv(
            compatibility_table,
            Path(commands_cfg.get("compatibility_csv_path", "artifacts/compatibility_matrix.csv")),
        )

        s_log.log_json(
            "artifacts",
            {
                "catalog_path": str(catalog_path),
                "review_path": str(review_path),
                "review_schema_version": review_cfg.get("schema_version", "review-0.1.0"),
                "review_generated_at": generated_at,
                "compatibility_csv_path": str(compatibility_csv_path),
            },
        )
        s_log.log_json("review_payload", review_payload)
        cache_json(context, "review_payload", review_payload)
        s_log.log_json(
            "compatibility_matrix",
            {
                "commands": command_names,
                "mapping": compatibility_mapping,
                "default": default_state,
                "csv_path": str(compatibility_csv_path),
            },
        )
        cache_json(
            context,
            "compatibility_matrix",
            {
                "commands": command_names,
                "mapping": compatibility_mapping,
                "default": default_state,
            },
        )

    return {
        "run_id": context["id"],
        "catalog_path": str(catalog_path),
        "review_path": str(review_path),
        "compatibility_csv_path": str(compatibility_csv_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VAI_PLAN 파이프라인 실행")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--pdf", type=str, help="대상 DDR5 PDF 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(args.config, args.pdf)


if __name__ == "__main__":
    main()
