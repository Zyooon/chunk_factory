import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./vector_data/chroma")
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "beauty_hair_rag")
HF_EMBEDDING_MODEL: str = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-m3")
GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ------------------------------------------------------------
# 고객 정보 사전 설정
# ------------------------------------------------------------
# 챗봇 실행 전 고객 정보를 미리 입력해 두세요.
#
# USER_GENDER       : 남성 / 여성
# USER_FACE_SHAPE   : 계란형 / 둥근형 / 각진형 / 장방형 / 역삼각형
# USER_FACE_PROPORTION : 균형 / 상안부_긴형 / 중안부_긴형 / 하안부_긴형
USER_GENDER: str = "여성"
USER_FACE_SHAPE: str = "둥근형"
USER_FACE_PROPORTION: str = "균형"
