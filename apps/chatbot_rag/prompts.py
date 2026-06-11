from __future__ import annotations

from typing import Any

from apps.rag_core.schemas import ChatGenerationInput
from apps.rag_core.utils import format_documents_as_context


INTENT_STYLE_FIT = "style_fit"
INTENT_STYLING_METHOD = "styling_method"
INTENT_MAINTENANCE = "maintenance"
INTENT_COMPARISON = "comparison"
INTENT_GENERAL_FOLLOWUP = "general_followup"
INTENT_MOOD_SELECTION = "mood_selection"
INTENT_MOOD_CHOICE = "mood_choice"
INTENT_UNCLEAR = "unclear"
INTENT_MISSING_ANALYSIS = "missing_analysis"

# non-RAG intent
INTENT_GREETING = "greeting"
INTENT_SMALLTALK = "smalltalk"
INTENT_IRRELEVANT = "irrelevant"
INTENT_NOISE = "noise"

CATEGORY_HAIR = "hair"
CATEGORY_MAKEUP = "makeup"
PENDING_SELECTION_MOOD = "mood"


MISSING_ANALYSIS_MESSAGE = (
    "아직 추천 결과가 없어 피드백 상담을 진행하기 어려워요. "
    "먼저 헤어 또는 메이크업 추천 결과를 받은 뒤 다시 질문해 주세요."
)


CLARIFICATION_OPTIONS = [
    "추천받은 헤어스타일이 나에게 어울리는지 궁금해요.",
    "추천받은 헤어스타일의 손질 방법이 궁금해요.",
    "추천받은 메이크업이 나에게 어울리는지 궁금해요.",
    "추천받은 메이크업의 연출 방법이 궁금해요.",
    "추천 스타일끼리 비교해 보고 싶어요.",
]

MOOD_SELECTION_KEYWORDS = [
    "분위기",
    "느낌",
    "무드",
    "이미지",
    "인상",
    "소개팅에 맞게",
    "데이트에 맞게",
    "면접에 맞게",
    "부드럽게",
    "차분하게",
    "세련되게",
    "깔끔하게",
    "자연스럽게",
    "너무 세 보이지",
    "어떤 느낌",
    "어떤 분위기",
]

MOOD_OPTIONS = [
    {
        "id": "neat_trustworthy",
        "label": "단정하고 신뢰감 있는 느낌",
        "mood_keywords": ["단정함", "신뢰감", "깔끔함"],
    },
    {
        "id": "soft_comfortable",
        "label": "부드럽고 편안한 느낌",
        "mood_keywords": ["부드러움", "편안함", "자연스러움"],
    },
    {
        "id": "stylish_clean",
        "label": "세련되고 깔끔한 느낌",
        "mood_keywords": ["세련됨", "깔끔함", "정돈됨"],
    },
    {
        "id": "natural_effortless",
        "label": "자연스럽고 꾸미지 않은 느낌",
        "mood_keywords": ["자연스러움", "내추럴", "담백함"],
    },
]


INTENT_KEYWORDS = {
    INTENT_MOOD_SELECTION: MOOD_SELECTION_KEYWORDS,
    INTENT_STYLE_FIT: [
        "어울",
        "괜찮",
        "맞아",
        "어때",
        "나한테",
        "잘 맞",
        "추천받은",
        "세련",
        "깔끔",
        "부드러운",
        "부드럽",
        "차분",
        "어려 보",
        "성숙",
        "튀는 건 싫",
        "바꾸고 싶",
        "달라지고 싶",
        "짧은 머리",
        "기장감",
        "앞머리",
        "이마",
        "얼굴이 길어",
        "볼살",
        "고민",
        "데일리",
        "뭐가 좋아",
        "어떤 게 좋아",
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
        "바르는",
        "바르면",
        "립",
        "블러셔",
        "섀도우",
        "쉐도우",
        "베이스",
        "연출",
        "화장법",
        "메이크업법",
        "사진",
        "또렷",
        "어떻게 해야",
        "어떻게 하면",
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
        "수정",
        "무너짐",
        "지속",
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
        "피치랑",
        "코랄이랑",
        "로즈랑",
        "브라운이랑",
        "vs",
    ],
}


MAKEUP_CATEGORY_KEYWORDS = [
    "메이크업",
    "화장",
    "립",
    "블러셔",
    "치크",
    "섀도우",
    "쉐도우",
    "아이섀도우",
    "베이스",
    "톤업",
    "퍼스널컬러",
    "봄웜",
    "여름쿨",
    "가을웜",
    "겨울쿨",
    "피치",
    "코랄",
    "주시",
    "쥬시",
    "듀이",
    "내추럴",
    "로즈",
    "브라운",
    "시크",
    "오피스",
    "버건디",
    "글램",
    "레드",
]


