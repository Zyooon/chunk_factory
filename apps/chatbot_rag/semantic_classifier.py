from __future__ import annotations

from functools import lru_cache
from typing import Any

from apps.chatbot_rag.intents import (
    INTENT_COMPARISON,
    INTENT_IRRELEVANT,
    INTENT_MAINTENANCE,
    INTENT_MOOD_SELECTION,
    INTENT_NOISE,
    INTENT_STYLE_FIT,
    INTENT_STYLING_METHOD,
)
from apps.chatbot_rag.noise_filter import is_noise

MODEL_NAME = "jhgan/ko-sroberta-multitask"
SEMANTIC_INTENT_THRESHOLD = 0.58
SEMANTIC_IRRELEVANT_THRESHOLD = 0.68

INTENT_EXAMPLES: dict[str, list[str]] = {
    INTENT_STYLE_FIT: [
        "이 스타일이 나한테 어울릴까?",
        "추천받은 머리가 내 얼굴형에 괜찮아?",
        "이 메이크업이 내 퍼스널컬러랑 잘 맞아?",
        "이 스타일이 너무 부담스럽지는 않을까?",
        "데일리로 해도 괜찮을까?",
        "이 스타일이 출근할 때도 괜찮을까요?",
        "출근할 때 하기엔 괜찮은 스타일인가요?",
        "아이비리그는 데일리로 하기 괜찮은 스타일인가요?",
        "이 머리 하면 얼굴이 더 길어 보이지 않을까?",
        "얼굴형 단점이 더 부각될까 봐 걱정돼요",
        "이 스타일이 얼굴을 더 둥글어 보이게 하지는 않을까?",
        "볼살이 더 부각될까요?",
        "출근할 때 하기엔 너무 화려하지 않을까요?",
        "이 메이크업이 얼굴을 칙칙해 보이게 하지는 않을까요?",
        "쿨톤인데 코랄 느낌을 살짝 써도 괜찮을까요?",
        "이 색이 제 퍼스널컬러에 맞을까요?",
        "로즈톤이 저한테 어울릴까요?",
        "처음 만나는 사람에게 좋은 인상을 주려면 어떤 스타일이 좋아?",
        "목이 짧은 편이면 어떤 기장이 나아?",
        "눈이 작은 편인데 추천 스타일이 더 작아 보이게 하진 않을까?",
        "회사에서는 단정하고 퇴근 후에는 캐주얼하게 보이려면 어떤 방향이 좋아?",
        "면접 볼 때 이 머리 해도 단정해 보일까요?",
    ],
    INTENT_STYLING_METHOD: [
        "이 머리는 어떻게 손질해?",
        "이 스타일은 드라이를 어떻게 해야 해?",
        "이 메이크업은 어떻게 연출하면 좋아?",
        "사진 찍을 때 더 또렷하게 하려면 어떻게 해야 해?",
        "립이나 블러셔는 어떻게 바르면 좋아?",
        "볼륨은 어디에 넣는 게 좋아?",
        "얼굴이 둥글어 보이지 않게 하려면 어디에 볼륨을 줘야 해요?",
        "정수리 볼륨은 얼마나 살리는 게 좋아요?",
        "피부 표현은 매트하게 하는 게 좋아요 촉촉하게 하는 게 좋아요?",
        "립은 어느 정도 진하게 바르는 게 좋아?",
        "블러셔는 어느 위치에 바르면 자연스러워요?",
        "코가 낮은 편이면 하이라이터 방향이 달라질까?",
        "귀 뒤로 넘겼을 때 자연스러운 스타일은 어떤 방향이야?",
        "원하는 스타일 설명할 때 어떤 단어를 쓰면 잘 통할까?",
        "눈이 처진 편이면 어떤 라인이 자연스럽게 보완돼?",
        "언더라인을 그리면 내 눈 타입에 자연스러울까?",
        "자연스러운 웨이브를 살리려면 어떤 방법이 좋아?",
        "뒷모습도 예쁜 스타일로 가려면 어떤 걸 고려해야 해?",
    ],
    INTENT_MAINTENANCE: [
        "이 스타일은 관리하기 쉬워?",
        "얼마나 자주 커트해야 해?",
        "손이 많이 가는 스타일이야?",
        "메이크업이 오래 유지되려면 어떻게 해야 해?",
        "유지관리하기 편한 편이야?",
        "머리가 자라면 모양이 쉽게 무너질까?",
        "머리가 자라면 모양이 빨리 무너질까요?",
        "자랐을 때 지저분해질까요?",
        "모양이 오래 유지될까요?",
        "커트 주기는 어느 정도가 좋아요?",
        "헬멧 써도 덜 망가지는 스타일은 뭐야?",
        "바람에 덜 흐트러지는 스타일이 있을까?",
        "위생 모자 써도 덜 눌려?",
    ],
    INTENT_COMPARISON: [
        "추천받은 스타일 중 뭐가 더 나아?",
        "이 스타일이랑 저 스타일 중 뭐가 나한테 더 맞아?",
        "둘 중 어떤 게 더 괜찮아?",
        "추천받은 메이크업 중 뭐가 더 자연스러워?",
        "면접에는 추천받은 것 중 뭐가 제일 괜찮아?",
        "댄디랑 아이비리그 중 뭐가 더 깔끔해 보여요?",
        "추천받은 스타일 중 가장 무난한 건 뭐야?",
        "가장 깔끔해 보이는 스타일은 뭐야?",
        "이미지 변신이 제일 큰 스타일은 뭐야?",
        "로즈 메이크업이랑 내추럴 메이크업 중 뭐가 더 잘 맞아요?",
    ],
    INTENT_MOOD_SELECTION: [
        "이 스타일을 어떤 분위기로 가져가면 좋을까?",
        "소개팅에 맞게 어떤 느낌으로 하면 좋을까?",
        "자연스럽고 꾸미지 않은 느낌으로 가고 싶어",
        "꾸미지 않은 자연스러운 분위기로 가고 싶어",
        "어떤 이미지로 연출하면 좋을까?",
        "면접용으로 분위기 맞출 수 있을까?",
        "추천받은 메이크업을 면접용으로 바꾸면 어떻게 해야 해요?",
        "메이크업을 출근용 분위기로 바꾸고 싶어요",
        "소개팅 분위기에 어울리는 스타일로 바꿔줄 수 있어?",
        "어떤 무드로 가져가면 좋을지 골라줘",
        # 제거됨: "부드러운 분위기로 보이고 싶어", "차분하고 깔끔한 느낌으로 하고 싶어",
        # "부드럽고 차분한 분위기로 보이게 할 수 있을까요?" — style_fit 예제와 의미 겹침
        # 제거됨: "면접 볼 때 이 머리 해도 단정해 보일까요?", "면접에서 단정한 인상으로 보이고 싶어요"
        # — 단순 어울림 확인은 style_fit이 담당
    ],
    INTENT_IRRELEVANT: [
        "오늘 날씨 어때?",
        "다른 주제에 대해 알려줘",
        "맛있는 음식 추천해줘",
        "여행 계획을 세워줘",
        "영화 추천해줘",
    ],
}


