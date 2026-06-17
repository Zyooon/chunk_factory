from __future__ import annotations

import os
from typing import Any

from apps.chatbot_rag.bypass_gate import get_bypass_response
from apps.chatbot_rag.intent_classifier import get_intent
from apps.chatbot_rag.intent_keywords import (
    _extract_outfit_context_from_message,
    detect_question_category,
)
from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_GENERAL_FOLLOWUP,
    INTENT_GREETING,
    INTENT_IRRELEVANT,
    INTENT_MISSING_ANALYSIS,
    INTENT_MOOD_CHOICE,
    INTENT_NOISE,
    INTENT_OUTFIT_EVENT_COORDINATION,
    INTENT_OUTFIT_FIT_CHECK,
    INTENT_OUTFIT_RECOMMENDATION,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR,
    OUTFIT_INTENTS,
    PENDING_OUTFIT_CONTEXT,
    PENDING_OUTFIT_OPTION_SELECTION,
    PENDING_OUTFIT_SYNTHESIS_CONFIRMATION,
    PENDING_OUTFIT_USER_IMAGE_REQUIRED,
    PENDING_SELECTION_MOOD,
)
from apps.chatbot_rag.memory import (
    append_chat_history,
    extract_simple_user_preferences,
    merge_user_profile,
)
from apps.chatbot_rag.makeup_catalog import find_makeup_style_in_message
from apps.chatbot_rag.outfit_prompts import build_outfit_coordination_prompt, parse_outfit_response
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
from apps.rag_core.generator import (
    generate_chat_answer,
    get_chat_model,
    invoke_with_retry,
    normalize_model_content,
)
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


