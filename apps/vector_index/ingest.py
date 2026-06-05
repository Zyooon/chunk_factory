import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from apps.vector_index.chunking import build_documents_from_items
from apps.vector_index.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
)
from apps.vector_index.embeddings import get_embedding_model
from apps.vector_index.vectorstore import (
    get_vectorstore,
    reset_vectorstore,
)


def find_latest_cleaned_json() -> Path:
    """
    cleaned 폴더에서 가장 최근에 수정된 done.json 파일을 찾는다.
    """
    cleaned_dir = Path("data/cleaned")
    files = list(cleaned_dir.glob("done.json"))

    if not files:
        raise FileNotFoundError(
            "cleaned_data 폴더에서 done.json 파일을 찾을 수 없습니다."
        )

    return max(files, key=lambda path: path.stat().st_mtime)


def load_json_file(file_path: Path) -> list[dict[str, Any]]:
    """
    JSON 파일을 읽어서 list[dict] 형태로 반환한다.
    """
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"정제 JSON은 list 형태여야 합니다. 현재 타입: {type(data).__name__}"
        )

    invalid_items = [
        index
        for index, item in enumerate(data)
        if not isinstance(item, dict)
    ]

    if invalid_items:
        raise ValueError(
            f"정제 JSON 리스트 안에 dict가 아닌 항목이 있습니다. "
            f"문제 인덱스: {invalid_items[:10]}"
        )

    return data


def print_sample_document(documents: list[Document]) -> None:
    """
    생성된 Document 중 첫 번째 샘플을 출력한다.
    """
    if not documents:
        print("[샘플 Document 없음]")
        return

    sample = documents[0]

    print("\n[샘플 Document metadata]")
    print(json.dumps(sample.metadata, ensure_ascii=False, indent=2))

    print("\n[샘플 Document page_content]")
    print(sample.page_content)


def main() -> None:
    """
    벡터 DB 생성 전체 과정을 실행한다.
    """
    latest_json_path = find_latest_cleaned_json()
    print(f"최신 cleaned JSON 파일: {latest_json_path}")

    items = load_json_file(latest_json_path)
    print(f"JSON 로드 완료: {len(items)}개")

    documents = build_documents_from_items(items)
    print(f"Document 생성 완료: {len(documents)}개")

    if len(documents) != len(items):
        print(
            "[주의] Document 개수와 JSON 객체 개수가 다릅니다. "
            f"JSON: {len(items)}개, Document: {len(documents)}개"
        )

    print_sample_document(documents)

    embedding_model = get_embedding_model()
    print("\n임베딩 모델 로드 완료")

    reset_vectorstore()
    print("기존 ChromaDB 초기화 완료")

    vectorstore = get_vectorstore(embedding_model)
    vectorstore.add_documents(documents)
    print(f"ChromaDB 적재 완료: {len(documents)}개 문서")

    print(f"저장 경로: {CHROMA_DIR}")
    print(f"컬렉션 이름: {CHROMA_COLLECTION_NAME}")


if __name__ == "__main__":
    main()