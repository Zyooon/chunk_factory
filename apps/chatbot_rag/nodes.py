from __future__ import annotations

from typing import Any

from apps.chatbot_rag.bypass_gate import get_bypass_response
from apps.chatbot_rag.intent_classifier import get_intent
from apps.chatbot_rag.intent_keywords import detect_question_category
from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_GENERAL_FOLLOWUP,
    INTENT_GREETING,
    INTENT_IRRELEVANT,
    INTENT_MISSING_ANALYSIS,
    INTENT_MOOD_CHOICE,
    INTENT_NOISE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR,
    PENDING_SELECTION_MOOD,
)
from apps.chatbot_rag.memory import (
    append_chat_history,
    extract_simple_user_preferences,
    merge_user_profile,
)
from apps.chatbot_rag.makeup_catalog import find_makeup_style_in_message
from apps.chatbot_rag.selection_options import (
    MOOD_OPTIONS,
    build_mood_selection_title,
    get_mood_option_by_id,
)
from apps.chatbot_rag.static_responses import (
    CLARIFICATION_OPTIONS,
    MISSING_ANALYSIS_MESSAGE,
    build_clarification_message,
)
from apps.chatbot_rag.state import ChatbotState
from apps.chatbot_rag.style_catalog import find_hair_style_in_message
from apps.rag_core.generator import generate_chat_answer
from apps.rag_core.retriever import retrieve_docs
from apps.rag_core.schemas import ChatGenerationInput, RetrievalResult


def check_analysis_exists(state: ChatbotState) -> ChatbotState:
    """
    chatbot_rag 실행 전제 조건을 확인한다.

    chatbot_rag는 추천 결과에 대한 피드백/후속 질문 기능이므로
    previous_analysis와 previous_recommendations가 없으면
    RAG 검색이나 Gemini 호출을 하지 않고 조기 반환한다.
    """

    previous_analysis = state.get("previous_analysis")
    previous_recommendations = state.get("previous_recommendations") or []

    if previous_analysis and previous_recommendations:
        state["error"] = None
        return state

    state["intent"] = INTENT_MISSING_ANALYSIS
    state["intent_debug"] = {"classifier": "system", "reason": "missing_analysis"}
    state["category"] = state.get("target_type") or CATEGORY_HAIR
    state["needs_clarification"] = False
    state["answer"] = MISSING_ANALYSIS_MESSAGE
    state["error"] = "missing_analysis"
    state["retrieval_result"] = RetrievalResult(
        query=state.get("user_message", ""),
        documents=[],
        retrieved_count=0,
        fallback_stage=None,
        used_filter={},
    )
    state["retrieval_info"] = {
        "retrieved_count": 0,
        "fallback_stage": "none",
        "intent_debug": state.get("intent_debug"),
    }

    return state


def ask_clarification(state: ChatbotState) -> ChatbotState:
    """
    질문 의도가 불명확할 때 객관식 재질문을 반환한다.
    """

    state["answer"] = build_clarification_message()
    state["retrieval_result"] = RetrievalResult(
        query=state.get("user_message", ""),
        documents=[],
        retrieved_count=0,
        fallback_stage=None,
        used_filter={},
    )
    state["retrieval_info"] = {
        "retrieved_count": 0,
        "fallback_stage": "none",
        "used_filter": {},
        "skipped_rag": True,
        "skip_reason": state.get("intent"),
        "intent_debug": state.get("intent_debug"),
    }

    return state


def ask_mood_selection(state: ChatbotState) -> ChatbotState:
    """
    추천받은 스타일을 어떤 분위기로 가져갈지 선택 UI를 반환한다.
    """

    state["answer"] = build_mood_selection_title()
    state["pending_selection"] = PENDING_SELECTION_MOOD
    state["selected_mood"] = None
    state["selected_mood_id"] = None
    state["selected_mood_keywords"] = []
    state["selection"] = {
        "type": PENDING_SELECTION_MOOD,
        "title": "원하는 분위기를 선택해 주세요.",
        "options": [
            {
                "id": option["id"],
                "label": option["label"],
                "value": option["label"],
            }
            for option in MOOD_OPTIONS
        ],
    }
    state["retrieval_result"] = RetrievalResult(
        query=state.get("user_message", ""),
        documents=[],
        retrieved_count=0,
        fallback_stage=None,
        used_filter={},
    )
    state["retrieval_info"] = {
        "category": state.get("category") or state.get("target_type") or CATEGORY_HAIR,
        "target_type": state.get("target_type"),
        "applied_style_key": state.get("applied_style_key"),
        "retrieved_count": 0,
        "fallback_stage": "none",
        "used_filter": {},
        "skipped_rag": True,
        "skip_reason": state.get("intent"),
        "pending_selection": PENDING_SELECTION_MOOD,
        "intent_debug": state.get("intent_debug"),
    }

    return state