def handle_mood_pending(state: ChatbotState) -> ChatbotState:
    """
    mood 선택 버튼 응답을 처리한다. (classify_intent에서 분리)
    """
    user_message = state.get("user_message", "")
    selected_option = state.get("selected_option") or {}
    user_profile = state.get("user_profile") or {}

    target_type = _normalize_target_type(state.get("target_type"))
    category = target_type or detect_question_category(user_message)

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

    # 선택값 불일치 시 일반 메시지로 fallback — intent를 비워 classify_intent로 재분류
    state["intent"] = None
    state["pending_selection"] = None
    return state


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

    target_type = _normalize_target_type(state.get("target_type"))
    category = target_type or detect_question_category(user_message)

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

    # 이미지 분석 결과가 있으면 query 구성 요소를 보강한다.
    image_analysis = state.get("image_analysis")
    image_visual_features: list[str] = state.get("image_visual_features") or []
    rag_query_text = ""
    if image_analysis:
        if not style_code:
            candidates = image_analysis.get("style_code_candidates") or []
            if candidates:
                style_code = candidates[0]
        if not detected_style_name:
            detected_style_name = image_analysis.get("detected_style_name") or ""
        rag_query_text = image_analysis.get("rag_query_text") or ""

    image_features_text = " ".join(image_visual_features)

    mood_text = " ".join(selected_mood_keywords)

    if category == CATEGORY_MAKEUP:
        query = (
            f"{gender or ''} {personal_color or ''} 퍼스널컬러 "
            f"{detected_style_name} "
            f"{selected_mood or ''} "
            f"{mood_text} "
            f"{rag_query_text} "
            f"{image_features_text} "
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
            f"{rag_query_text} "
            f"{image_features_text} "
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

    # pending_selection: None이면 user_profile에서도 제거
    new_preferences["pending_selection"] = state.get("pending_selection")

    if state.get("selected_mood"):
        new_preferences["selected_mood"] = state.get("selected_mood")
        new_preferences["selected_mood_id"] = state.get("selected_mood_id")
        new_preferences["selected_mood_keywords"] = state.get("selected_mood_keywords", [])
        new_preferences["pending_selection"] = None

    # outfit 관련 필드 보존
    if state.get("outfit_intent"):
        new_preferences["outfit_intent"] = state.get("outfit_intent")
    if state.get("outfit_context"):
        new_preferences["outfit_context"] = state.get("outfit_context")
    if state.get("outfit_options"):
        new_preferences["outfit_options"] = state.get("outfit_options")
    if state.get("selected_outfit_option"):
        new_preferences["selected_outfit_option"] = state.get("selected_outfit_option")
    # pending_outfit_synthesis: 명시적으로 None이 되면 제거, 값이 있으면 저장
    pending_synthesis = state.get("pending_outfit_synthesis")
    if "pending_outfit_synthesis" in state:
        new_preferences["pending_outfit_synthesis"] = pending_synthesis

    updated_user_profile = merge_user_profile(
        user_profile=state.get("user_profile") or {},
        new_preferences=new_preferences,
    )

    state["updated_chat_history"] = updated_chat_history
    state["updated_user_profile"] = updated_user_profile

    return state


# ---------------------------------------------------------------------------
# pending_selection 라우터 노드
# ---------------------------------------------------------------------------

def resolve_pending_selection(state: ChatbotState) -> ChatbotState:
    """
    user_profile에 저장된 pending_selection과 outfit 관련 필드를
    state로 복원한다.
    """
    user_profile = state.get("user_profile") or {}

    if not state.get("pending_selection"):
        pending = user_profile.get("pending_selection")
        if pending:
            state["pending_selection"] = pending

    if not state.get("outfit_options"):
        outfit_options = user_profile.get("outfit_options")
        if outfit_options:
            state["outfit_options"] = outfit_options

    if not state.get("pending_outfit_synthesis"):
        pending_synthesis = user_profile.get("pending_outfit_synthesis")
        if pending_synthesis:
            state["pending_outfit_synthesis"] = pending_synthesis

    if not state.get("outfit_intent"):
        outfit_intent = user_profile.get("outfit_intent")
        if outfit_intent:
            state["outfit_intent"] = outfit_intent

    if not state.get("outfit_context"):
        outfit_context = user_profile.get("outfit_context")
        if outfit_context:
            state["outfit_context"] = outfit_context

    return state


# ---------------------------------------------------------------------------
# outfit 전제조건 확인
# ---------------------------------------------------------------------------

def check_hair_makeup_ready(state: ChatbotState) -> ChatbotState:
    """헤어/메이크업 추천이 모두 완료됐는지 확인한다."""
    previous_recommendations = state.get("previous_recommendations") or []

    has_hair = any(r.get("category") == CATEGORY_HAIR for r in previous_recommendations)
    has_makeup = any(r.get("category") == CATEGORY_MAKEUP for r in previous_recommendations)

    if not (has_hair and has_makeup):
        state["outfit_prerequisites_met"] = False
        state["answer"] = (
            "아직 헤어와 메이크업 추천 결과가 없어 의상 추천을 진행하기 어려워요.\n"
            "먼저 헤어와 메이크업 분석을 완료한 뒤 의상 추천을 도와드릴게요."
        )
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
            "skip_reason": "outfit_prerequisites_not_met",
        }
        return state

    state["outfit_prerequisites_met"] = True
    intent = state.get("intent")
    state["outfit_intent"] = intent

    # outfit_event_coordination: 메시지에서 상황 추출
    if intent == INTENT_OUTFIT_EVENT_COORDINATION and not state.get("outfit_context"):
        extracted = _extract_outfit_context_from_message(state.get("user_message", ""))
        state["outfit_context"] = extracted

    return state


# ---------------------------------------------------------------------------
# outfit 이미지 분석
# ---------------------------------------------------------------------------

def analyze_outfit_image(state: ChatbotState) -> ChatbotState:
    """
    의상 이미지를 vision LLM으로 분석한다. 현재는 stub.
    """
    image_url = state.get("image_url")
    if not image_url:
        return state

    # TODO: Gemini Vision API로 의상 이미지 분석 연동
    state["outfit_image_analysis"] = {
        "outfit_type": "",
        "colors": [],
        "silhouette": "",
        "formality": "",
        "style_mood": [],
        "match_points": [],
        "risk_points": [],
        "confidence": "low",
    }
    return state


# ---------------------------------------------------------------------------
# outfit 상황 선택 요청
# ---------------------------------------------------------------------------

