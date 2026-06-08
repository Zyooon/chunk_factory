from __future__ import annotations


INTENT_STYLE_FIT = "style_fit"
INTENT_STYLING_METHOD = "styling_method"
INTENT_MAINTENANCE = "maintenance"
INTENT_COMPARISON = "comparison"
INTENT_GENERAL_FOLLOWUP = "general_followup"
INTENT_UNCLEAR = "unclear"
INTENT_MISSING_ANALYSIS = "missing_analysis"


CATEGORY_HAIR = "hair"


MISSING_ANALYSIS_MESSAGE = (
    "아직 분석 결과가 없어 맞춤 상담을 진행하기 어려워요. "
    "먼저 얼굴형과 삼정 비율 분석을 완료한 뒤 다시 질문해 주세요."
)


CLARIFICATION_OPTIONS = [
    "추천받은 스타일이 나에게 어울리는지 궁금해요.",
    "추천받은 스타일의 손질 방법이 궁금해요.",
    "추천받은 스타일의 유지 관리가 어려운지 궁금해요.",
    "추천 스타일끼리 비교해 보고 싶어요.",
    "다른 헤어 관련 질문을 하고 싶어요.",
]


INTENT_KEYWORDS = {
    INTENT_STYLE_FIT: [
        "어울",
        "괜찮",
        "맞아",
        "어때",
        "나한테",
        "잘 맞",
        "추천받은",
    ],
    INTENT_STYLING_METHOD: [
        "손질",
        "드라이",
        "고데기",
        "왁스",
        "스프레이",
        "세팅",
        "스타일링",
        "말리",
    ],
    INTENT_MAINTENANCE: [
        "유지",
        "관리",
        "커트",
        "펌",
        "주기",
        "얼마나",
        "오래",
        "미용실",
        "손 많이",
    ],
    INTENT_COMPARISON: [
        "비교",
        "뭐가 더",
        "어느 게",
        "어떤 게",
        "둘 중",
        "리프랑",
        "퀴프랑",
        "댄디랑",
        "vs",
    ],
}


AMBIGUOUS_MESSAGES = {
    "이거",
    "그거",
    "추천해줘",
    "어떻게 해",
    "어떻게 하면 돼",
    "뭐가 좋아",
    "괜찮아",
    "별로야",
    "좋아",
}


def build_clarification_message() -> str:
    """
    질문 의도가 불명확할 때 사용자에게 보여줄 객관식 재질문 메시지를 만든다.
    """

    option_lines = [
        f"{index}. {option}"
        for index, option in enumerate(CLARIFICATION_OPTIONS, start=1)
    ]

    return "\n".join(
        [
            "어떤 헤어 상담이 필요하신지 조금만 더 알려주세요.",
            "",
            *option_lines,
        ]
    )


def get_intent_by_keyword(message: str) -> str:
    """
    간단한 keyword 기반 intent 분류 함수.

    현재 1차 구현에서는 LLM intent classification 없이
    규칙 기반으로 먼저 분류한다.
    """

    normalized_message = message.strip().lower()

    if not normalized_message:
        return INTENT_UNCLEAR

    if normalized_message in AMBIGUOUS_MESSAGES:
        return INTENT_UNCLEAR

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in normalized_message for keyword in keywords):
            return intent

    return INTENT_GENERAL_FOLLOWUP