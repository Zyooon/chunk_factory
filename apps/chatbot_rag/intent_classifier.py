from __future__ import annotations

from typing import Any

from apps.chatbot_rag.intent_keywords import get_intent_by_keyword
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
from apps.chatbot_rag.noise_filter import is_noise
from apps.chatbot_rag.semantic_classifier import classify_intent_semantically

KEYWORD_FIRST_INTENTS = {
    INTENT_STYLING_METHOD,
    INTENT_MAINTENANCE,
    INTENT_COMPARISON,
    INTENT_MOOD_SELECTION,
    INTENT_STYLE_FIT,      # keyword가 명확히 매치한 경우 semantic이 오버라이드하지 않도록
    INTENT_IRRELEVANT,
    INTENT_GREETING,
    INTENT_SMALLTALK,
}


def get_intent(message: str) -> tuple[str, dict[str, Any]]:
    if is_noise(message):
        return INTENT_NOISE, {"classifier": "noise_filter", "semantic_score": 1.0}

    keyword_intent = get_intent_by_keyword(message)
    if keyword_intent in KEYWORD_FIRST_INTENTS:
        return keyword_intent, {"classifier": "keyword", "semantic_score": 0.0}

    semantic_intent, semantic_score = classify_intent_semantically(message)

    if semantic_intent:
        return semantic_intent, {"classifier": "semantic", "semantic_score": semantic_score}

    if keyword_intent != INTENT_UNCLEAR:
        return keyword_intent, {"classifier": "keyword", "semantic_score": semantic_score}

    return INTENT_UNCLEAR, {"classifier": "keyword", "semantic_score": semantic_score}
