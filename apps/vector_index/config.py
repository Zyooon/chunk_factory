# apps/vector_index/config.py

from pathlib import Path
import os

from dotenv import load_dotenv


# .env 파일 로드
load_dotenv()


# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parents[2]


# ChromaDB 저장 경로
CHROMA_DIR = os.getenv(
    "CHROMA_DIR",
    str(BASE_DIR / "vector_data" / "chroma"),
)


# ChromaDB 컬렉션 이름
CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "beauty_rag",
)


# Ollama 서버 주소
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)


# Ollama 임베딩 모델명
OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "bge-m3",
)