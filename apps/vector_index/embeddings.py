from langchain_ollama import OllamaEmbeddings

from apps.vector_index.config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
)


def get_embedding_model() -> OllamaEmbeddings:
    """
    어떤 임베딩 모델을 쓸지, 해당 모델 자체를 반환하는 함수
    임베딩 과정은 해당 함수에서는 진행되지 않는다.

    이 모델은 Document.page_content를 벡터로 변환할 때 사용된다.
    """
    return OllamaEmbeddings(
        model=OLLAMA_EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )