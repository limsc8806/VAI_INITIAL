from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

LOGGER = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert verification engineer. Summarize DDR5 specification text "
    "into a concise requirement unit for DV coverage. Produce a short structured JSON "
    "capturing key verification intent."
)
DEFAULT_USER_TEMPLATE = (
    "Summarize the following DDR5 specification excerpt into a JSON object with keys "
    '`"title"`, `"description"`, `"source_pages"` (array of ints), and `"confidence"` '
    "(float between 0 and 1). Keep the description within 6 sentences and focus on "
    "verification-relevant behavior.\n\n"
    "### Excerpt (page {start_page}):\n{chunk_text}\n"
)

try:  # pragma: no cover - optional dependency
    from openai import OpenAI  # type: ignore

    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore
    _OPENAI_AVAILABLE = False


def redact_terms(text: str, terms: Iterable[str]) -> str:
    """민감한 용어를 마스킹합니다."""
    redacted = text
    for term in terms:
        if term:
            redacted = redacted.replace(term, "[REDACTED]")
    return redacted


def summarize_chunks(
    chunked_texts: Iterable[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    LLM 요약 엔트리포인트.

    * `config.provider`가 `openai`이고 API 키가 유효하면 실제 요청
    * 그 외에는 스텁 요약으로 대체
    """
    if not config.get("enable_summary", True):
        LOGGER.info("LLM 요약이 비활성화되어 스텁 결과를 반환합니다.")
        return _fallback_summaries(chunked_texts)

    provider = (config.get("provider") or "").lower()
    if provider == "openai":
        summaries = _summarize_with_openai(chunked_texts, config)
        if summaries is not None:
            return summaries
        LOGGER.warning("OpenAI 요약 실패. 스텁 요약으로 대체합니다.")
    else:
        LOGGER.info("지원되지 않는 LLM provider '%s'. 스텁 요약 사용.", provider)

    return _fallback_summaries(chunked_texts)


def _summarize_with_openai(
    chunked_texts: Iterable[Dict[str, Any]],
    config: Dict[str, Any],
) -> Optional[List[Dict[str, Any]]]:
    if not _OPENAI_AVAILABLE:
        LOGGER.warning("openai 패키지가 설치되지 않아 실제 호출을 건너뜁니다.")
        return None

    api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        LOGGER.warning("환경변수 %s 에서 OpenAI API 키를 찾을 수 없습니다.", api_key_env)
        return None

    try:
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        api_base = config.get("api_base")
        if api_base:
            client_kwargs["base_url"] = api_base
        client = OpenAI(**client_kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("OpenAI 클라이언트 초기화 실패: %s", exc, exc_info=True)
        return None

    system_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    user_template = config.get("user_prompt_template", DEFAULT_USER_TEMPLATE)
    temperature = float(config.get("temperature", 0.2))
    max_tokens = int(config.get("max_tokens", 1024))
    model = config.get("model", "gpt-4o-mini")

    summaries: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunked_texts, start=1):
        text = chunk.get("text", "") or ""
        metadata = chunk.get("metadata", {}) or {}
        start_page = metadata.get("start_page", "unknown")
        user_prompt = user_template.format(
            chunk_index=idx,
            start_page=start_page,
            chunk_text=text.strip(),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""
        except Exception as exc:  # pragma: no cover - network failure fallback
            LOGGER.warning("OpenAI API 호출 실패: %s", exc, exc_info=True)
            return None

        summary = _parse_llm_response(content, chunk, idx)
        summary["llm_prompt"] = user_prompt
        summary["llm_response"] = content
        summary["model"] = model
        summaries.append(summary)

    return summaries


def _parse_llm_response(
    response_text: str,
    chunk: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    clean = response_text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean, count=1).strip()
        clean = re.sub(r"```$", "", clean).strip()

    data: Dict[str, Any] = {}
    if clean:
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            LOGGER.debug("LLM 응답이 JSON 파싱에 실패했습니다. 원문을 설명으로 사용합니다.")

    text = chunk.get("text", "") or ""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    title = data.get("title") or (first_line[:60] if first_line else f"요약 {index}")
    description = data.get("description") or (clean if clean else text[:500])
    source_pages = data.get("source_pages") or []
    if isinstance(source_pages, int):
        source_pages = [source_pages]
    elif not isinstance(source_pages, list):
        source_pages = []

    metadata = chunk.get("metadata", {}) or {}
    if not source_pages and metadata.get("start_page") is not None:
        source_pages = [metadata.get("start_page")]

    confidence_raw = data.get("confidence", 0.7)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.7

    return {
        "title": title,
        "description": description,
        "source_pages": source_pages,
        "evidence": metadata,
        "confidence": confidence,
    }


def _fallback_summaries(
    chunked_texts: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunked_texts, start=1):
        text = chunk.get("text", "") or ""
        metadata = chunk.get("metadata", {}) or {}
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        summaries.append(
            {
                "title": first_line[:60] or f"요약 {idx}",
                "description": text[:500],
                "source_pages": [
                    metadata.get("start_page"),
                ],
                "evidence": metadata,
                "confidence": 0.5,
                "llm_prompt": "<stubbed>",
                "llm_response": "<stubbed>",
            }
        )
    return summaries
