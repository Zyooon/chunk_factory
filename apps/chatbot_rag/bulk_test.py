from __future__ import annotations

from datetime import datetime
from pathlib import Path

from apps.chatbot_rag.graph import run_chatbot


BASE_DIR = Path(__file__).resolve().parent
QUESTION_FILE = BASE_DIR / "data" / "test" / "bulk_questions.txt"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "chatbot_rag_bulk_test.log"


COMMON_INPUT = {
    "gender": "남성",
    "face_shape": "계란형",
    "face_proportion": "균형",
    "previous_analysis": (
        "계란형 얼굴과 균형 잡힌 삼정 비율입니다. "
        "하이앤타이트, 댄디, 아이비리그가 추천되었습니다."
    ),
    "previous_recommendations": [
        {"style_name": "하이앤타이트", "style_code": "m-02"},
        {"style_name": "댄디", "style_code": "m-08"},
        {"style_name": "아이비리그", "style_code": "m-03"},
    ],
    "user_profile": {},
    "chat_history": [],
}


def load_questions(path: Path) -> list[str]:
    """
    질문 파일에서 테스트 질문을 한 줄씩 읽는다.

    빈 줄과 #으로 시작하는 주석 줄은 제외한다.
    """

    if not path.exists():
        raise FileNotFoundError(f"질문 파일을 찾을 수 없습니다: {path}")

    questions: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        question = line.strip()

        if not question:
            continue

        if question.startswith("#"):
            continue

        questions.append(question)

    return questions


def count_sentence_like_units(text: str) -> int:
    """
    답변이 너무 길어지는지 대략 확인하기 위한 간단한 문장 수 계산.
    """

    if not text:
        return 0

    normalized = text.replace("\n", " ").strip()

    count = 0

    for marker in [".", "?", "!", "요.", "다."]:
        count += normalized.count(marker)

    return max(1, count)


def format_result_log(
    *,
    index: int,
    total: int,
    question: str,
    result: dict,
) -> str:
    retrieval_info = result.get("retrieval_info", {})
    detected_style = result.get("detected_style")

    answer = result.get("answer", "")
    sentence_count = count_sentence_like_units(answer)

    return "\n".join(
        [
            "=" * 100,
            f"[{index}/{total}] 질문: {question}",
            f"intent: {result.get('intent')}",
            f"category: {result.get('category')}",
            f"needs_clarification: {result.get('needs_clarification')}",
            f"detected_style: {detected_style}",
            "detected_style_is_recommended: "
            f"{result.get('detected_style_is_recommended')}",
            f"skipped_rag: {retrieval_info.get('skipped_rag')}",
            f"skip_reason: {retrieval_info.get('skip_reason')}",
            f"retrieved_count: {retrieval_info.get('retrieved_count')}",
            f"fallback_stage: {retrieval_info.get('fallback_stage')}",
            f"sentence_count: {sentence_count}",
            f"error: {result.get('error')}",
            "",
            "[answer]",
            answer,
            "",
        ]
    )


def main() -> None:
    questions = load_questions(QUESTION_FILE)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs: list[str] = [
        "=" * 100,
        f"chatbot_rag bulk test started_at={started_at}",
        f"question_file={QUESTION_FILE}",
        f"total_questions={len(questions)}",
        "=" * 100,
        "",
    ]

    total = len(questions)

    for index, question in enumerate(questions, start=1):
        print(f"[{index}/{total}] 테스트 중: {question}")

        try:
            result = run_chatbot(
                user_message=question,
                **COMMON_INPUT,
            )
        except Exception as exc:
            result = {
                "answer": "",
                "intent": None,
                "category": None,
                "needs_clarification": False,
                "detected_style": None,
                "detected_style_is_recommended": False,
                "retrieval_info": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

        log_text = format_result_log(
            index=index,
            total=total,
            question=question,
            result=result,
        )

        logs.append(log_text)

        retrieval_info = result.get("retrieval_info", {})
        print(
            "  → "
            f"intent={result.get('intent')}, "
            f"style={result.get('detected_style')}, "
            f"skipped_rag={retrieval_info.get('skipped_rag')}, "
            f"error={result.get('error')}"
        )

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs.append("=" * 100)
    logs.append(f"chatbot_rag bulk test finished_at={finished_at}")
    logs.append("=" * 100)

    LOG_FILE.write_text("\n".join(logs), encoding="utf-8")

    print()
    print(f"테스트 완료: {total}개")
    print(f"로그 저장 위치: {LOG_FILE}")


if __name__ == "__main__":
    main()