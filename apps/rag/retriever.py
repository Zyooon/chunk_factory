from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from apps.rag.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    HF_EMBEDDING_MODEL,
)


def _get_db() -> Chroma:
    embeddings = HuggingFaceEmbeddings(
        model_name=HF_EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def _search(db: Chroma, query: str, k: int, filter_dict: dict) -> list[Document]:
    try:
        return db.similarity_search(query, k=k, filter=filter_dict)
    except Exception:
        return []


def retrieve_docs(
    query: str,
    gender: str,
    face_shape: str,
    face_proportion: str,
    k: int = 5,
) -> tuple[list[Document], str]:
    db = _get_db()

    # 단계별 fallback 전략 (조건이 많은 것부터 줄여나감)
    stages: list[tuple[str, dict]] = [
        (
            "gender+face_shape+face_proportion",
            {"$and": [
                {"gender": {"$eq": gender}},
                {"face_shape": {"$eq": face_shape}},
                {"face_proportion": {"$eq": face_proportion}},
            ]},
        ),
        (
            "gender+face_shape",
            {"$and": [
                {"gender": {"$eq": gender}},
                {"face_shape": {"$eq": face_shape}},
            ]},
        ),
        (
            "face_shape",
            {"face_shape": {"$eq": face_shape}},
        ),
        (
            "category=hair",
            {"category": {"$eq": "hair"}},
        ),
    ]

    for stage_name, filter_dict in stages:
        results = _search(db, query, k, filter_dict)
        if results:
            return results, stage_name

    return [], "no_result"
