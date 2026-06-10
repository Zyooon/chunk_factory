# apps/rag_core/retriever.py

from typing import Any

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from apps.rag_core.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    DEFAULT_RETRIEVAL_K,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
)
from apps.rag_core.schemas import RetrievalQuery, RetrievalResult
from apps.rag_core.utils import (
    clean_metadata_filter,
    scored_documents_to_retrieved_documents,
)


CATEGORY_HAIR = "hair"
CATEGORY_MAKEUP = "makeup"


def get_embedding_model() -> OllamaEmbeddings:
    """
    ChromaDB 검색에 사용할 embedding model을 생성한다.

    vector_index에서 DB를 만들 때 사용한 embedding model과
    rag_core에서 검색할 때 사용하는 embedding model은 같아야 한다.

    현재 기준:
    - Ollama
    - bge-m3
    """

    return OllamaEmbeddings(
        model=OLLAMA_EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )


def get_vectorstore() -> Chroma:
    """
    vector_index가 생성한 ChromaDB collection에 연결한다.

    주의:
    - 여기서는 새 DB를 만드는 것이 아니라 기존 DB를 읽어 검색한다.
    - CHROMA_DIR, CHROMA_COLLECTION_NAME은 vector_index와 동일해야 한다.
    """

    embedding_model = get_embedding_model()

    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model,
    )


def get_covered_style_codes() -> set[str]:
    """
    ChromaDB에 실제 데이터가 있는 style_code 집합을 반환한다.

    새 done.json 스키마에서는 스타일 1개가 Document 1개로 저장되고,
    metadata에도 단수 필드인 style_code가 저장된다.
    """
    vs = get_vectorstore()
    result = vs.get(include=["metadatas"])
    covered: set[str] = set()

    for meta in result.get("metadatas", []):
        if not isinstance(meta, dict):
            continue

        code = meta.get("style_code")
        if isinstance(code, str):
            code = code.strip()

        if code:
            covered.add(str(code))

    return covered


def build_hair_fallback_filters(
    *,
    category: str,
    gender: str | None = None,
    face_shape: str | None = None,
    face_proportion: str | None = None,
    style_code: str | None = None,
) -> list[dict[str, Any]]:
    """
    hair 검색용 fallback metadata filter 목록을 만든다.

    보고서 기준 fallback 순서:

    1차: category + gender + face_shape + face_proportion + style_code
    2차: category + gender + face_shape + style_code
    3차: category + face_shape + style_code
    4차: category + style_code
    5차: category + gender + face_shape
    6차: category + face_shape
    7차: category

    style_code가 None이면 style_code 조건은 자동으로 제거된다.
    """

    raw_filters = [
        {
            "category": category,
            "gender": gender,
            "face_shape": face_shape,
            "face_proportion": face_proportion,
            "style_code": style_code,
        },
        {
            "category": category,
            "gender": gender,
            "face_shape": face_shape,
            "style_code": style_code,
        },
        {
            "category": category,
            "face_shape": face_shape,
            "style_code": style_code,
        },
        {
            "category": category,
            "style_code": style_code,
        },
        {
            "category": category,
            "gender": gender,
            "face_shape": face_shape,
        },
        {
            "category": category,
            "face_shape": face_shape,
        },
        {
            "category": category,
        },
    ]

    cleaned_filters: list[dict[str, Any]] = []

    for raw_filter in raw_filters:
        cleaned_filter = clean_metadata_filter(raw_filter)

        if cleaned_filter not in cleaned_filters:
            cleaned_filters.append(cleaned_filter)

    return cleaned_filters


def build_makeup_fallback_filters(
    *,
    category: str,
    gender: str | None = None,
    personal_color: str | None = None,
    style_code: str | None = None,
    makeup_group: str | None = None,
) -> list[dict[str, Any]]:
    """
    makeup 검색용 fallback metadata filter 목록을 만든다.

    메이크업 검색에서는 face_shape, face_proportion을 사용하지 않는다.

    설계도 기준 fallback 순서:

    1차: category + gender + personal_color + style_code
    2차: category + personal_color + style_code
    3차: category + gender + personal_color + makeup_group
    4차: category + personal_color + makeup_group
    5차: category + gender + personal_color
    6차: category + personal_color
    7차: category

    style_code가 있으면 style_code 조건을 우선 사용하고,
    style_code가 없거나 검색되지 않으면 makeup_group 조건으로 fallback한다.
    """

    raw_filters = [
        {
            "category": category,
            "gender": gender,
            "personal_color": personal_color,
            "style_code": style_code,
        },
        {
            "category": category,
            "personal_color": personal_color,
            "style_code": style_code,
        },
        {
            "category": category,
            "gender": gender,
            "personal_color": personal_color,
            "makeup_group": makeup_group,
        },
        {
            "category": category,
            "personal_color": personal_color,
            "makeup_group": makeup_group,
        },
        {
            "category": category,
            "gender": gender,
            "personal_color": personal_color,
        },
        {
            "category": category,
            "personal_color": personal_color,
        },
        {
            "category": category,
        },
    ]

    cleaned_filters: list[dict[str, Any]] = []

    for raw_filter in raw_filters:
        cleaned_filter = clean_metadata_filter(raw_filter)

        if cleaned_filter not in cleaned_filters:
            cleaned_filters.append(cleaned_filter)

    return cleaned_filters