HAIR_CATEGORY_KEYWORDS = [
    "헤어",
    "머리",
    "스타일",
    "커트",
    "펌",
    "앞머리",
    "옆머리",
    "정수리",
    "볼륨",
    "드라이",
    "왁스",
    "스프레이",
]


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


GREETING_MESSAGE = (
    "추천받은 헤어스타일이나 메이크업에 대해 궁금한 점을 물어봐 주세요."
)


SMALLTALK_MESSAGE = (
    "좋아요. 추천 결과에 대해 더 궁금한 점이 있으면 이어서 물어봐 주세요."
)


IRRELEVANT_MESSAGE = (
    "저는 추천받은 헤어스타일과 메이크업에 대한 피드백 상담을 도와드리는 챗봇입니다. "
    "추천 결과의 어울림, 손질·연출 방법, 유지 관리, 스타일 비교에 대해 질문해 주세요."
)


NOISE_MESSAGE = (
    "질문을 이해하기 어려워요. 추천받은 헤어스타일이나 메이크업에 대해 조금 더 구체적으로 입력해 주세요."
)


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
            "추천 결과에 대해 어떤 피드백 상담이 필요하신지 조금만 더 알려주세요.",
            "",
            *option_lines,
        ]
    )


def get_mood_option_by_id(option_id: str | None) -> dict | None:
    if not option_id:
        return None

    for option in MOOD_OPTIONS:
        if option["id"] == option_id:
            return option

    return None


def build_mood_selection_title() -> str:
    return "추천받은 스타일을 어떤 분위기로 가져가고 싶으신가요?"



def detect_question_category(message: str) -> str:
    """
    사용자 메시지에서 hair/makeup category를 추론한다.

    메이크업 키워드가 명확하면 makeup을 우선한다.
    둘 다 없으면 hair를 기본값으로 둔다.
    """
    normalized_message = message.strip().lower()

    if any(keyword.lower() in normalized_message for keyword in MAKEUP_CATEGORY_KEYWORDS):
        return CATEGORY_MAKEUP

    if any(keyword.lower() in normalized_message for keyword in HAIR_CATEGORY_KEYWORDS):
        return CATEGORY_HAIR

    return CATEGORY_HAIR


def format_previous_recommendations_for_prompt(
    previous_recommendations: list[dict[str, Any]],
    category: str | None = None,
) -> str:
    """
    이전 추천 스타일 목록을 프롬프트용 문자열로 변환한다.

    style_code는 내부 식별자이므로 프롬프트에도 전달하지 않는다.
    category가 주어지면 해당 category 추천만 우선 표시한다.
    """

    if not previous_recommendations:
        return "이전 추천 스타일 정보가 없습니다."

    lines: list[str] = []

    for recommendation in previous_recommendations:
        if category and recommendation.get("category") not in {category, None}:
            continue

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


def _get_category_label(category: str | None) -> str:
    if category == CATEGORY_MAKEUP:
        return "메이크업"
    return "헤어"


def _get_category_specific_rules(category: str | None) -> str:
    if category == CATEGORY_MAKEUP:
        return "\n".join(
            [
                "- 현재 질문은 추천받은 메이크업에 대한 피드백 상담으로 처리하세요.",
                "- 메이크업 답변은 퍼스널컬러, 이전 추천 메이크업, 검색된 메이크업 문맥을 기준으로 하세요.",
                "- 얼굴형이나 삼정 비율을 메이크업 추천 근거로 사용하지 마세요.",
                "- 검색 문맥에 없는 메이크업 그룹을 임의로 새로 추천하지 마세요.",
            ]
        )

    return "\n".join(
        [
            "- 현재 질문은 추천받은 헤어스타일에 대한 피드백 상담으로 처리하세요.",
            "- 헤어 답변은 얼굴형, 삼정 비율, 이전 추천 헤어스타일, 검색된 헤어 문맥을 기준으로 하세요.",
            "- 퍼스널컬러를 헤어 추천의 주요 근거로 사용하지 마세요.",
            "- 검색 문맥에 없는 헤어스타일을 임의로 새로 추천하지 마세요.",
        ]
    )


