import requests
import json

OLLAMA_API_BASE = "http://localhost:11434/v1"
MODEL = "phi3"  # Ollama에서 실행 중인 모델명

SYSTEM_PROMPT = "You are an expert verification engineer. Summarize DDR5 specification text into a concise requirement unit for DV coverage."
USER_PROMPT = "Summarize the following DDR5 specification excerpt into a JSON object with keys 'title', 'description', 'source_pages', and 'confidence'. Focus on verification intent and keep the description under six sentences.\nExcerpt (page 12):\nDDR5 initialization requires issuing MRS commands in sequence."

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ],
    "temperature": 0.2,
    "max_tokens": 512
}

response = requests.post(f"{OLLAMA_API_BASE}/chat/completions", json=payload)

print(f"Status: {response.status_code}")
try:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("응답 파싱 오류:", e)
    print(response.text)
