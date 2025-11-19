# 환경/모듈 설치 자동화 스크립트 (Windows)

# 필수 Python 패키지 설치
python -m pip install --upgrade pip
pip install pymupdf camelot-py[cv] pdfplumber openai vllm

# LLM API Key 환경변수 체크
if not defined OPENAI_API_KEY (
    echo [ERROR] 환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다.
    exit /b 1
)

echo [INFO] 환경 및 모듈 설치 완료
