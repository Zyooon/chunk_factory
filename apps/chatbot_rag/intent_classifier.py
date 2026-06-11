from __future__ import annotations

from typing import Any

from apps.chatbot_rag.noise_filter import is_noise
from apps.chatbot_rag.prompts import INTENT_NOISE, get_intent_by_keyword
from apps.chatbot_rag.semantic_classifier import classify_intent_semantically


def get_intent(message: str) -> tuple[str, dict[str, Any]]:
    """
    semantic classifier를 우선 사용하고 keyword classifier를 fallback으로 사용하는 intent 분류 함수.
    """

    if is_noise(message):
        return INTENT_NOISE, {
            "classifier": "noise_filter",
            "semantic_score": 1.0,
            "semantic_intent": INTENT_NOISE,
            "fallback_intent": None,
        }

    semantic_intent, semantic_score = classify_intent_semantically(message)

    if semantic_intent:
        return semantic_intent, {
            "classifier": "semantic",
            "semantic_score": semantic_score,
            "semantic_intent": semantic_intent,
            "fallback_intent": None,
        }

    fallback_intent = get_intent_by_keyword(message)

    return fallback_intent, {
        "classifier": "keyword",
        "semantic_score": semantic_score,
        "semantic_intent": None,
        "fallback_intent": fallback_intent,
    }