def search_with_fallback(
    vectorstore,
    query: str,
    fallback_filters: list[dict[str, Any]],
    k: int,
) -> RetrievalResult:
    """
    fallback filter를 순서대로 적용하면서 ChromaDB 검색을 수행한다.

    첫 번째로 검색 결과가 나온 단계에서 멈춘다.
    """

    for stage_index, metadata_filter in enumerate(fallback_filters, start=1):
        chroma_filter = convert_to_chroma_filter(metadata_filter)

        scored_documents = vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=chroma_filter,
        )

        if scored_documents:
            retrieved_documents = scored_documents_to_retrieved_documents(
                scored_documents
            )

            return RetrievalResult(
                query=query,
                documents=retrieved_documents,
                retrieved_count=len(retrieved_documents),
                fallback_stage=stage_index,
                used_filter=metadata_filter,
            )

    return RetrievalResult(
        query=query,
        documents=[],
        retrieved_count=0,
        fallback_stage="none",
        used_filter={},
    )


def _retrieve_docs_with_vectorstore(
    retrieval_query: RetrievalQuery,
    vectorstore,
) -> RetrievalResult:
    """이미 생성된 vectorstore를 받아 단건 검색을 수행하는 내부 함수."""

    category = retrieval_query.category or CATEGORY_HAIR
    k = retrieval_query.k or DEFAULT_RETRIEVAL_K

    if category == CATEGORY_HAIR:
        fallback_filters = build_hair_fallback_filters(
            category=category,
            gender=retrieval_query.gender,
            face_shape=retrieval_query.face_shape,
            face_proportion=retrieval_query.face_proportion,
            style_code=retrieval_query.style_code,
        )
    elif category == CATEGORY_MAKEUP:
        fallback_filters = build_makeup_fallback_filters(
            category=category,
            gender=retrieval_query.gender,
            personal_color=retrieval_query.personal_color,
            style_code=retrieval_query.style_code,
            makeup_group=retrieval_query.makeup_group,
        )
    else:
        raise ValueError(
            f"지원하지 않는 category입니다. 입력된 category: {category}"
        )

    return search_with_fallback(
        vectorstore=vectorstore,
        query=retrieval_query.query,
        fallback_filters=fallback_filters,
        k=k,
    )


def retrieve_docs(
    retrieval_query: RetrievalQuery | None = None,
    *,
    query: str | None = None,
    category: str = CATEGORY_HAIR,
    gender: str | None = None,
    face_shape: str | None = None,
    face_proportion: str | None = None,
    personal_color: str | None = None,
    makeup_group: str | None = None,
    style_code: str | None = None,
    k: int | None = None,
) -> RetrievalResult:
    """
    rag_core 외부에서 사용하는 대표 검색 함수.

    hair와 makeup 두 category를 모두 지원한다.

    1) RetrievalQuery 객체로 호출:

        result = retrieve_docs(
            RetrievalQuery(
                query="퀴프 스타일이 둥근형 남성에게 어울리는 이유",
                category="hair",
                gender="남성",
                face_shape="둥근형",
                face_proportion="균형",
                style_code="m-10",
                k=5,
            )
        )

    2) keyword argument로 hair 검색:

        result = retrieve_docs(
            query="퀴프 스타일이 둥근형 남성에게 어울리는 이유",
            category="hair",
            gender="남성",
            face_shape="둥근형",
            face_proportion="균형",
            style_code="m-10",
            k=5,
        )

    3) keyword argument로 makeup 검색:

        result = retrieve_docs(
            query="봄웜에게 피치 메이크업이 어울리는 이유",
            category="makeup",
            gender="여성",
            personal_color="봄웜",
            makeup_group="peach",
            style_code="mk-sp-peach",
            k=5,
        )
    """

    if retrieval_query is None:
        if not query:
            raise ValueError("retrieve_docs 호출 시 query 값이 필요합니다.")

        retrieval_query = RetrievalQuery(
            query=query,
            category=category,
            gender=gender,
            face_shape=face_shape,
            face_proportion=face_proportion,
            personal_color=personal_color,
            makeup_group=makeup_group,
            style_code=style_code,
            k=k or DEFAULT_RETRIEVAL_K,
        )

    vectorstore = get_vectorstore()
    return _retrieve_docs_with_vectorstore(retrieval_query, vectorstore)


def retrieve_many_docs(
    retrieval_queries: list[RetrievalQuery],
) -> list[RetrievalResult]:
    """
    여러 RetrievalQuery를 하나의 vectorstore 연결로 일괄 검색한다.

    get_vectorstore()를 한 번만 호출하므로 반복 호출보다 빠르다.
    """

    vectorstore = get_vectorstore()
    return [
        _retrieve_docs_with_vectorstore(q, vectorstore)
        for q in retrieval_queries
    ]


def convert_to_chroma_filter(metadata_filter: dict[str, Any]) -> dict[str, Any] | None:
    """
    일반 metadata filter dict를 ChromaDB where 문법으로 변환한다.

    예:
        {"category": "hair", "gender": "남성"}

    변환:
        {
            "$and": [
                {"category": {"$eq": "hair"}},
                {"gender": {"$eq": "남성"}},
            ]
        }
    """

    cleaned_filter = {
        key: value
        for key, value in metadata_filter.items()
        if value is not None
    }

    if not cleaned_filter:
        return None

    conditions = [
        {key: {"$eq": value}}
        for key, value in cleaned_filter.items()
    ]

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}
