from pathlib import Path
import os

from dotenv import load_dotenv


# 프로젝트 루트의 .env 파일 로드
load_dotenv()


# 프로젝트 루트 디렉토리
# apps/rag_core/config.py 기준으로 parents[2]가 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parents[2]


# =========================
# ChromaDB 설정
# =========================

CHROMA_DIR = os.getenv(
    "CHROMA_DIR",
    str(BASE_DIR / "vector_data" / "chroma"),
)

CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "beauty_rag",
)


# =========================
# Embedding 설정
# =========================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "bge-m3",
)


# =========================
# Gemini 설정
# =========================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_CHAT_MODEL = os.getenv(
    "GEMINI_CHAT_MODEL",
    "gemini-2.5-flash",
)


# =========================
# Retrieval 기본값
# =========================

DEFAULT_RETRIEVAL_K = int(
    os.getenv("DEFAULT_RETRIEVAL_K", "5")
)

DEFAULT_FALLBACK_MIN_RESULTS = int(
    os.getenv("DEFAULT_FALLBACK_MIN_RESULTS", "1")
)