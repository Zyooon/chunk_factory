"""
실행: uv run python -m apps.rag.ingest
"""
import json
import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from apps.rag.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    GEMINI_API_KEY,
    HF_EMBEDDING_MODEL,
)
from apps.rag.chunking import build_documents_from_items

# 실제 cleaned 데이터 위치 (hair_factory.py 기준)
CLEANED_DATA_DIR = Path("./data/cleaned")
GLOB_PATTERN = "cleaned_rag_data_*.json"


def find_all_jsons() -> list[Path]:
    files = sorted(CLEANED_DATA_DIR.glob(GLOB_PATTERN))
    if not files:
        raise FileNotFoundError(
            f"'{CLEANED_DATA_DIR}' 에서 '{GLOB_PATTERN}' 파일을 찾을 수 없습니다.\n"
            "먼저 'uv run hair_factory.py' 를 실행해 데이터를 생성해 주세요."
        )
    return files


def main() -> None:
    if not GEMINI_API_KEY:
        print("[오류] GEMINI_API_KEY가 설정되지 않았습니다.")
        print("프로젝트 루트의 .env 파일에 GEMINI_API_KEY=your_key 를 추가해 주세요.")
        sys.exit(1)

    json_paths = find_all_jsons()
    print(f"[인제스트] 발견된 파일 수: {len(json_paths)}개")

    items: list[dict] = []
    for json_path in json_paths:
        file_items = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"  - {json_path.name}: {len(file_items)}개 항목")
        items.extend(file_items)
    print(f"[인제스트] 전체 로드된 항목 수: {len(items)}")

    docs = build_documents_from_items(items)
    print(f"[인제스트] Document 변환 완료: {len(docs)}개")

    print(f"[인제스트] 임베딩 모델 로드 중: {HF_EMBEDDING_MODEL} (최초 실행 시 다운로드 발생)")
    embeddings = HuggingFaceEmbeddings(
        model_name=HF_EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

    chroma_path = Path(CHROMA_DIR)
    chroma_path.mkdir(parents=True, exist_ok=True)

    # 기존 컬렉션 삭제 후 새로 생성
    existing = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(chroma_path),
    )
    existing.delete_collection()
    print("[인제스트] 기존 컬렉션 초기화 완료")

    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=str(chroma_path),
    )

    count = db._collection.count()
    print(f"\n[완료] {count}개 문서가 ChromaDB에 저장되었습니다.")
    print(f"[완료] 사용 파일 수: {len(json_paths)}개")


if __name__ == "__main__":
    main()
