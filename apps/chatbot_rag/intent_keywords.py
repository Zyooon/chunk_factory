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

# ---------------------------------------------------------------------------
# mood_selection: 분위기 선택을 명시적으로 위임할 때만 포함한다.
# "자연스럽게", "부드럽게", "단정", "캐주얼" 단독으로는 mood_selection이 되지 않는다.
# ---------------------------------------------------------------------------

MOOD_SELECTION_KEYWORDS = [
    "소개팅에 맞게",
    "데이트에 맞게",
    "면접에 맞게",
    "면접용으로 바꾸",
    "출근용으로 바꾸",
    "데이트용으로 바꾸",
    "메이크업을 면접용",
    "메이크업 분위기",
    "분위기로 골라",
    "분위기를 골라",
    "분위기 선택",
    "어떤 분위기로 가져가",
    "어떤 무드로",
    "무드로 가져가",
    "분위기로 맞춰",
    "분위기 맞출",
    "느낌으로 가고 싶",
    "어떤 분위기로 갈지",
]

# ---------------------------------------------------------------------------
# 우선순위 구문 — 키워드 루프보다 먼저 검사한다.
# ---------------------------------------------------------------------------

# mood_selection 우선 판단: 명확한 occasion·선택 위임 표현
# "단정해 보", "단정한 인상" 등 형용사는 제거 — style_fit/styling_method가 담당
MOOD_PRIORITY_PHRASES = [
    "소개팅에 맞게",
    "데이트에 맞게",
    "면접에 맞게",
    "면접용으로 바꾸",
    "메이크업을 면접용",
    "느낌으로 가고 싶",
    "분위기 맞출",
    "어떤 분위기로 가져가",
]

# style_fit 우선 판단: 루프에서 STYLING_METHOD보다 먼저 확정해야 하는 표현
STYLE_FIT_PRIORITY_PHRASES = [
    "출근할 때도 괜찮",
    "출근할 때 괜찮",
    "데일리로 하기 괜찮",
    "데일리로 괜찮",
    "이 스타일 괜찮",
    "스타일인가요",
    "현실적",
    "데이트할 때",
    "면접용으로도",
]

# ---------------------------------------------------------------------------
# intent 키워드 테이블
#
# 루프 우선순위:
#   comparison → maintenance → styling_method → mood_selection → style_fit
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: dict[str, list[str]] = {
    INTENT_COMPARISON: [
        # _has_explicit_comparison()이 구조적 비교를 처리하므로
        # 여기서는 명시적 비교 단어만 남긴다.
        "비교",
        "둘 중",
        " vs ",
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
        # 내구성/유지력 관련
        "망가지",
        "흐트러",
        "눌려",
        "눌리",
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
        "어떻게 해",  # "어떻게 해?" 형태 포함
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
        # 스타일 조작·처리 동사
        "다듬어",
        "조정",
        "피해야",
        "피해서",
        "처리",
        "살리",   # "살리면", "살리려면" 모두 포함
        "바꾸려면",
        "어떻게 잡",
        "정리해야",
        "어떻게 다듬",
        "줄여야",
        "줄이면",
        # 추가: 효과 보완·교정 동사
        "보완",
        "달라질",
        "그리면",
        "고려해야",
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
        "기장",
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
        # 어울림·적합성 표현
        "어울릴까",
        "맞을까",
        "괜찮을까",
        "부담스럽지",
        "자연스러워",
        "변한 느낌",
        "답답해 보",
        "면접용",
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
    "처음이야",
    "처음 뵙겠습니다",
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

# greeting 판단 시 제거할 말미 표현 (감탄사·이모티콘·구두점)
_GREETING_STRIP_CHARS = "!?~ㅎㅋ\t\n "

_GREETING_SET = {kw.lower() for kw in GREETING_KEYWORDS}


def _has_any(message: str, phrases: list[str]) -> bool:
    return any(phrase.lower() in message for phrase in phrases)


def _is_pure_greeting(message: str) -> bool:
    """
    메시지 전체가 인사 표현일 때만 True를 반환한다.

    "하이라이터", "달라질까" 등 인사 단어를 포함하는 긴 문장에서
    greeting이 오분류되는 것을 방지한다.
    """
    stripped = message.strip(_GREETING_STRIP_CHARS).lower()
    return stripped in _GREETING_SET


def _has_explicit_comparison(message: str) -> bool:
    """
    2개 항목을 명확하게 비교하는 구조일 때만 True를 반환한다.

    단순히 "제일", "가장", "어떤 게" 만으로는 True가 되지 않는다.
    "어떤", "뭐가", "좋아", "나아" 단독도 해당하지 않는다.
    """
    # "둘 중" — 두 항목 중 선택
    if "둘 중" in message:
        return True

    # "A vs B"
    if " vs " in message.lower():
        return True

    # "나을까"가 2번 이상 — "A가 나을까 B가 나을까" 구조
    if message.count("나을까") >= 2:
        return True

    # "어느 쪽" — 두 선택지 중 하나를 고르는 표현
    if "어느 쪽" in message:
        return True

    # "더 맞는 건", "더 쉬운 건" — 비교 우위 표현
    if "더 맞는 건" in message or "더 쉬운 건" in message:
        return True

    # "A랑/이랑 B 중에서", "A랑 B 중 ~", "A랑 B 뭐가 더" — 한국어 비교 패턴
    if "랑" in message and any(p in message for p in ["중에서", "중 ", "뭐가 더", "어느 쪽"]):
        return True

    # "추천받은 것 중 뭐가 더 ~" — 복수 후보 중 선택하는 비교 패턴
    if "중" in message and "뭐가 더" in message:
        return True

    return False


def get_intent_by_keyword(message: str) -> str:
    if is_noise(message):
        return INTENT_NOISE

    normalized_message = message.strip().lower()

    if any(keyword in normalized_message for keyword in IRRELEVANT_KEYWORDS):
        return INTENT_IRRELEVANT

    # 명확한 비교 구조 — 2개 항목이 분명할 때만 comparison
    if _has_explicit_comparison(normalized_message):
        return INTENT_COMPARISON

    # 분위기 선택 우선 구문 — 명확한 occasion·선택 위임
    if _has_any(normalized_message, MOOD_PRIORITY_PHRASES):
        return INTENT_MOOD_SELECTION

    # style_fit 우선 구문 — STYLING_METHOD 키워드보다 먼저 확정
    if _has_any(normalized_message, STYLE_FIT_PRIORITY_PHRASES):
        return INTENT_STYLE_FIT

    # 키워드 루프 (comparison → maintenance → styling_method → mood_selection → style_fit)
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in normalized_message for keyword in keywords):
            return intent

    if normalized_message in AMBIGUOUS_MESSAGES:
        return INTENT_UNCLEAR

    # greeting: 전체 문장이 인사일 때만 처리 (부분 문자열 매칭 금지)
    if _is_pure_greeting(normalized_message):
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
