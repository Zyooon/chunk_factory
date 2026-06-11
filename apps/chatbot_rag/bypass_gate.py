from __future__ import annotations

from apps.chatbot_rag.intents import (
    INTENT_GREETING,
    INTENT_IRRELEVANT,
    INTENT_MISSING_ANALYSIS,
    INTENT_NOISE,
    INTENT_SMALLTALK,
)
from apps.chatbot_rag.static_responses import (
    GREETING_MESSAGE,
    IRRELEVANT_MESSAGE,
    MISSING_ANALYSIS_MESSAGE,
    NOISE_MESSAGE,
    SMALLTALK_MESSAGE,
)

NON_LLM_INTENTS: set[str] = {
    INTENT_GREETING,
    INTENT_SMALLTALK,
    INTENT_IRRELEVANT,
    INTENT_NOISE,
    INTENT_MISSING_ANALYSIS,
}

NON_LLM_RESPONSES: dict[str, str] = {
    INTENT_GREETING: GREETING_MESSAGE,
    INTENT_SMALLTALK: SMALLTALK_MESSAGE,
    INTENT_IRRELEVANT: IRRELEVANT_MESSAGE,
    INTENT_NOISE: NOISE_MESSAGE,
    INTENT_MISSING_ANALYSIS: MISSING_ANALYSIS_MESSAGE,
}


def should_bypass_llm(intent: str | None) -> bool:
    return intent in NON_LLM_INTENTS


def get_bypass_response(intent: str | None) -> str | None:
    return NON_LLM_RESPONSES.get(intent)