def generate_non_rag_answer(state: ChatbotState) -> ChatbotState:
    """
    LLM/RAG를 우회하는 intent에 대해 bypass_gate의 고정 응답을 반환한다.
    """

    intent = state.get("intent")
    answer = get_bypass_response(intent)

    if answer is None:
        answer = build_clarification_message()
        state["needs_clarification"] = True
        state["clarification_options"] = CLARIFICATION_OPTIONS

    state["answer"] = answer
    state["retrieval_result"] = RetrievalResult(
        query=state.get("user_message", ""),
        documents=[],
        retrieved_count=0,
        fallback_stage=None,
        used_filter={},
    )
    state["retrieval_info"] = {
        "retrieved_count": 0,
        "fallback_stage": "none",
        "used_filter": {},
        "skipped_rag": True,
        "skip_reason": intent,
        "intent_debug": state.get("intent_debug"),
    }

    return state


def _normalize_target_type(target_type: str | None) -> str | None:
    if target_type in {CATEGORY_HAIR, CATEGORY_MAKEUP}:
        return target_type
    return None


def _find_recommended_style_by_key(
    applied_style_key: str | None,
    previous_recommendations: list[dict[str, Any]],
    category: str | None = None,
) -> dict[str, str] | None:
    """
    DB/API에서 전달된 applied_style_key로 이전 추천 스타일을 찾는다.
    """

    if not applied_style_key:
        return None

    for recommendation in previous_recommendations:
        if category and recommendation.get("category") not in {category, None}:
            continue

        candidate_keys = {
            recommendation.get("style_code"),
            recommendation.get("style_key"),
            recommendation.get("applied_style_key"),
            recommendation.get("style_name"),
        }

        if applied_style_key not in {str(key) for key in candidate_keys if key}:
            continue

        style_name = recommendation.get("style_name")
        style_code = recommendation.get("style_code") or recommendation.get("style_key")

        if not style_name and not style_code:
            continue

        return {
            "style_name": str(style_name or ""),
            "style_code": str(style_code or applied_style_key),
            "makeup_group": recommendation.get("makeup_group"),
        }

    return None


def _find_style_code_from_message(
    user_message: str,
    previous_recommendations: list[dict[str, Any]],
    category: str | None = None,
) -> str | None:
    """
    사용자 질문에 이전 추천 스타일명이 포함되어 있으면 해당 style_code를 찾는다.
    """

    for recommendation in previous_recommendations:
        if category and recommendation.get("category") not in {category, None}:
            continue

        style_name = recommendation.get("style_name")
        style_code = recommendation.get("style_code")

        if not style_name or not style_code:
            continue

        if style_name in user_message:
            return str(style_code)

    return None


def _is_recommended_style(
    detected_style: dict[str, str] | None,
    previous_recommendations: list[dict[str, Any]],
    category: str | None = None,
) -> bool:
    """
    감지된 스타일이 이전 추천 목록에 포함되어 있는지 확인한다.
    """

    if not detected_style:
        return False

    detected_style_code = detected_style.get("style_code")
    detected_style_name = detected_style.get("style_name")

    for recommendation in previous_recommendations:
        if category and recommendation.get("category") not in {category, None}:
            continue

        if detected_style_code and recommendation.get("style_code") == detected_style_code:
            return True

        if detected_style_name and recommendation.get("style_name") == detected_style_name:
            return True

    return False


