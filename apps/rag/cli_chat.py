"""
실행: uv run python -m apps.rag.cli_chat
"""
import sys

from apps.rag.config import (
    GEMINI_API_KEY,
    USER_FACE_PROPORTION,
    USER_FACE_SHAPE,
    USER_GENDER,
)
from apps.rag.generator import generate_answer
from apps.rag.retriever import retrieve_docs


def main() -> None:
    if not GEMINI_API_KEY:
        print("[오류] GEMINI_API_KEY가 설정되지 않았습니다.")
        print("프로젝트 루트의 .env 파일에 GEMINI_API_KEY=your_key 를 추가해 주세요.")
        sys.exit(1)

    gender = USER_GENDER
    face_shape = USER_FACE_SHAPE
    face_proportion = USER_FACE_PROPORTION

    print("=" * 55)
    print("  뷰티 헤어 RAG 챗봇에 오신 것을 환영합니다!")
    print("  종료하려면 'exit' 또는 'quit'을 입력하세요.")
    print("=" * 55)
    print(f"\n[설정] 성별: {gender}  얼굴형: {face_shape}  삼정 비율: {face_proportion}")
    print("-" * 55)

    # 초기 분석 자동 출력
    print("\n[분석 중...]")
    _init_query = f"{gender} {face_shape} {face_proportion} 얼굴형 삼정 비율 분석 헤어스타일 추천"
    init_docs, init_stage = retrieve_docs(_init_query, gender, face_shape, face_proportion)
    init_answer = generate_answer(
        f"제 얼굴형({face_shape}), 삼정 비율({face_proportion})에 대해 분석하고 어울리는 헤어스타일을 추천해주세요.",
        gender,
        face_shape,
        face_proportion,
        init_docs,
        init_stage,
    )
    print(init_answer)
    print("\n" + "=" * 55)

    while True:
        try:
            query = input("\n질문: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n챗봇을 종료합니다. 안녕히 가세요!")
            break

        if query.lower() in ("exit", "quit"):
            print("챗봇을 종료합니다. 안녕히 가세요!")
            break

        if not query:
            continue

        print("[검색 중...]")
        docs, fallback_stage = retrieve_docs(query, gender, face_shape, face_proportion)
        print(f"[검색 결과] {len(docs)}개 문서  |  fallback 단계: {fallback_stage}\n")

        answer = generate_answer(query, gender, face_shape, face_proportion, docs, fallback_stage)
        print(answer)
        print("\n" + "-" * 55)


if __name__ == "__main__":
    main()
