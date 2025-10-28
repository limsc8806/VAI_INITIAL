from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vai_plan import llm


def test_summarize_chunks_fallback_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    chunked = [
        {
            "text": "DDR5 initialization requires issuing MRS commands in sequence.",
            "metadata": {"start_page": 12},
        }
    ]
    config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "enable_summary": True,
    }

    summaries = llm.summarize_chunks(chunked, config)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["title"]
    assert summary["description"]
    assert summary["llm_prompt"] == "<stubbed>"
    assert summary["llm_response"] == "<stubbed>"
