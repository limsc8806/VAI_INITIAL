from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


def setup_logging(
    base_dir: str,
    level: str = "INFO",
) -> Path:
    """Configure root logger and ensure log directory exists."""
    log_dir = Path(base_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    file_handler = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

    logging.debug("로그 디렉토리 %s 설정 완료", log_dir)
    return log_dir


def _sanitize_filename(name: str) -> str:
    return "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip("_")


def _dump_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


class StageLogger:
    """Helper to persist structured snapshots per pipeline stage."""

    def __init__(
        self,
        stage_name: str,
        log_dir: Path,
        redact_fields: Optional[list[str]] = None,
    ) -> None:
        self.stage_name = _sanitize_filename(stage_name)
        self.log_dir = log_dir
        self.redact_fields = set(redact_fields or [])
        self._stage_path = log_dir / self.stage_name

    def log_json(self, name: str, payload: Dict[str, Any]) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        sanitized = _sanitize_filename(name)
        file_path = self._stage_path / f"{timestamp}_{sanitized}.json"
        redacted_payload = self._redact(payload)
        _dump_json(file_path, redacted_payload)
        logging.getLogger(__name__).debug(
            "Stage %s: %s 저장 (%s)", self.stage_name, sanitized, file_path
        )
        return file_path

    def log_markdown(self, name: str, content: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        sanitized = _sanitize_filename(name)
        file_path = self._stage_path / f"{timestamp}_{sanitized}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logging.getLogger(__name__).debug(
            "Stage %s: %s 저장 (%s)", self.stage_name, sanitized, file_path
        )
        return file_path

    def _redact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.redact_fields:
            return payload
        redacted = {}
        for key, value in payload.items():
            if key in self.redact_fields:
                redacted[key] = "<redacted>"
            elif isinstance(value, dict):
                redacted[key] = self._redact(value)
            else:
                redacted[key] = value
        return redacted


@contextmanager
def stage_logging(
    name: str,
    log_dir: Path,
    redact_fields: Optional[list[str]] = None,
) -> Iterator[StageLogger]:
    """Context manager to automatically log stage boundaries."""
    logger = logging.getLogger(__name__)
    stage_logger = StageLogger(name, log_dir, redact_fields=redact_fields)
    logger.info("▶️  Stage 시작: %s", name)
    try:
        yield stage_logger
    finally:
        logger.info("✅ Stage 완료: %s", name)
