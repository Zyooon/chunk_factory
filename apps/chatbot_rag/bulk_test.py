from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from apps.chatbot_rag.bypass_gate import should_bypass_llm
from apps.chatbot_rag.graph import run_chatbot
from apps.chatbot_rag.image_nodes import (
    IMAGE_INTENT_FIT_CHECK,
    IMAGE_INTENT_GENERAL_ANALYSIS,
    IMAGE_INTENT_MAKEUP_MATCH,
    IMAGE_INTENT_NONE,
    IMAGE_INTENT_STYLE_MATCH,
    IMAGE_INTENT_SYNTHESIS,
)
from apps.chatbot_rag.intent_classifier import get_intent
from apps.chatbot_rag.intent_keywords import detect_question_category
from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_MOOD_CHOICE,
    INTENT_MOOD_SELECTION,
    PENDING_SELECTION_MOOD,
)
from apps.chatbot_rag.selection_options import MOOD_OPTIONS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTION_FILE = PROJECT_ROOT / "data" / "test" / "bulk_questions.txt"
LOG_DIR = Path("logs")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"chatbot_rag_bulk_test_{timestamp}.log"

# True: intent 분류만 테스트한다. RAG/LLM 호출 없음.
# False: run_chatbot()으로 end-to-end 테스트한다.
INTENT_ONLY = True


HAIR_INPUT = {
    "target_type": CATEGORY_HAIR,
    "applied_style_key": "m-08",
    "gender": "남성",
    "face_shape": "계란형",
    "face_proportion": "균형",
    "personal_color": "",
    "previous_analysis": (
        "계란형 얼굴과 균형 잡힌 삼정 비율입니다. "
        "하이앤타이트, 댄디, 아이비리그가 추천되었습니다."
    ),
    "previous_recommendations": [
        {"category": CATEGORY_HAIR, "style_name": "하이앤타이트", "style_code": "m-02"},
        {"category": CATEGORY_HAIR, "style_name": "댄디", "style_code": "m-08"},
        {"category": CATEGORY_HAIR, "style_name": "아이비리그", "style_code": "m-03"},
    ],
    "user_profile": {},
    "chat_history": [],
}

MAKEUP_INPUT = {
    "target_type": CATEGORY_MAKEUP,
    "applied_style_key": "summer_cool_daily",
    "gender": "여성",
    "face_shape": "",
    "face_proportion": "",
    "personal_color": "여름쿨",
    "previous_analysis": (
        "여름쿨 퍼스널컬러입니다. "
        "맑고 차분한 로즈 계열 데일리 메이크업이 추천되었습니다."
    ),
    "previous_recommendations": [
        {
            "category": CATEGORY_MAKEUP,
            "style_name": "로즈 데일리 메이크업",
            "style_code": "summer_cool_daily",
            "makeup_group": "rose_daily",
        },
        {
            "category": CATEGORY_MAKEUP,
            "style_name": "쿨톤 오피스 메이크업",
            "style_code": "summer_cool_office",
            "makeup_group": "cool_office",
        },
    ],
    "user_profile": {},
    "chat_history": [],
}


# ---------------------------------------------------------------------------
# 이미지 테스트 케이스
# 이미지 테스트는 INTENT_ONLY 모드와 무관하게 항상 run_chatbot()으로 실행한다.
# 합성 요청(image_synthesis)은 RAG를 타지 않아 LLM 호출 없음.
# 그 외 케이스는 실제 RAG/LLM 호출이 발생할 수 있다.
# ---------------------------------------------------------------------------

