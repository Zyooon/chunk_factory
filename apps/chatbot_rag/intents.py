from __future__ import annotations

INTENT_STYLE_FIT = "style_fit"
INTENT_STYLING_METHOD = "styling_method"
INTENT_MAINTENANCE = "maintenance"
INTENT_COMPARISON = "comparison"
INTENT_GENERAL_FOLLOWUP = "general_followup"
INTENT_MOOD_SELECTION = "mood_selection"
INTENT_MOOD_CHOICE = "mood_choice"
INTENT_UNCLEAR = "unclear"
INTENT_MISSING_ANALYSIS = "missing_analysis"

# outfit intents
INTENT_OUTFIT_RECOMMENDATION = "outfit_recommendation"
INTENT_OUTFIT_EVENT_COORDINATION = "outfit_event_coordination"
INTENT_OUTFIT_FIT_CHECK = "outfit_fit_check"

OUTFIT_INTENTS: frozenset[str] = frozenset({
    INTENT_OUTFIT_RECOMMENDATION,
    INTENT_OUTFIT_EVENT_COORDINATION,
    INTENT_OUTFIT_FIT_CHECK,
})

# non-RAG intent
INTENT_GREETING = "greeting"
INTENT_SMALLTALK = "smalltalk"
INTENT_IRRELEVANT = "irrelevant"
INTENT_NOISE = "noise"

CATEGORY_HAIR = "hair"
CATEGORY_MAKEUP = "makeup"

# pending selection types
PENDING_SELECTION_MOOD = "mood"
PENDING_OUTFIT_CONTEXT = "outfit_context"
PENDING_OUTFIT_SYNTHESIS_CONFIRMATION = "outfit_synthesis_confirmation"
PENDING_OUTFIT_OPTION_SELECTION = "outfit_option_selection"
PENDING_OUTFIT_USER_IMAGE_REQUIRED = "outfit_user_image_required"