_OUTFIT_CONTEXT_OPTIONS = [
    {"id": "daily", "label": "데일리룩"},
    {"id": "date", "label": "데이트룩"},
    {"id": "wedding_guest", "label": "결혼식 하객룩"},
    {"id": "office", "label": "출근/면접룩"},
    {"id": "formal", "label": "격식 있는 자리"},
    {"id": "casual", "label": "꾸안꾸 캐주얼"},
]


def ask_outfit_context_selection(state: ChatbotState) -> ChatbotState:
    """상황이 없는 일반 의상 추천 질문에서 상황 선택 버튼을 제시한다."""
    state["outfit_intent"] = INTENT_OUTFIT_RECOMMENDATION
    state["answer"] = "어떤 상황에 맞춰 추천해드릴까요?"
    state["pending_selection"] = PENDING_OUTFIT_CONTEXT
    state["selection"] = {
        "type": PENDING_OUTFIT_CONTEXT,
        "options": _OUTFIT_CONTEXT_OPTIONS,
    }
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
        "skip_reason": "pending_outfit_context",
    }
    return state


# ---------------------------------------------------------------------------
# outfit 상황 선택 완료 처리
# ---------------------------------------------------------------------------

def handle_outfit_context_pending(state: ChatbotState) -> ChatbotState:
    """상황 선택 결과를 outfit_context에 저장한다."""
    selected_option = state.get("selected_option") or {}
    outfit_context = selected_option.get("id")

    state["outfit_context"] = outfit_context
    state["outfit_intent"] = INTENT_OUTFIT_RECOMMENDATION
    state["intent"] = INTENT_OUTFIT_RECOMMENDATION
    state["pending_selection"] = None
    state["selection"] = None
    state["outfit_prerequisites_met"] = True

    return state


# ---------------------------------------------------------------------------
# outfit 답변 생성 (RAG 없이 LLM coordination prompt)
# ---------------------------------------------------------------------------

def generate_outfit_answer(state: ChatbotState) -> ChatbotState:
    """LLM coordination prompt로 의상 추천/판단 답변을 생성한다."""
    previous_recommendations = state.get("previous_recommendations") or []
    hair_recs = [r for r in previous_recommendations if r.get("category") == CATEGORY_HAIR]
    makeup_recs = [r for r in previous_recommendations if r.get("category") == CATEGORY_MAKEUP]

    hair_summary = hair_recs[0] if hair_recs else {}
    makeup_summary = makeup_recs[0] if makeup_recs else {}

    outfit_intent = state.get("outfit_intent") or state.get("intent")

    prompt = build_outfit_coordination_prompt(
        gender=state.get("gender"),
        face_shape=state.get("face_shape"),
        face_proportion=state.get("face_proportion"),
        personal_color=state.get("personal_color"),
        hair_summary=hair_summary,
        makeup_summary=makeup_summary,
        outfit_context=state.get("outfit_context"),
        outfit_image_analysis=state.get("outfit_image_analysis"),
        outfit_intent=outfit_intent,
        user_message=state.get("user_message", ""),
        previous_analysis=state.get("previous_analysis"),
    )

    if os.getenv("RAG_GENERATOR_MODE", "gemini") == "mock":
        answer = "현재는 개발용 mock 의상 추천 응답입니다."
        outfit_options: list[dict] = [
            {"id": "look_1", "label": "모크 룩 1", "description": "개발용 의상 후보", "colors": [], "items": [], "avoid": []},
            {"id": "look_2", "label": "모크 룩 2", "description": "개발용 의상 후보", "colors": [], "items": [], "avoid": []},
        ]
        if outfit_intent == INTENT_OUTFIT_FIT_CHECK:
            outfit_options = [{"id": "uploaded_outfit", "label": "업로드한 의상", "source": "image"}]
    else:
        chat_model = get_chat_model()
        response = invoke_with_retry(chat_model, prompt)
        content = normalize_model_content(getattr(response, "content", response))
        answer, outfit_options = parse_outfit_response(content, outfit_intent)

    state["outfit_options"] = outfit_options
    state["outfit_intent"] = outfit_intent

    if outfit_intent == INTENT_OUTFIT_FIT_CHECK:
        synthesis_offer = "이 의상을 고객님 사진에 맞춰 합성해서 보여드릴까요?"
    else:
        synthesis_offer = "추천드린 의상 중 하나를 고객님 사진에 합성해서 보여드릴까요?"

    state["answer"] = f"{answer}\n\n{synthesis_offer}"
    state["pending_selection"] = PENDING_OUTFIT_SYNTHESIS_CONFIRMATION
    state["selection"] = {
        "type": PENDING_OUTFIT_SYNTHESIS_CONFIRMATION,
        "options": [
            {"id": "confirm_outfit_synthesis", "label": "합성 진행하기"},
            {"id": "cancel_outfit_synthesis", "label": "취소하기"},
        ],
    }

    user_profile = state.get("user_profile") or {}
    state["pending_outfit_synthesis"] = {
        "question_type": outfit_intent,
        "outfit_context": state.get("outfit_context"),
        "user_image_url": user_profile.get("user_image_url"),
        "outfit_image_url": state.get("image_url") if outfit_intent == INTENT_OUTFIT_FIT_CHECK else None,
        "selected_outfit_option": None,
        "outfit_options": outfit_options,
        "hair_summary": hair_summary,
        "makeup_summary": makeup_summary,
        "user_profile": {
            "gender": state.get("gender"),
            "face_shape": state.get("face_shape"),
            "face_proportion": state.get("face_proportion"),
            "personal_color": state.get("personal_color"),
        },
        "original_user_message": state.get("user_message", ""),
    }

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
        "skip_reason": outfit_intent,
    }

    return state


