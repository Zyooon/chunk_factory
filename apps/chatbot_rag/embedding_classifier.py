from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from apps.chatbot_rag.intents import (
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

_INTENT_EXAMPLES: dict[str, list[str]] = {
    INTENT_GREETING: [
        "안녕하세요",
        "안녕!",
        "하이",
        "hello",
        "hi",
        "반가워요",
        "반갑습니다",
        "처음 왔어요",
    ],
    INTENT_SMALLTALK: [
        "고마워요",
        "감사합니다",
        "알겠어요",
        "오케이",
        "네, 알겠습니다",
        "좋아요",
        "이해했어요",
        "그렇군요",
        "도움이 됐어요",
    ],
    INTENT_IRRELEVANT: [
        "오늘 날씨 어때요?",
        "주식 추천해 주세요",
        "파이썬 코딩 알려주세요",
        "맛있는 맛집 알려주세요",
        "재미있는 게임 추천해 주세요",
        "여행 어디가면 좋을까요?",
        "요즘 뉴스 어때요?",
        "영화 추천해 주세요",
        "음식 레시피 알려주세요",
        "정치 얘기 해줘",
        "노래 추천해줘",
    ],
    INTENT_NOISE: [
        "ㅋㅋㅋ",
        "ㅎㅎㅎ",
        "asdf",
        "ㅁㄴㅇㄹ",
        "ㅏㅏㅏ",
        "qwer",
        "zxcv",
        "...",
        "!!!!",
        "ㄱㄴㄷ",
    ],
    INTENT_MOOD_SELECTION: [
        "이 스타일 어떤 분위기예요?",
        "부드러운 느낌으로 연출하고 싶어요",
        "소개팅에 맞는 무드로 해주세요",
        "차분한 이미지를 원해요",
        "어떤 인상을 줄 수 있을까요",
        "데이트에 맞게 연출하고 싶어요",
        "면접에 맞게 스타일링하고 싶어요",
        "세련된 느낌으로 하고 싶어요",
        "자연스럽게 보이고 싶어요",
        "너무 세 보이지 않게 하고 싶어요",
        "어떤 분위기로 가져가면 좋을까요?",
    ],
    INTENT_STYLE_FIT: [
        "이 헤어스타일이 나한테 어울릴까요?",
        "추천받은 스타일이 내 얼굴형에 맞을까요?",
        "이 메이크업이 나한테 괜찮을까요?",
        "짧은 머리가 나에게 잘 맞을까요?",
        "앞머리를 하면 어때 보일까요?",
        "이 스타일이 세련돼 보일까요?",
        "볼살을 커버할 수 있는 스타일인가요?",
        "나한테 어울리는 스타일인지 궁금해요",
        "이 스타일로 달라지고 싶어요",
        "어려 보이는 스타일인가요?",
        "얼굴이 길어서 어떤 스타일이 맞을지 고민돼요",
        "이마가 좁은데 어울리는 스타일인가요?",
    ],
    INTENT_STYLING_METHOD: [
        "이 헤어스타일은 어떻게 손질하나요?",
        "드라이기로 어떻게 세팅하면 되나요?",
        "고데기 사용 방법이 궁금해요",
        "왁스는 어떻게 바르면 되나요?",
        "이 립 색은 어떻게 연출하나요?",
        "블러셔는 어디에 어떻게 바르면 되나요?",
        "섀도우를 어떻게 발라야 또렷해 보일까요?",
        "베이스 메이크업 순서가 어떻게 되나요?",
        "사진처럼 연출하려면 어떻게 해야 하나요?",
        "스타일링 방법을 알려주세요",
        "스프레이는 언제 뿌리면 되나요?",
        "화장법을 알려주세요",
    ],
    INTENT_MAINTENANCE: [
        "이 헤어스타일은 유지하기 어렵나요?",
        "관리하는 데 얼마나 시간이 걸리나요?",
        "커트는 얼마나 자주 해야 하나요?",
        "펌이 얼마나 오래 가나요?",
        "미용실에 얼마나 자주 가야 하나요?",
        "손이 많이 가는 스타일인가요?",
        "메이크업이 무너지지 않게 유지하려면 어떻게 해야 하나요?",
        "지속력이 좋은 방법이 있나요?",
        "이 스타일 관리 주기가 어떻게 되나요?",
        "오래 유지할 수 있는 스타일인가요?",
    ],
    INTENT_COMPARISON: [
        "두 스타일 중 어느 게 더 나을까요?",
        "리프와 댄디 중 뭐가 더 나한테 어울릴까요?",
        "이 두 스타일을 비교해 주세요",
        "피치랑 코랄이랑 어느 게 더 나에게 맞을까요?",
        "둘 중 어떤 게 더 관리하기 쉬운가요?",
        "뭐가 더 세련돼 보일까요?",
        "두 스타일의 차이점이 뭔가요?",
        "어느 스타일이 더 나을까요?",
    ],
}


class EmbeddingIntentClassifier:
    _MODEL_NAME = "jhgan/ko-sroberta-multitask"
    _DEFAULT_THRESHOLD = 0.55

    def __init__(self, threshold: float = 0.55) -> None:
        self._threshold = threshold
        self._model = SentenceTransformer(self._MODEL_NAME)
        self._intent_embeddings: dict[str, np.ndarray] = {}
        self._build_index()

    def _build_index(self) -> None:
        for intent, examples in _INTENT_EXAMPLES.items():
            embeddings = self._model.encode(examples, normalize_embeddings=True)
            self._intent_embeddings[intent] = np.array(embeddings)

    def classify(self, message: str) -> str:
        if not message.strip():
            return INTENT_NOISE

        query_embedding = self._model.encode([message], normalize_embeddings=True)[0]

        best_intent = INTENT_UNCLEAR
        best_score = -1.0

        for intent, embeddings in self._intent_embeddings.items():
            score = float((embeddings @ query_embedding).max())
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_score < self._threshold:
            return INTENT_UNCLEAR

        return best_intent
