# apps/rag_core/utils.py

from typing import Any, Iterable

from langchain_core.documents import Document

from apps.rag_core.schemas import RetrievedDocument


def clean_metadata_filter(metadata_filter: dict[str, Any]) -> dict[str, Any]:
    """
    ChromaDB metadata filter에 사용할 수 있도록 비어 있는 값을 제거한다.

    제거 대상:
    - None
    - 빈 문자열 ""
    - 공백 문자열 "   "

    예:
        {
            "category": "hair",
            "gender": "남성",
            "style_code": None,
        }

        ->

        {
            "category": "hair",
            "gender": "남성",
        }
    """

    cleaned: dict[str, Any] = {}

    for key, value in metadata_filter.items():
        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        cleaned[key] = value

    return cleaned


def document_to_retrieved_document(
    document: Document,
    score: float | None = None,
) -> RetrievedDocument:
    """
    LangChain Document 1개를 rag_core의 RetrievedDocument로 변환한다.

    LangChain Document:
        - page_content: LLM에게 전달할 본문
        - metadata: 검색 필터/출처 정보

    RetrievedDocument:
        - rag_core 내부에서 공통으로 사용하는 검색 결과 schema
    """

    return RetrievedDocument(
        page_content=document.page_content,
        metadata=dict(document.metadata or {}),
        score=score,
    )


def documents_to_retrieved_documents(
    documents: Iterable[Document],
) -> list[RetrievedDocument]:
    """
    LangChain Document 목록을 RetrievedDocument 목록으로 변환한다.

    similarity_search()처럼 score가 없는 검색 결과에 사용한다.
    """

    return [
        document_to_retrieved_document(document)
        for document in documents
    ]


def scored_documents_to_retrieved_documents(
    scored_documents: Iterable[tuple[Document, float]],
) -> list[RetrievedDocument]:
    """
    score가 포함된 ChromaDB 검색 결과를 RetrievedDocument 목록으로 변환한다.

    similarity_search_with_score() 결과에 사용한다.
    """

    return [
        document_to_retrieved_document(document, score=score)
        for document, score in scored_documents
    ]


def format_documents_as_context(
    documents: list[RetrievedDocument],
) -> str:
    """
    검색된 문서 목록을 Gemini에게 전달할 context 문자열로 변환한다.

    Gemini API generator는 객체 목록이 아니라 문자열 context를 입력으로 받기 때문에
    검색 결과를 사람이 읽을 수 있는 형태로 정리한다.
    """

    if not documents:
        return "검색된 참고 문서가 없습니다."

    context_blocks: list[str] = []

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata

        style_name = metadata.get("style_name", "알 수 없음")
        style_code = metadata.get("style_code", "알 수 없음")
        category = metadata.get("category", "알 수 없음")
        gender = metadata.get("gender", "알 수 없음")
        face_shape = metadata.get("face_shape", "알 수 없음")
        face_proportion = metadata.get("face_proportion", "알 수 없음")

        block = f"""
[문서 {index}]
카테고리: {category}
성별: {gender}
얼굴형: {face_shape}
삼정 비율: {face_proportion}
스타일명: {style_name}
스타일 코드: {style_code}

내용:
{document.page_content}
""".strip()

        context_blocks.append(block)

    return "\n\n---\n\n".join(context_blocks)