def build_chat_generation_prompt(
    generation_input: ChatGenerationInput,
) -> str:
    """
    chatbot_rag 답변 생성용 프롬프트.

    chatbot_rag의 말투, 길이, 출력 형식은 이 함수 한 곳에서만 관리한다.
    """

    category = generation_input.category or CATEGORY_HAIR
    category_label = _get_category_label(category)

    retrieved_context = format_documents_as_context(
        generation_input.retrieval_result.documents
    )
    previous_recommendations_text = format_previous_recommendations_for_prompt(
        generation_input.previous_recommendations,
        category=category,
    )
    detected_style_text = format_detected_style_for_prompt(
        detected_style=generation_input.detected_style,
        detected_style_is_recommended=generation_input.detected_style_is_recommended,
        category=category,
    )
    chat_history_text = format_chat_history_for_prompt(
        generation_input.chat_history
    )
    category_specific_rules = _get_category_specific_rules(category)

    return f"""
당신은 앱에서 추천받은 헤어스타일과 메이크업 결과에 대한 피드백 질문에 답하는 AI 어시스턴트입니다.

[기본 원칙]
1. 사용자의 진단 정보, 최초 분석 결과, 이전 추천 스타일, 최근 대화 흐름을 함께 반영하세요.
2. 사용자가 새 추천을 요구하더라도 기본적으로 이전 추천 결과에 대한 피드백 범위 안에서 답변하세요.
3. 검색된 참고 문맥이 있으면 그 내용을 우선 근거로 사용하세요.
4. 검색된 참고 문맥이 부족하면 이전 분석 결과와 이전 추천 스타일을 기준으로 보수적으로 답변하세요.
5. 기본적으로 이전 추천 스타일을 우선 기준으로 답변하세요.
6. 사용자가 이전 추천 목록 밖의 특정 스타일을 직접 물어본 경우에는 검색된 참고 문맥을 기준으로 설명할 수 있지만, 새 추천처럼 확장하지 마세요.
7. 이전 추천 목록 밖의 스타일을 답변할 때는 그 스타일을 "추천받은 스타일"처럼 표현하지 마세요.
8. style_code, doc_id, metadata key 같은 내부 식별자는 최종 답변에 절대 노출하지 마세요.
9. 데이터가 부족하면 "현재 모아둔 정보로 먼저 확인해 드리자면," 이라고 표현하세요.
10. 답변에는 이유를 포함하세요.

[카테고리별 원칙]
{category_specific_rules}

[말투 원칙]
- 존댓말을 사용하세요.
- 매장 상담사나 접객 말투가 아니라, 앱의 AI 답변처럼 차분하게 설명하세요.
- 사용자를 직접 부르는 호칭으로 시작하지 마세요.
- 인사말, 감탄문, 과한 칭찬은 사용하지 마세요.
- 질문에 직접 답하고, 필요한 이유만 간결하게 덧붙이세요.

[사용자 진단 정보]
- 성별: {generation_input.gender}
- 얼굴형: {generation_input.face_shape}
- 삼정 비율: {generation_input.face_proportion}
- 퍼스널컬러: {generation_input.personal_color or "정보 없음"}

[질문 카테고리]
{category_label}

[질문 의도]
{generation_input.intent or "분류되지 않음"}

[최초 분석 결과]
{generation_input.previous_analysis or "이전 분석 결과가 없습니다."}

[이전 추천 스타일]
{previous_recommendations_text}

[사용자가 질문한 스타일]
{detected_style_text}

[유저 취향 정보]
{generation_input.user_profile if generation_input.user_profile else "추가 취향 정보가 없습니다."}

[최근 대화 기록]
{chat_history_text}

[검색된 참고 문맥]
{retrieved_context}

[사용자 피드백 질문]
{generation_input.user_message}

[답변 작성 지침]
- 사용자의 피드백 질문에 직접 답하세요.
- 이전 분석 결과와 추천 스타일을 기준으로 연결감 있게 답하세요.
- 선택된 분위기나 무드 정보가 있으면 같은 추천 스타일 안에서 연출 방향을 조정해 답하세요.
- 손질, 연출, 유지관리, 비교 질문이면 장단점을 쉽게 설명하세요.
- 근거가 부족하면 단정하지 말고 부족하다고 말하세요.
- 최종 답변은 2~3문장으로 작성하세요.
- 한 문장은 너무 길게 쓰지 마세요.
- 핵심 결론을 첫 문장에 말하세요.
- 불필요한 다른 스타일 비교는 하지 마세요.
- 사용자가 묻지 않은 추천 스타일을 새로 언급하지 마세요.
""".strip()


def format_detected_style_for_prompt(
    detected_style: dict[str, str] | None,
    detected_style_is_recommended: bool,
    category: str | None = None,
) -> str:
    """
    사용자 현재 질문에서 감지된 헤어스타일 또는 메이크업 스타일 정보를 프롬프트용 문자열로 변환한다.

    style_code는 내부 식별자이므로 프롬프트에 넣지 않는다.
    """

    category_label = _get_category_label(category)

    if not detected_style:
        return f"사용자 질문에서 특정 {category_label} 스타일이 감지되지 않았습니다."

    style_name = detected_style.get("style_name")

    if not style_name:
        return f"사용자 질문에서 특정 {category_label} 스타일이 감지되지 않았습니다."

    if detected_style_is_recommended:
        relation_text = "이 스타일은 이전 추천 목록에 포함되어 있습니다."
    else:
        relation_text = (
            "이 스타일은 이전 추천 목록에는 없지만, "
            "사용자가 직접 질문한 스타일입니다."
        )

    return "\n".join(
        [
            f"- 스타일명: {style_name}",
            f"- 추천 목록 포함 여부: {relation_text}",
        ]
    )