def classify_intent(state: ChatbotState) -> ChatbotState:
    """
    추천 결과에 대한 사용자 피드백 질문의 의도를 분류한다.
    """

    if state.get("error") == "missing_analysis":
        return state

    user_message = state.get("user_message", "")
    gender = state.get("gender")
    personal_color = state.get("personal_color")
    previous_recommendations = state.get("previous_recommendations") or []
    applied_style_key = state.get("applied_style_key")
    selected_option = state.get("selected_option")
    user_profile = state.get("user_profile") or {}

    target_type = _normalize_target_type(state.get("target_type"))
    category = target_type or detect_question_category(user_message)

    pending_selection = state.get("pending_selection") or user_profile.get("pending_selection")
    if pending_selection == PENDING_SELECTION_MOOD and selected_option:
        selected_option_type = selected_option.get("type")
        selected_option_id = selected_option.get("id")

        if selected_option_type == PENDING_SELECTION_MOOD:
            mood_option = get_mood_option_by_id(selected_option_id)

            if mood_option:
                state["intent"] = INTENT_MOOD_CHOICE
                state["intent_debug"] = {
                    "classifier": "selection",
                    "selected_option_id": selected_option_id,
                }
                state["category"] = category
                state["selected_mood_id"] = mood_option["id"]
                state["selected_mood"] = mood_option["label"]
                state["selected_mood_keywords"] = mood_option["mood_keywords"]
                state["pending_selection"] = None
                state["needs_clarification"] = False
                state["clarification_options"] = []
                state["selection"] = None
                return state

    intent, intent_debug = get_intent(user_message)
    state["intent_debug"] = intent_debug

    detected_style = _find_recommended_style_by_key(
        applied_style_key=applied_style_key,
        previous_recommendations=previous_recommendations,
        category=category,
    )

    if not detected_style:
        detected_hair_style = find_hair_style_in_message(
            message=user_message,
            gender=gender,
        )
        detected_makeup_style = find_makeup_style_in_message(
            message=user_message,
            personal_color=personal_color,
            gender=gender,
        )

        if category == CATEGORY_MAKEUP:
            detected_style = detected_makeup_style
        elif category == CATEGORY_HAIR:
            detected_style = detected_hair_style
        elif detected_makeup_style:
            category = CATEGORY_MAKEUP
            detected_style = detected_makeup_style
        elif detected_hair_style:
            category = CATEGORY_HAIR
            detected_style = detected_hair_style
        else:
            detected_style = None

    detected_style_is_recommended = _is_recommended_style(
        detected_style=detected_style,
        previous_recommendations=previous_recommendations,
        category=category,
    )

    if detected_style and applied_style_key:
        detected_style_is_recommended = True

    if detected_style and intent in {
        INTENT_UNCLEAR,
        INTENT_GREETING,
        INTENT_SMALLTALK,
        INTENT_IRRELEVANT,
        INTENT_NOISE,
    }:
        intent = INTENT_GENERAL_FOLLOWUP

    state["intent"] = intent
    state["category"] = category
    state["detected_style"] = detected_style
    state["detected_style_is_recommended"] = detected_style_is_recommended

    if intent == INTENT_UNCLEAR:
        state["needs_clarification"] = True
        state["clarification_options"] = CLARIFICATION_OPTIONS
    else:
        state["needs_clarification"] = False
        state["clarification_options"] = []

    return state


def retrieve_context(state: ChatbotState) -> ChatbotState:
    """
    추천 결과 피드백 질문과 사용자 진단 정보를 바탕으로 ChromaDB에서 문서를 검색한다.
    """

    if state.get("error") == "missing_analysis":
        return state

    if state.get("needs_clarification"):
        return state

    user_message = state.get("user_message", "")
    category = state.get("category") or CATEGORY_HAIR
    gender = state.get("gender")
    face_shape = state.get("face_shape")
    face_proportion = state.get("face_proportion")
    personal_color = state.get("personal_color")
    previous_recommendations = state.get("previous_recommendations") or []
    detected_style = state.get("detected_style")
    applied_style_key = state.get("applied_style_key")
    selected_mood = state.get("selected_mood")
    selected_mood_keywords = state.get("selected_mood_keywords") or []

    if detected_style:
        style_code = detected_style.get("style_code")
    elif applied_style_key:
        style_code = applied_style_key
    else:
        style_code = _find_style_code_from_message(
            user_message=user_message,
            previous_recommendations=previous_recommendations,
            category=category,
        )

    detected_style_name = ""
    makeup_group = None
    if detected_style:
        detected_style_name = detected_style.get("style_name", "")
        makeup_group = detected_style.get("makeup_group")

    mood_text = " ".join(selected_mood_keywords)

    if category == CATEGORY_MAKEUP:
        query = (
            f"{gender or ''} {personal_color or ''} 퍼스널컬러 "
            f"{detected_style_name} "
            f"{selected_mood or ''} "
            f"{mood_text} "
            f"{user_message}"
        ).strip()
        retrieve_kwargs = {
            "query": query,
            "category": CATEGORY_MAKEUP,
            "gender": gender,
            "personal_color": personal_color,
            "makeup_group": makeup_group,
            "style_code": style_code,
            "k": 3,
        }
    else:
        query = (
            f"{gender or ''} {face_shape or ''} 얼굴형 "
            f"{face_proportion or ''} 삼정 비율 "
            f"{detected_style_name} "
            f"{selected_mood or ''} "
            f"{mood_text} "
            f"{user_message}"
        ).strip()

        retrieve_kwargs = {
            "query": query,
            "category": CATEGORY_HAIR,
            "gender": gender,
            "face_shape": face_shape,
            "face_proportion": face_proportion,
            "style_code": style_code,
            "k": 3,
        }

    try:
        retrieval_result = retrieve_docs(**retrieve_kwargs)

        state["retrieval_result"] = retrieval_result
        state["retrieval_info"] = {
            "category": category,
            "target_type": state.get("target_type"),
            "applied_style_key": applied_style_key,
            "selected_mood_id": state.get("selected_mood_id"),
            "selected_mood": selected_mood,
            "retrieved_count": retrieval_result.retrieved_count,
            "fallback_stage": retrieval_result.fallback_stage
            if retrieval_result.fallback_stage is not None
            else "none",
            "used_filter": retrieval_result.used_filter,
            "intent_debug": state.get("intent_debug"),
        }

    except Exception as exc:
        state["retrieval_result"] = RetrievalResult(
            query=query,
            documents=[],
            retrieved_count=0,
            fallback_stage=None,
            used_filter={},
        )
        state["retrieval_info"] = {
            "category": category,
            "target_type": state.get("target_type"),
            "applied_style_key": applied_style_key,
            "selected_mood_id": state.get("selected_mood_id"),
            "selected_mood": selected_mood,
            "retrieved_count": 0,
            "fallback_stage": "none",
            "intent_debug": state.get("intent_debug"),
        }
        state["error"] = f"retrieval_failed: {exc}"

    return state