# ---------------------------------------------------------------------------
# 합성 확인 버튼 처리
# ---------------------------------------------------------------------------

def handle_synthesis_confirmation(state: ChatbotState) -> ChatbotState:
    """합성 진행하기 / 취소하기 선택을 처리한다."""
    selected_option = state.get("selected_option") or {}
    selected_id = selected_option.get("id")

    if selected_id == "cancel_outfit_synthesis":
        state["outfit_synthesis_action"] = "cancel"
        state["pending_outfit_synthesis"] = None
        state["pending_selection"] = None
        state["selection"] = None
        state["outfit_options"] = []
        state["answer"] = "의상 합성을 취소했습니다. 다른 궁금한 점이 있으시면 언제든 말씀해 주세요."
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
            "skip_reason": "outfit_synthesis_cancelled",
        }
        return state

    # confirm 선택
    outfit_options = state.get("outfit_options") or (state.get("pending_outfit_synthesis") or {}).get("outfit_options") or []
    state["pending_selection"] = None
    state["selection"] = None

    if len(outfit_options) > 1:
        state["outfit_synthesis_action"] = "select_option"
    else:
        # 단일 의상이면 바로 선택 처리
        if outfit_options:
            single = outfit_options[0]
            state["selected_outfit_option"] = single
            pending_synthesis = dict(state.get("pending_outfit_synthesis") or {})
            pending_synthesis["selected_outfit_option"] = single
            state["pending_outfit_synthesis"] = pending_synthesis
        state["outfit_synthesis_action"] = "check_image"

    return state


# ---------------------------------------------------------------------------
# 의상 후보 선택 요청
# ---------------------------------------------------------------------------

def ask_outfit_option_selection(state: ChatbotState) -> ChatbotState:
    """추천된 의상 후보 중 합성할 룩을 선택하도록 요청한다."""
    outfit_options = state.get("outfit_options") or []

    state["answer"] = "어떤 룩으로 합성할까요?"
    state["pending_selection"] = PENDING_OUTFIT_OPTION_SELECTION
    state["selection"] = {
        "type": PENDING_OUTFIT_OPTION_SELECTION,
        "options": [{"id": opt["id"], "label": opt["label"]} for opt in outfit_options],
    }
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
        "skip_reason": "pending_outfit_option_selection",
    }
    return state


# ---------------------------------------------------------------------------
# 의상 후보 선택 완료 처리
# ---------------------------------------------------------------------------

