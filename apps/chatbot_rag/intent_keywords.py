from __future__ import annotations

from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_COMPARISON,
    INTENT_GREETING,
    INTENT_IRRELEVANT,
    INTENT_MAINTENANCE,
    INTENT_MOOD_SELECTION,
    INTENT_NOISE,
    INTENT_SMALLTALK,
    INTENT_STYLE_FIT,
    INTENT_STYLING_METHOD,
    INTENT_UNCLEAR,
)
from apps.chatbot_rag.noise_filter import is_noise

MOOD_SELECTION_KEYWORDS = [
    "분위기",
    "무드",
    "소개팅에 맞게",
    "데이트에 맞게",
    "면접에 맞게",
    "면접용으로 바꾸",
    "출근용으로 바꾸",
    "데이트용으로 바꾸",
    "메이크업을 면접용",
    "메이크업 분위기",
    "부드럽게",
    "차분하게",
    "세련되게",
    "깔끔하게",
    "자연스럽게",
    "너무 세 보이지",
    "어떤 느낌",
    "어떤 분위기",
    "어떤 이미지로",
    "이미지로 연출",
    "분위기 맞출",
]

COMPARISON_PRIORITY_PHRASES = [
    "추천받은 것 중",
    "추천받은 스타일 중",
    "추천받은 메이크업 중",
    "뭐가 제일",
    "뭐가 가장",
    "가장 괜찮",
    "제일 괜찮",
    "중 뭐가",
    "중에 뭐",
    "둘 중",
]

STYLE_FIT_PRIORITY_PHRASES = [
    "데일리로 하기 괜찮",
    "데일리로 괜찮",
    "면접 볼 때",
    "이 머리 해도 단정",
    "이 스타일 괜찮",
    "스타일인가요",
]

INTENT_KEYWORDS: dict[str, list[str]] = {
    INTENT_COMPARISON: [
        "비교",
        "뭐가 더",
        "어느 게",
        "어떤 게",
        "둘 중",
        "중 뭐가",
        "중에 뭐",
        "제일",
        "가장",
        "더 나아",
        "더 좋아",
        "더 잘",
        "랑",
        "이랑",
        "vs",
        "리프랑",
        "퀴프랑",
        "댄디랑",
        "피치랑",
        "코랄이랑",
        "로즈랑",
        "브라운이랑",
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
        "무너질",
        "무너지",
        "자라면",
        "자랐을 때",
        "지속",
        "비용",
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
        "볼륨",
        "어디에 넣",
        "어디에 볼륨",
        "정수리 볼륨",
        "옆 볼륨",
        "피부 표현",
        "매트",
        "촉촉",
        "진하게",
        "연하게",
    ],
    INTENT_MOOD_SELECTION: MOOD_SELECTION_KEYWORDS,
    INTENT_STYLE_FIT: [
        "어울",
        "괜찮",
        "맞아",
        "어때",
        "나한테",
        "잘 맞",
        "퍼스널컬러",
        "쿨톤",
        "웜톤",
        "봄웜",
        "여름쿨",
        "가을웜",
        "겨울쿨",
        "코랄",
        "로즈",
        "피치",
        "레드",
        "브라운",
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
        "길어 보",
        "둥글어 보",
        "얼굴형",
        "볼살",
        "칙칙",
        "화려하지",
        "부담",
        "고민",
        "데일리",
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

AMBIGUOUS_MESSAGES: set[str] = {
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

GREETING_KEYWORDS = [
    "안녕",
    "안녕하세요",
    "하이",
    "hello",
    "hi",
    "반가워",
    "반갑습니다",
]

SMALLTALK_KEYWORDS = [
    "고마워",
    "감사",
    "좋아",
    "알겠어",
    "오케이",
    "ㅇㅋ",
    "네",
    "응",
]

IRRELEVANT_KEYWORDS = [
    "날씨",
    "주식",
    "코딩",
    "파이썬",
    "게임",
    "여행",
    "음식",
    "맛집",
    "뉴스",
    "정치",
    "영화",
    "노래",
]


def _has_any(message: str, phrases: list[str]) -> bool:
    return any(phrase.lower() in message for phrase in phrases)


def get_intent_by_keyword(message: str) -> str:
    if is_noise(message):
        return INTENT_NOISE

    normalized_message = message.strip().lower()

    if any(keyword in normalized_message for keyword in IRRELEVANT_KEYWORDS):
        return INTENT_IRRELEVANT

    if _has_any(normalized_message, COMPARISON_PRIORITY_PHRASES):
        return INTENT_COMPARISON

    if _has_any(normalized_message, STYLE_FIT_PRIORITY_PHRASES):
        return INTENT_STYLE_FIT

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in normalized_message for keyword in keywords):
            return intent

    if normalized_message in AMBIGUOUS_MESSAGES:
        return INTENT_UNCLEAR

    if any(keyword in normalized_message for keyword in GREETING_KEYWORDS):
        return INTENT_GREETING

    if normalized_message in SMALLTALK_KEYWORDS:
        return INTENT_SMALLTALK

    return INTENT_UNCLEAR


def detect_question_category(message: str) -> str:
    normalized_message = message.strip().lower()

    if any(keyword.lower() in normalized_message for keyword in MAKEUP_CATEGORY_KEYWORDS):
        return CATEGORY_MAKEUP

    if any(keyword.lower() in normalized_message for keyword in HAIR_CATEGORY_KEYWORDS):
        return CATEGORY_HAIR

    return CATEGORY_HAIR
