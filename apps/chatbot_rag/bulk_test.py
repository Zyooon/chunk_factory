from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from apps.chatbot_rag.bypass_gate import should_bypass_llm
from apps.chatbot_rag.graph import run_chatbot
from apps.chatbot_rag.intent_classifier import get_intent
from apps.chatbot_rag.intent_keywords import detect_question_category
from apps.chatbot_rag.intents import INTENT_MOOD_CHOICE, INTENT_MOOD_SELECTION, PENDING_SELECTION_MOOD
from apps.chatbot_rag.selection_options import MOOD_OPTIONS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTION_FILE = PROJECT_ROOT / "data" / "test" / "bulk_questions.txt"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "chatbot_rag_bulk_test.log"

# True: intent 분류만 테스트한다. RAG/LLM 호출 없음.
# False: 기존처럼 run_chatbot()으로 end-to-end 테스트한다.
INTENT_ONLY = True


COMMON_INPUT = {
    "gender": "남성",
    "face_shape": "계란형",
    "face_proportion": "균형",
    "previous_analysis": (
        "계란형 얼굴과 균형 잡힌 삼정 비율입니다. "
        "하이앤타이트, 댄디, 아이비리그가 추천되었습니다."
    ),
    "previous_recommendations": [
        {"category": "hair", "style_name": "하이앤타이트", "style_code": "m-02"},
        {"category": "hair", "style_name": "댄디", "style_code": "m-08"},
        {"category": "hair", "style_name": "아이비리그", "style_code": "m-03"},
    ],
    "user_profile": {},
    "chat_history": [],
}


TWO_TURN_SELECTED_OPTION = {
    "type": PENDING_SELECTION_MOOD,
    "id": "soft_comfortable",
    "label": "부드럽고 편안한 느낌",
    "value": "부드럽고 편안한 느낌",
}


TWO_TURN_FIRST_QUESTION = "소개팅에 맞게 어떤 분위기로 가져가면 좋을까?"
TWO_TURN_SECOND_MESSAGE = "부드럽고 편안한 느낌"


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


def get_selection_summary(result: dict[str, Any]) -> str:
    selection = result.get("selection") or {}
    options = selection.get("options") or []

    if not selection:
        return "None"

    return (
        f"type={selection.get('type')}, "
        f"title={selection.get('title')}, "
        f"options_count={len(options)}"
    )


def build_intent_only_result(question: str) -> dict[str, Any]:
    intent, intent_debug = get_intent(question)
    category = detect_question_category(question)
    skipped_rag = True
    skip_reason = "intent_only"

    result: dict[str, Any] = {
        "answer": "",
        "intent": intent,
        "intent_debug": intent_debug,
        "category": category,
        "needs_clarification": False,
        "detected_style": None,
        "detected_style_is_recommended": False,
        "pending_selection": None,
        "selection": None,
        "selected_mood_id": None,
        "selected_mood": None,
        "selected_mood_keywords": [],
        "retrieval_info": {
            "skipped_rag": skipped_rag,
            "skip_reason": skip_reason,
            "retrieved_count": 0,
            "fallback_stage": "none",
            "intent_debug": intent_debug,
            "bypass_llm": should_bypass_llm(intent),
        },
        "error": None,
    }

    if intent == INTENT_MOOD_SELECTION:
        result["pending_selection"] = PENDING_SELECTION_MOOD
        result["selection"] = {
            "type": PENDING_SELECTION_MOOD,
            "title": "원하는 분위기를 선택해 주세요.",
            "options": [
                {
                    "id": option["id"],
                    "label": option["label"],
                    "value": option["label"],
                }
                for option in MOOD_OPTIONS
            ],
        }

    return result