def _load_sentence_transformer_class() -> Any | None:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    return SentenceTransformer


@lru_cache(maxsize=1)
def _get_model() -> Any | None:
    SentenceTransformer = _load_sentence_transformer_class()
    if SentenceTransformer is None:
        return None

    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _get_example_embeddings() -> tuple[list[str], list[str], Any] | None:
    model = _get_model()
    if model is None:
        return None

    intents: list[str] = []
    examples: list[str] = []

    for intent, intent_examples in INTENT_EXAMPLES.items():
        for example in intent_examples:
            intents.append(intent)
            examples.append(example)

    try:
        embeddings = model.encode(
            examples,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
    except Exception:
        return None

    return intents, examples, embeddings


def classify_intent_semantically(message: str) -> tuple[str | None, float]:
    """
    ko-sroberta 기반 semantic intent 분류를 수행한다.

    모델 또는 의존성이 없으면 (None, 0.0)을 반환하여 keyword fallback이 동작하게 한다.
    """

    normalized_message = message.strip()

    if is_noise(normalized_message):
        return INTENT_NOISE, 1.0

    cached_examples = _get_example_embeddings()
    model = _get_model()

    if cached_examples is None or model is None:
        return None, 0.0

    intents, _examples, example_embeddings = cached_examples

    try:
        from sentence_transformers import util

        message_embedding = model.encode(
            normalized_message,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
        scores = util.cos_sim(message_embedding, example_embeddings)[0]
        best_index = int(scores.argmax().item())
        best_score = float(scores[best_index].item())
        best_intent = intents[best_index]
    except Exception:
        return None, 0.0

    if best_intent == INTENT_IRRELEVANT:
        if best_score >= SEMANTIC_IRRELEVANT_THRESHOLD:
            return best_intent, best_score
        return None, best_score

    if best_score >= SEMANTIC_INTENT_THRESHOLD:
        return best_intent, best_score

    return None, best_score
