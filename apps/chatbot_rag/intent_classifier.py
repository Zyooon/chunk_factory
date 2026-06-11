from __future__ import annotations

from typing import Any

from apps.chatbot_rag.intent_keywords import get_intent_by_keyword
from apps.chatbot_rag.intents import INTENT_NOISE
from apps.chatbot_rag.noise_filter import is_noise
from apps.chatbot_rag.semantic_classifier import classify_intent_semantically


def get_intent(message: str) -> tuple[str, dict[str, Any]]:
    if is_noise(message):
        return INTENT_NOISE, {"classifier": "noise_filter", "semantic_score": 1.0}

    semantic_intent, semantic_score = classify_intent_semantically(message)

    if semantic_intent:
        return semantic_intent, {"classifier": "semantic", "semantic_score": semantic_score}

    fallback_intent = get_intent_by_keyword(message)
    return fallback_intent, {"classifier": "keyword", "semantic_score": semantic_score}