def generate_answer_node(state: ChatbotState) -> ChatbotState:
    """
    ChatGenerationInput을 구성하고 generate_chat_answer()로 최종 답변을 생성한다.
    """

    if state.get("error") == "missing_analysis":
        return state

    if state.get("needs_clarification"):
        return state

    retrieval_result = state.get("retrieval_result")

    if retrieval_result is None:
        retrieval_result = RetrievalResult(
            query=state.get("user_message", ""),
            documents=[],
            retrieved_count=0,
            fallback_stage=None,
            used_filter={},
        )

    user_profile = dict(state.get("user_profile") or {})

    if state.get("target_type"):
        user_profile["target_type"] = state.get("target_type")

    if state.get("applied_style_key"):
        user_profile["applied_style_key"] = state.get("applied_style_key")

    if state.get("selected_mood"):
        user_profile["selected_mood"] = state.get("selected_mood")
        user_profile["selected_mood_id"] = state.get("selected_mood_id")
        user_profile["selected_mood_keywords"] = state.get("selected_mood_keywords", [])

    generation_input = ChatGenerationInput(
        user_message=state.get("user_message", ""),
        gender=state.get("gender", ""),
        face_shape=state.get("face_shape", ""),
        face_proportion=state.get("face_proportion", ""),
        personal_color=state.get("personal_color"),
        previous_analysis=state.get("previous_analysis"),
        previous_recommendations=state.get("previous_recommendations") or [],
        user_profile=user_profile,
        chat_history=state.get("chat_history") or [],
        retrieval_result=retrieval_result,
        intent=state.get("intent"),
        category=state.get("category"),
        detected_style=state.get("detected_style"),
        detected_style_is_recommended=state.get(
            "detected_style_is_recommended",
            False,
        ),
    )

    generation_result = generate_chat_answer(generation_input)

    state["answer"] = generation_result.answer
    state["retrieval_result"] = generation_result.retrieval_result
    state["retrieval_info"] = {
        "category": state.get("category"),
        "target_type": state.get("target_type"),
        "applied_style_key": state.get("applied_style_key"),
        "selected_mood_id": state.get("selected_mood_id"),
        "selected_mood": state.get("selected_mood"),
        "retrieved_count": generation_result.retrieval_result.retrieved_count,
        "fallback_stage": generation_result.retrieval_result.fallback_stage
        if generation_result.retrieval_result.fallback_stage is not None
        else "none",
        "used_filter": generation_result.retrieval_result.used_filter,
        "model_name": generation_result.model_name,
        "intent_debug": state.get("intent_debug"),
    }

    return state


def update_memory(state: ChatbotState) -> ChatbotState:
    """
    답변 생성 후 chat_history와 user_profile을 업데이트한다.
    """

    user_message = state.get("user_message", "")
    answer = state.get("answer", "")

    updated_chat_history = append_chat_history(
        chat_history=state.get("chat_history") or [],
        user_message=user_message,
        assistant_answer=answer,
    )

    new_preferences = extract_simple_user_preferences(user_message)

    if state.get("pending_selection"):
        new_preferences["pending_selection"] = state.get("pending_selection")

    if state.get("selected_mood"):
        new_preferences["selected_mood"] = state.get("selected_mood")
        new_preferences["selected_mood_id"] = state.get("selected_mood_id")
        new_preferences["selected_mood_keywords"] = state.get(
            "selected_mood_keywords",
            [],
        )
        new_preferences["pending_selection"] = None

    updated_user_profile = merge_user_profile(
        user_profile=state.get("user_profile") or {},
        new_preferences=new_preferences,
    )

    state["updated_chat_history"] = updated_chat_history
    state["updated_user_profile"] = updated_user_profile

    return state
