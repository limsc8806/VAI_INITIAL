import requests
import json
import re
from typing import List, Dict, Any

def validate_llm_response(response_text: str) -> bool:
    """응답이 요구 JSON 스키마에 맞는지 검증. confidence는 float/int 또는 'high'/'medium'/'low' 문자열 허용."""
    clean = response_text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean, count=1).strip()
        clean = re.sub(r"```$", "", clean).strip()
    try:
        data = json.loads(clean)
    except Exception:
        return False
    required = ["title", "description", "source_pages", "confidence"]
    if not all(k in data for k in required):
        return False
    conf = data["confidence"]
    if not (isinstance(conf, float) or isinstance(conf, int) or (isinstance(conf, str) and conf.lower() in ["high", "medium", "low"])):
        return False
    return True

OLLAMA_API_BASE = "http://localhost:11434/v1"
MODEL = "phi3"
SYSTEM_PROMPT = "You are an expert verification engineer. Summarize DDR5 specification text into a concise requirement unit for DV coverage."
PROMPTS = [
    "DDR5 initialization requires issuing MRS commands in sequence.",
    "The memory controller must support auto-refresh cycles as described in section 4.2.",
    "Timing parameters for WRITE operations are specified in Table 3-2.",
    "Bank group interleaving is mandatory for high-speed operation.",
    "Power-down entry and exit sequences must follow the JEDEC standard."
]

results: List[Dict[str, Any]] = []
for idx, user_text in enumerate(PROMPTS, start=1):
    user_prompt = f"Summarize the following DDR5 specification excerpt into a JSON object with keys 'title', 'description', 'source_pages', and 'confidence'. Focus on verification intent and keep the description under six sentences.\nExcerpt (page {idx}):\n{user_text}"
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 512
    }
    response = requests.post(f"{OLLAMA_API_BASE}/chat/completions", json=payload)
    status = response.status_code
    content = ""
    try:
        data = response.json()
        if "choices" in data and data["choices"]:
            content = data["choices"][0]["message"]["content"]
    except Exception:
        content = response.text
    valid = validate_llm_response(content)
    results.append({
        "prompt": user_text,
        "status": status,
        "valid_json": valid,
        "response": content
    })

for r in results:
    print(f"Prompt: {r['prompt']}")
    print(f"Status: {r['status']}, Valid JSON: {r['valid_json']}")
    print(r['response'])
    print("-"*60)