IMAGE_TEST_CASES: list[dict[str, Any]] = [
    {
        "label": "image_none — image_url 없이 일반 질문",
        "user_message": "추천받은 댄디 스타일이 내 얼굴형에 어울릴까요?",
        "image_url": None,
        "target_type": CATEGORY_HAIR,
        "expected_image_intent": IMAGE_INTENT_NONE,
    },
    {
        "label": "image_general_analysis — 이미지 + 일반 어울림 질문",
        "user_message": "이 스타일 나한테 어울릴까요?",
        "image_url": "http://localhost:8000/uploads/test_style.jpg",
        "target_type": CATEGORY_HAIR,
        "expected_image_intent": IMAGE_INTENT_GENERAL_ANALYSIS,
    },
    {
        "label": "image_general_analysis — 이미지 + 비슷한 스타일 질문",
        "user_message": "이 헤어스타일과 비슷한 추천 있어요?",
        "image_url": "http://localhost:8000/uploads/test_style.jpg",
        "target_type": CATEGORY_HAIR,
        "expected_image_intent": IMAGE_INTENT_GENERAL_ANALYSIS,
    },
    {
        "label": "image_synthesis — 합성 키워드 '입혀줘'",
        "user_message": "이 헤어스타일 나한테 입혀줘",
        "image_url": "http://localhost:8000/uploads/test_style.jpg",
        "target_type": CATEGORY_HAIR,
        "expected_image_intent": IMAGE_INTENT_SYNTHESIS,
    },
    {
        "label": "image_synthesis — 합성 키워드 '합성'",
        "user_message": "이 스타일로 합성해줘",
        "image_url": "http://localhost:8000/uploads/test_style.jpg",
        "target_type": CATEGORY_HAIR,
        "expected_image_intent": IMAGE_INTENT_SYNTHESIS,
    },
    {
        "label": "image_synthesis — 합성 키워드 '적용해줘'",
        "user_message": "이 메이크업 나한테 적용해줘",
        "image_url": "http://localhost:8000/uploads/test_makeup.jpg",
        "target_type": CATEGORY_MAKEUP,
        "expected_image_intent": IMAGE_INTENT_SYNTHESIS,
    },
    {
        "label": "image_general_analysis — 메이크업 이미지 분석 질문",
        "user_message": "이 메이크업 내 퍼스널컬러에 맞을까요?",
        "image_url": "http://localhost:8000/uploads/test_makeup.jpg",
        "target_type": CATEGORY_MAKEUP,
        "expected_image_intent": IMAGE_INTENT_GENERAL_ANALYSIS,
    },
]


TWO_TURN_SELECTED_OPTION = {
    "type": PENDING_SELECTION_MOOD,
    "id": "soft_comfortable",
    "label": "부드럽고 편안한 느낌",
    "value": "부드럽고 편안한 느낌",
}


HAIR_TWO_TURN_FIRST_QUESTION = "소개팅에 맞게 어떤 분위기로 가져가면 좋을까?"
MAKEUP_TWO_TURN_FIRST_QUESTION = "소개팅에 맞게 메이크업 분위기를 어떻게 잡으면 좋아?"
TWO_TURN_SECOND_MESSAGE = "부드럽고 편안한 느낌"


def _infer_section_target_type(comment_line: str, current_target_type: str) -> str:
    normalized = comment_line.lower()

    if "메이크업" in comment_line or "makeup" in normalized:
        return CATEGORY_MAKEUP

    if "헤어" in comment_line or "hair" in normalized:
        return CATEGORY_HAIR

    if any(
        keyword in comment_line
        for keyword in ["어울림", "손질", "유지", "비교", "mood", "분위기"]
    ):
        return CATEGORY_HAIR

    return current_target_type


def load_questions(path: Path) -> list[dict[str, str]]:
    """
    질문 파일에서 테스트 질문을 읽는다.

    # 헤어 또는 # 메이크업 섹션 주석을 기준으로 target_type을 고정한다.
    실제 서비스에서는 헤어 챗봇과 메이크업 챗봇이 분리되어 있으므로
    문장만 보고 category를 추정하지 않는다.
    """

    if not path.exists():
        raise FileNotFoundError(f"질문 파일을 찾을 수 없습니다: {path}")

    cases: list[dict[str, str]] = []
    current_target_type = CATEGORY_HAIR

    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()

        if not text:
            continue

        if text.startswith("#"):
            current_target_type = _infer_section_target_type(text, current_target_type)
            continue

        cases.append(
            {
                "question": text,
                "target_type": current_target_type,
            }
        )

    return cases


def get_input_for_target(target_type: str | None) -> dict[str, Any]:
    if target_type == CATEGORY_MAKEUP:
        return dict(MAKEUP_INPUT)

    return dict(HAIR_INPUT)


def count_sentence_like_units(text: str) -> int:
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


