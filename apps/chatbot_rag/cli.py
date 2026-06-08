from __future__ import annotations

from pprint import pprint

from apps.chatbot_rag.graph import run_chatbot


SAMPLE_PREVIOUS_ANALYSIS = (
    "고객님은 둥근 얼굴형과 균형 잡힌 삼정 비율을 가지고 있어요. "
    "현재 추천 스타일은 리프, 퀴프, 댄디입니다. "
    "리프는 자연스러운 앞머리 흐름으로 얼굴선을 부드럽게 보완하고, "
    "퀴프는 위쪽 볼륨으로 얼굴을 더 길고 시원하게 보이게 하며, "
    "댄디는 부드럽고 단정한 인상을 줄 수 있습니다."
)


SAMPLE_PREVIOUS_RECOMMENDATIONS = [
    {
        "style_name": "리프",
        "style_code": "m-09",
    },
    {
        "style_name": "퀴프",
        "style_code": "m-10",
    },
    {
        "style_name": "댄디",
        "style_code": "m-08",
    },
]


def print_result(title: str, result: dict) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    print("\n[답변]")
    print(result.get("answer"))

    print("\n[메타 정보]")
    pprint(
        {
            "intent": result.get("intent"),
            "category": result.get("category"),
            "needs_clarification": result.get("needs_clarification"),
            "clarification_options": result.get("clarification_options"),
            "retrieval_info": result.get("retrieval_info"),
            "error": result.get("error"),
        },
        sort_dicts=False,
    )

    print("\n[업데이트된 대화 기록]")
    pprint(result.get("updated_chat_history"), sort_dicts=False)

    print("\n[업데이트된 유저 프로필]")
    pprint(result.get("updated_user_profile"), sort_dicts=False)


def run_sample_cases() -> None:
    common_input = {
        "gender": "남성",
        "face_shape": "둥근형",
        "face_proportion": "균형",
        "previous_analysis": SAMPLE_PREVIOUS_ANALYSIS,
        "previous_recommendations": SAMPLE_PREVIOUS_RECOMMENDATIONS,
        "user_profile": {},
        "chat_history": [],
    }

    normal_result = run_chatbot(
        user_message="리프 손질 어려워?",
        **common_input,
    )
    print_result("CASE 1. 정상 질문", normal_result)

    unclear_result = run_chatbot(
        user_message="이거",
        **common_input,
    )
    print_result("CASE 2. 애매한 질문", unclear_result)

    missing_analysis_result = run_chatbot(
        user_message="리프 손질 어려워?",
        gender="남성",
        face_shape="둥근형",
        face_proportion="균형",
        previous_analysis=None,
        previous_recommendations=[],
        user_profile={},
        chat_history=[],
    )
    print_result("CASE 3. 분석 결과 없음", missing_analysis_result)


def main() -> None:
    run_sample_cases()


if __name__ == "__main__":
    main()