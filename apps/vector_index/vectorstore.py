import shutil
from pathlib import Path

from langchain_chroma import Chroma

from apps.vector_index.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
)


def reset_vectorstore() -> None:
    """
    기존 ChromaDB 저장 폴더를 삭제해서 벡터 DB를 초기화한다.

    이번 vector_index 앱은 cleaned JSON 기준으로
    매번 새 벡터 DB를 생성하는 목적이므로,
    기존 데이터를 유지하지 않고 초기화한다.
    """
    chroma_path = Path(CHROMA_DIR)

    if chroma_path.exists():
        shutil.rmtree(chroma_path)

    chroma_path.mkdir(parents=True, exist_ok=True)


def get_vectorstore(embedding_model) -> Chroma:
    """
    Chroma vectorstore 객체를 생성해서 반환한다.

    반환된 vectorstore에 add_documents(documents)를 호출하면,
    Document.page_content가 embedding_model을 통해 벡터로 변환되고
    ChromaDB에 저장된다.
    """
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model,
    )