def build_intent_only_result(question: str, target_type: str | None) -> dict[str, Any]:
    intent, intent_debug = get_intent(question)
    category = target_type or detect_question_category(question)

    result: dict[str, Any] = {
        "answer": "",
        "intent": intent,
        "intent_debug": intent_debug,
        "category": category,
        "target_type": target_type,
        "needs_clarification": False,
        "detected_style": None,
        "detected_style_is_recommended": False,
        "pending_selection": None,
        "selection": None,
        "selected_mood_id": None,
        "selected_mood": None,
        "selected_mood_keywords": [],
        "retrieval_info": {
            "category": category,
            "target_type": target_type,
            "skipped_rag": True,
            "skip_reason": "intent_only",
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
    target_type: str | None,
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
            f"target_type: {target_type}",
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
    label: str,
    first_question: str,
    first_result: dict[str, Any],
    second_result: dict[str, Any],
) -> str:
    first_retrieval_info = first_result.get("retrieval_info", {})
    second_retrieval_info = second_result.get("retrieval_info", {})

    return "\n".join(
        [
            "=" * 100,
            f"[2턴 mood 선택 테스트 - {label}]",
            "",
            "[1턴 입력]",
            first_question,
            "",
            "[1턴 결과]",
            f"target_type: {first_result.get('target_type')}",
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
            f"target_type: {second_result.get('target_type')}",
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


def format_image_test_log(
    *,
    index: int,
    total: int,
    case: dict[str, Any],
    result: dict[str, Any],
) -> str:
    retrieval_info = result.get("retrieval_info", {})

    expected = case.get("expected_image_intent")
    actual = result.get("image_intent")
    passed = actual == expected
    pass_label = "PASS" if passed else f"FAIL (expected={expected}, actual={actual})"

    return "\n".join(
        [
            "=" * 100,
            f"[IMAGE {index}/{total}] {case['label']}",
            f"user_message: {case['user_message']}",
            f"image_url: {case.get('image_url')}",
            f"target_type: {case.get('target_type')}",
            f"expected_image_intent: {expected}",
            f"image_intent: {actual}",
            f"image_intent_debug: {result.get('image_intent_debug')}",
            f"image_is_synthesis_request: {result.get('image_is_synthesis_request')}",
            f"image_analysis: {result.get('image_analysis')}",
            f"image_visual_features: {result.get('image_visual_features')}",
            f"skipped_rag: {retrieval_info.get('skipped_rag')}",
            f"skip_reason: {retrieval_info.get('skip_reason')}",
            f"retrieved_count: {retrieval_info.get('retrieved_count')}",
            f"intent: {result.get('intent')}",
            f"error: {result.get('error')}",
            f"RESULT: {pass_label}",
            "",
            "[answer]",
            result.get("answer", ""),
            "",
        ]
    )


def run_image_tests(logs: list[str]) -> tuple[int, int]:
    """
    IMAGE_TEST_CASES를 순서대로 실행하고 결과를 logs에 추가한다.

    INTENT_ONLY 모드와 무관하게 항상 run_chatbot()으로 실행한다.

    반환: (pass_count, total)
    """
    total = len(IMAGE_TEST_CASES)
    pass_count = 0

    logs.append("=" * 100)
    logs.append(f"[이미지 테스트] 총 {total}개 (항상 run_chatbot 사용, INTENT_ONLY 무관)")
    logs.append("=" * 100)
    logs.append("")

    for index, case in enumerate(IMAGE_TEST_CASES, start=1):
        print(f"[IMAGE {index}/{total}] {case['label']}")

        chatbot_input = get_input_for_target(case.get("target_type"))

        try:
            result = run_chatbot(
                user_message=case["user_message"],
                image_url=case.get("image_url"),
                **chatbot_input,
            )
        except Exception as exc:
            result = {
                "answer": "",
                "intent": None,
                "image_intent": None,
                "image_intent_debug": None,
                "image_is_synthesis_request": False,
                "image_analysis": None,
                "image_visual_features": [],
                "retrieval_info": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

        expected = case.get("expected_image_intent")
        actual = result.get("image_intent")
        passed = actual == expected
        if passed:
            pass_count += 1

        logs.append(
            format_image_test_log(
                index=index,
                total=total,
                case=case,
                result=result,
            )
        )

        retrieval_info = result.get("retrieval_info", {})
        status = "PASS" if passed else f"FAIL(expected={expected}, got={actual})"
        print(
            f"  → {status}, "
            f"image_intent={actual}, "
            f"skipped_rag={retrieval_info.get('skipped_rag')}, "
            f"skip_reason={retrieval_info.get('skip_reason')}, "
            f"retrieved_count={retrieval_info.get('retrieved_count')}, "
            f"error={result.get('error')}"
        )

    return pass_count, total


def run_mood_two_turn_test(
    *,
    label: str,
    target_type: str,
    first_question: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if INTENT_ONLY:
        first_result = build_intent_only_result(first_question, target_type)
        second_result = {
            "answer": "",
            "intent": INTENT_MOOD_CHOICE,
            "intent_debug": {
                "classifier": "selection",
                "selected_option_id": TWO_TURN_SELECTED_OPTION["id"],
            },
            "category": target_type,
            "target_type": target_type,
            "pending_selection": None,
            "selection": None,
            "selected_mood_id": TWO_TURN_SELECTED_OPTION["id"],
            "selected_mood": TWO_TURN_SELECTED_OPTION["label"],
            "selected_mood_keywords": ["부드러움", "편안함", "자연스러움"],
            "retrieval_info": {
                "category": target_type,
                "target_type": target_type,
                "skipped_rag": True,
                "skip_reason": "intent_only",
                "retrieved_count": 0,
                "fallback_stage": "none",
            },
            "error": None,
        }
        return first_result, second_result

    first_input = get_input_for_target(target_type)
    first_result = run_chatbot(
        user_message=first_question,
        **first_input,
    )

    second_input = get_input_for_target(target_type)
    second_result = run_chatbot(
        user_message=TWO_TURN_SECOND_MESSAGE,
        **{
            **second_input,
            "user_profile": {
                "pending_selection": first_result.get("pending_selection"),
            },
            "chat_history": first_result.get("updated_chat_history", []),
            "selected_option": TWO_TURN_SELECTED_OPTION,
        },
    )

    return first_result, second_result


def main() -> None:
    cases = load_questions(QUESTION_FILE)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs: list[str] = [
        "=" * 100,
        f"chatbot_rag bulk test started_at={started_at}",
        f"question_file={QUESTION_FILE}",
        f"total_questions={len(cases)}",
        f"intent_only={INTENT_ONLY}",
        "hair_makeup_split=True",
        "=" * 100,
        "",
    ]

    total = len(cases)

    for index, case in enumerate(cases, start=1):
        question = case["question"]
        target_type = case.get("target_type") or CATEGORY_HAIR
        print(f"[{index}/{total}] 테스트 중: ({target_type}) {question}")

        try:
            if INTENT_ONLY:
                result = build_intent_only_result(question, target_type)
            else:
                chatbot_input = get_input_for_target(target_type)
                result = run_chatbot(
                    user_message=question,
                    **chatbot_input,
                )
        except Exception as exc:
            result = {
                "answer": "",
                "intent": None,
                "intent_debug": None,
                "category": target_type,
                "target_type": target_type,
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
            target_type=target_type,
            result=result,
        )

        logs.append(log_text)

        retrieval_info = result.get("retrieval_info", {})
        intent_debug = result.get("intent_debug") or retrieval_info.get("intent_debug") or {}
        print(
            "  → "
            f"target={target_type}, "
            f"intent={result.get('intent')}, "
            f"classifier={intent_debug.get('classifier')}, "
            f"score={intent_debug.get('semantic_score')}, "
            f"pending={result.get('pending_selection')}, "
            f"selection={get_selection_summary(result)}, "
            f"skipped_rag={retrieval_info.get('skipped_rag')}, "
            f"error={result.get('error')}"
        )

    two_turn_tests = [
        ("hair", CATEGORY_HAIR, HAIR_TWO_TURN_FIRST_QUESTION),
        ("makeup", CATEGORY_MAKEUP, MAKEUP_TWO_TURN_FIRST_QUESTION),
    ]

    for label, target_type, first_question in two_turn_tests:
        print(f"[2턴 mood 선택 테스트 - {label}] 테스트 중")

        try:
            first_result, second_result = run_mood_two_turn_test(
                label=label,
                target_type=target_type,
                first_question=first_question,
            )
        except Exception as exc:
            first_result = {
                "answer": "",
                "intent": None,
                "category": target_type,
                "target_type": target_type,
                "retrieval_info": {},
                "error": f"{type(exc).__name__}: {exc}",
            }
            second_result = {
                "answer": "",
                "intent": None,
                "category": target_type,
                "target_type": target_type,
                "retrieval_info": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

        logs.append(
            format_two_turn_log(
                label=label,
                first_question=first_question,
                first_result=first_result,
                second_result=second_result,
            )
        )

        print(
            "  → "
            f"target={target_type}, "
            f"first_intent={first_result.get('intent')}, "
            f"first_pending={first_result.get('pending_selection')}, "
            f"second_intent={second_result.get('intent')}, "
            f"selected_mood={second_result.get('selected_mood')}, "
            f"error={second_result.get('error')}"
        )

    # 이미지 테스트 (INTENT_ONLY 무관하게 항상 run_chatbot 사용)
    print()
    image_pass_count, image_total = run_image_tests(logs)

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logs.append("=" * 100)
    logs.append(f"chatbot_rag bulk test finished_at={finished_at}")
    logs.append(f"image_test_pass={image_pass_count}/{image_total}")
    logs.append("=" * 100)

    LOG_FILE.write_text("\n".join(logs), encoding="utf-8")

    print()
    print(f"텍스트 테스트: {total}개 + 2턴 mood 선택 테스트 {len(two_turn_tests)}개")
    print(f"이미지 테스트: {image_pass_count}/{image_total} PASS")
    print(f"intent_only={INTENT_ONLY}")
    print("hair_makeup_split=True")
    print(f"로그 저장 위치: {LOG_FILE}")


if __name__ == "__main__":
    main()