def format_result_log(
    *,
    index: int,
    total: int,
    question: str,
    result: dict[str, Any],
) -> str:
    retrieval_info = result.get("retrieval_info", {})
    detected_style = result.get("detected_style")
    intent_debug = result.get("intent_debug") or retrieval_info.get("intent_debug")

    answer = result.get("answer", "")
    sentence_count = count_sentence_like_units(answer)

    return "\n".join(
        [
            "=" * 100,
            f"[{index}/{total}] 질문: {question}",
            f"intent: {result.get('intent')}",
            f"intent_debug: {intent_debug}",
            f"category: {result.get('category')}",
            f"needs_clarification: {result.get('needs_clarification')}",
            f"detected_style: {detected_style}",
            "detected_style_is_recommended: "
            f"{result.get('detected_style_is_recommended')}",
            f"pending_selection: {result.get('pending_selection')}",
            f"selection: {get_selection_summary(result)}",
            f"selected_mood_id: {result.get('selected_mood_id')}",
            f"selected_mood: {result.get('selected_mood')}",
            f"selected_mood_keywords: {result.get('selected_mood_keywords')}",
            f"skipped_rag: {retrieval_info.get('skipped_rag')}",
            f"skip_reason: {retrieval_info.get('skip_reason')}",
            f"bypass_llm: {retrieval_info.get('bypass_llm')}",
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


def format_two_turn_log(
    *,
    first_result: dict[str, Any],
    second_result: dict[str, Any],
) -> str:
    first_retrieval_info = first_result.get("retrieval_info", {})
    second_retrieval_info = second_result.get("retrieval_info", {})

    return "\n".join(
        [
            "=" * 100,
            "[2턴 mood 선택 테스트]",
            "",
            "[1턴 입력]",
            TWO_TURN_FIRST_QUESTION,
            "",
            "[1턴 결과]",
            f"intent: {first_result.get('intent')}",
            f"intent_debug: {first_result.get('intent_debug')}",
            f"category: {first_result.get('category')}",
            f"pending_selection: {first_result.get('pending_selection')}",
            f"selection: {get_selection_summary(first_result)}",
            f"skipped_rag: {first_retrieval_info.get('skipped_rag')}",
            f"skip_reason: {first_retrieval_info.get('skip_reason')}",
            f"error: {first_result.get('error')}",
            "",
            "[1턴 answer]",
            first_result.get("answer", ""),
            "",
            "[2턴 입력]",
            f"user_message: {TWO_TURN_SECOND_MESSAGE}",
            f"selected_option: {TWO_TURN_SELECTED_OPTION}",
            "",
            "[2턴 결과]",
            f"intent: {second_result.get('intent')}",
            f"intent_debug: {second_result.get('intent_debug')}",
            f"category: {second_result.get('category')}",
            f"pending_selection: {second_result.get('pending_selection')}",
            f"selected_mood_id: {second_result.get('selected_mood_id')}",
            f"selected_mood: {second_result.get('selected_mood')}",
            f"selected_mood_keywords: {second_result.get('selected_mood_keywords')}",
            f"skipped_rag: {second_retrieval_info.get('skipped_rag')}",
            f"skip_reason: {second_retrieval_info.get('skip_reason')}",
            f"retrieved_count: {second_retrieval_info.get('retrieved_count')}",
            f"fallback_stage: {second_retrieval_info.get('fallback_stage')}",
            f"error: {second_result.get('error')}",
            "",
            "[2턴 answer]",
            second_result.get("answer", ""),
            "",
        ]
    )


def run_mood_two_turn_test() -> tuple[dict[str, Any], dict[str, Any]]:
    if INTENT_ONLY:
        first_result = build_intent_only_result(TWO_TURN_FIRST_QUESTION)
        second_result = {
            "answer": "",
            "intent": INTENT_MOOD_CHOICE,
            "intent_debug": {
                "classifier": "selection",
                "selected_option_id": TWO_TURN_SELECTED_OPTION["id"],
            },
            "category": "hair",
            "pending_selection": None,
            "selection": None,
            "selected_mood_id": TWO_TURN_SELECTED_OPTION["id"],
            "selected_mood": TWO_TURN_SELECTED_OPTION["label"],
            "selected_mood_keywords": ["부드러움", "편안함", "자연스러움"],
            "retrieval_info": {
                "skipped_rag": True,
                "skip_reason": "intent_only",
                "retrieved_count": 0,
                "fallback_stage": "none",
            },
            "error": None,
        }
        return first_result, second_result

    first_result = run_chatbot(
        user_message=TWO_TURN_FIRST_QUESTION,
        **COMMON_INPUT,
    )

    second_result = run_chatbot(
        user_message=TWO_TURN_SECOND_MESSAGE,
        gender=COMMON_INPUT["gender"],
        face_shape=COMMON_INPUT["face_shape"],
        face_proportion=COMMON_INPUT["face_proportion"],
        previous_analysis=COMMON_INPUT["previous_analysis"],
        previous_recommendations=COMMON_INPUT["previous_recommendations"],
        user_profile={
            "pending_selection": first_result.get("pending_selection"),
        },
        chat_history=first_result.get("updated_chat_history", []),
        selected_option=TWO_TURN_SELECTED_OPTION,
    )

    return first_result, second_result


def main() -> None:
    questions = load_questions(QUESTION_FILE)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs: list[str] = [
        "=" * 100,
        f"chatbot_rag bulk test started_at={started_at}",
        f"question_file={QUESTION_FILE}",
        f"total_questions={len(questions)}",
        f"intent_only={INTENT_ONLY}",
        "=" * 100,
        "",
    ]

    total = len(questions)

    for index, question in enumerate(questions, start=1):
        print(f"[{index}/{total}] 테스트 중: {question}")

        try:
            if INTENT_ONLY:
                result = build_intent_only_result(question)
            else:
                result = run_chatbot(
                    user_message=question,
                    **COMMON_INPUT,
                )
        except Exception as exc:
            result = {
                "answer": "",
                "intent": None,
                "intent_debug": None,
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
        intent_debug = result.get("intent_debug") or retrieval_info.get("intent_debug") or {}
        print(
            "  → "
            f"intent={result.get('intent')}, "
            f"classifier={intent_debug.get('classifier')}, "
            f"score={intent_debug.get('semantic_score')}, "
            f"pending={result.get('pending_selection')}, "
            f"selection={get_selection_summary(result)}, "
            f"skipped_rag={retrieval_info.get('skipped_rag')}, "
            f"error={result.get('error')}"
        )

    print("[2턴 mood 선택 테스트] 테스트 중")

    try:
        first_result, second_result = run_mood_two_turn_test()
    except Exception as exc:
        first_result = {
            "answer": "",
            "intent": None,
            "category": None,
            "retrieval_info": {},
            "error": f"{type(exc).__name__}: {exc}",
        }
        second_result = {
            "answer": "",
            "intent": None,
            "category": None,
            "retrieval_info": {},
            "error": f"{type(exc).__name__}: {exc}",
        }

    logs.append(
        format_two_turn_log(
            first_result=first_result,
            second_result=second_result,
        )
    )

    print(
        "  → "
        f"first_intent={first_result.get('intent')}, "
        f"first_pending={first_result.get('pending_selection')}, "
        f"second_intent={second_result.get('intent')}, "
        f"selected_mood={second_result.get('selected_mood')}, "
        f"error={second_result.get('error')}"
    )

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs.append("=" * 100)
    logs.append(f"chatbot_rag bulk test finished_at={finished_at}")
    logs.append("=" * 100)

    LOG_FILE.write_text("\n".join(logs), encoding="utf-8")

    print()
    print(f"테스트 완료: {total}개 + 2턴 mood 선택 테스트 1개")
    print(f"intent_only={INTENT_ONLY}")
    print(f"로그 저장 위치: {LOG_FILE}")


if __name__ == "__main__":
    main()
