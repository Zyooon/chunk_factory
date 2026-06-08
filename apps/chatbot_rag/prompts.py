from __future__ import annotations

from typing import Any

from apps.rag_core.schemas import ChatGenerationInput
from apps.rag_core.utils import format_documents_as_context


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


def format_previous_recommendations_for_prompt(
    previous_recommendations: list[dict[str, Any]],
) -> str:
    """
    이전 추천 스타일 목록을 프롬프트용 문자열로 변환한다.

    style_code는 내부 식별자이므로 프롬프트에도 전달하지 않는다.
    """

    if not previous_recommendations:
        return "이전 추천 스타일 정보가 없습니다."

    lines: list[str] = []

    for recommendation in previous_recommendations:
        style_name = recommendation.get("style_name")
        if style_name:
            lines.append(f"- {style_name}")

    if not lines:
        return "이전 추천 스타일 정보가 없습니다."

    return "\n".join(lines)


def format_chat_history_for_prompt(
    chat_history: list[dict[str, str]],
    max_messages: int = 10,
) -> str:
    """
    최근 대화 기록을 프롬프트용 문자열로 변환한다.
    """

    if not chat_history:
        return "최근 대화 기록이 없습니다."

    recent_history = chat_history[-max_messages:]
    lines: list[str] = []

    for message in recent_history:
        role = message.get("role", "")
        content = message.get("content", "")

        if not content:
            continue

        if role == "user":
            role_label = "사용자"
        elif role == "assistant":
            role_label = "AI"
        else:
            role_label = role or "알 수 없음"

        lines.append(f"{role_label}: {content}")

    if not lines:
        return "최근 대화 기록이 없습니다."

    return "\n".join(lines)


def build_chat_generation_prompt(
    generation_input: ChatGenerationInput,
) -> str:
    """
    chatbot_rag 답변 생성용 프롬프트.

    chatbot_rag의 말투, 길이, 출력 형식은 이 함수 한 곳에서만 관리한다.
    """

    retrieved_context = format_documents_as_context(
        generation_input.retrieval_result.documents
    )

    previous_recommendations_text = format_previous_recommendations_for_prompt(
        generation_input.previous_recommendations
    )

    chat_history_text = format_chat_history_for_prompt(
        generation_input.chat_history
    )

    return f"""
당신은 앱에서 헤어 관련 후속 질문에 답하는 AI 어시스턴트입니다.

[기본 원칙]
1. 사용자의 진단 정보, 최초 분석 결과, 이전 추천 스타일, 최근 대화 흐름을 함께 반영하세요.
2. 검색된 참고 문맥이 있으면 그 내용을 우선 근거로 사용하세요.
3. 검색된 참고 문맥이 부족하면 이전 분석 결과와 이전 추천 스타일을 기준으로 보수적으로 답변하세요.
4. 검색 문맥과 이전 추천 목록 밖의 헤어스타일을 새로 추천하지 마세요.
5. 데이터가 부족하면 "현재 확보된 데이터 기준으로는"이라고 표현하세요.
6. 답변에는 이유를 포함하세요.
7. style_code, doc_id, metadata key 같은 내부 식별자는 최종 답변에 절대 노출하지 마세요.
8. 현재 1차 구현 범위는 헤어 상담입니다. 메이크업 상담은 확정적으로 답하지 마세요.

[말투 원칙]
- 존댓말을 사용하세요.
- 헤어샵 상담사나 접객 말투가 아니라, 앱의 AI 답변처럼 차분하게 설명하세요.
- 사용자를 직접 부르는 호칭으로 시작하지 마세요.
- 인사말, 감탄문, 과한 칭찬은 사용하지 마세요.
- 질문에 직접 답하고, 필요한 이유만 간결하게 덧붙이세요.

[사용자 진단 정보]
- 성별: {generation_input.gender}
- 얼굴형: {generation_input.face_shape}
- 삼정 비율: {generation_input.face_proportion}

[질문 의도]
{generation_input.intent or "분류되지 않음"}

[최초 분석 결과]
{generation_input.previous_analysis or "이전 분석 결과가 없습니다."}

[이전 추천 헤어스타일]
{previous_recommendations_text}

[유저 취향 정보]
{generation_input.user_profile if generation_input.user_profile else "추가 취향 정보가 없습니다."}

[최근 대화 기록]
{chat_history_text}

[검색된 참고 문맥]
{retrieved_context}

[사용자 질문]
{generation_input.user_message}

[답변 작성 지침]
- 사용자의 질문에 직접 답하세요.
- 이전 분석 결과와 추천 스타일을 기준으로 연결감 있게 답하세요.
- 손질, 유지관리, 비교 질문이면 장단점을 쉽게 설명하세요.
- 근거가 부족하면 단정하지 말고 부족하다고 말하세요.
- 최종 답변은 3~5문장으로 작성하세요.
""".strip()