def handle_outfit_option_pending(state: ChatbotState) -> ChatbotState:
    """선택된 의상 후보를 selected_outfit_option에 저장한다."""
    selected_option = state.get("selected_option") or {}
    selected_id = selected_option.get("id")

    outfit_options = (
        state.get("outfit_options")
        or (state.get("pending_outfit_synthesis") or {}).get("outfit_options")
        or []
    )
    selected = next((opt for opt in outfit_options if opt.get("id") == selected_id), None)

    state["selected_outfit_option"] = selected
    state["pending_selection"] = None
    state["selection"] = None

    if selected:
        pending_synthesis = dict(state.get("pending_outfit_synthesis") or {})
        pending_synthesis["selected_outfit_option"] = selected
        state["pending_outfit_synthesis"] = pending_synthesis

    return state


# ---------------------------------------------------------------------------
# 유저 사진 확인
# ---------------------------------------------------------------------------

def check_user_image_for_synthesis(state: ChatbotState) -> ChatbotState:
    """
    합성에 사용할 유저 사진 URL을 확인한다.
    헤어/메이크업 합성 완료 후 저장된 사진을 user_profile에서 가져온다.
    """
    user_profile = state.get("user_profile") or {}
    pending_synthesis = state.get("pending_outfit_synthesis") or {}

    user_image_url = (
        pending_synthesis.get("user_image_url")
        or user_profile.get("user_image_url")
        or user_profile.get("synthesized_image_url")
    )

    if user_image_url:
        pending_synthesis = dict(pending_synthesis)
        pending_synthesis["user_image_url"] = user_image_url
        state["pending_outfit_synthesis"] = pending_synthesis
        return state

    # 사진 없음
    state["answer"] = (
        "합성을 진행하려면 고객님 사진이 필요해요.\n"
        "현재 버전에서는 사진 업로드 후 합성 기능을 사용할 수 있어요.\n"
        "사진 업로드 기능이 연결되면 바로 합성을 진행할 수 있도록 준비해둘게요."
    )
    state["pending_selection"] = PENDING_OUTFIT_USER_IMAGE_REQUIRED
    state["selection"] = None
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
        "skip_reason": "outfit_user_image_required",
    }
    return state


# ---------------------------------------------------------------------------
# 유저 사진 대기 처리
# ---------------------------------------------------------------------------

def handle_outfit_user_image_pending(state: ChatbotState) -> ChatbotState:
    """사진 업로드 대기 상태에서 image_url이 들어오면 합성을 이어서 진행한다."""
    image_url = state.get("image_url")

    if image_url:
        pending_synthesis = dict(state.get("pending_outfit_synthesis") or {})
        pending_synthesis["user_image_url"] = image_url
        state["pending_outfit_synthesis"] = pending_synthesis
        state["pending_selection"] = None
        return state

    state["answer"] = (
        "합성을 진행하려면 고객님 사진이 필요해요.\n"
        "얼굴과 상반신이 잘 보이는 사진을 업로드해 주세요."
    )
    state["pending_selection"] = PENDING_OUTFIT_USER_IMAGE_REQUIRED
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
        "skip_reason": "outfit_user_image_required",
    }
    return state


# ---------------------------------------------------------------------------
# 의상 합성 실행
# ---------------------------------------------------------------------------

def run_outfit_synthesis(state: ChatbotState) -> ChatbotState:
    """
    의상 합성을 실행한다. 현재는 stub — 실제 합성 모듈 연동 시 교체한다.
    """
    pending_synthesis = state.get("pending_outfit_synthesis") or {}
    selected_outfit = pending_synthesis.get("selected_outfit_option") or {}
    outfit_label = selected_outfit.get("label", "선택한 의상")

    # TODO: 실제 이미지 합성 API 연동
    state["answer"] = (
        f"'{outfit_label}'으로 합성을 준비 중이에요. "
        "합성 기능은 추후 연결 예정입니다."
    )
    state["pending_selection"] = None
    state["selection"] = None
    state["pending_outfit_synthesis"] = None
    state["outfit_options"] = []
    state["selected_outfit_option"] = None
    state["outfit_synthesis_action"] = None
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
        "skip_reason": "outfit_synthesis",
    }
    return state
