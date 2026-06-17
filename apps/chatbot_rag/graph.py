from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.chatbot_rag.bypass_gate import should_bypass_llm
from apps.chatbot_rag.image_nodes import (
    IMAGE_INTENT_NONE,
    IMAGE_INTENT_SYNTHESIS,
    analyze_image_if_needed,
    classify_image_intent,
    handle_image_synthesis_request,
)
from apps.chatbot_rag.nodes import (
    analyze_outfit_image,
    ask_clarification,
    ask_mood_selection,
    ask_outfit_context_selection,
    ask_outfit_option_selection,
    check_analysis_exists,
    check_hair_makeup_ready,
    check_user_image_for_synthesis,
    classify_intent,
    generate_answer_node,
    generate_non_rag_answer,
    generate_outfit_answer,
    handle_mood_pending,
    handle_outfit_context_pending,
    handle_outfit_option_pending,
    handle_outfit_user_image_pending,
    handle_synthesis_confirmation,
    resolve_pending_selection,
    retrieve_context,
    run_outfit_synthesis,
    update_memory,
)
from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_MOOD_CHOICE,
    INTENT_MOOD_SELECTION,
    INTENT_OUTFIT_FIT_CHECK,
    INTENT_OUTFIT_RECOMMENDATION,
    OUTFIT_INTENTS,
    PENDING_OUTFIT_CONTEXT,
    PENDING_OUTFIT_OPTION_SELECTION,
    PENDING_OUTFIT_SYNTHESIS_CONFIRMATION,
    PENDING_OUTFIT_USER_IMAGE_REQUIRED,
    PENDING_SELECTION_MOOD,
)
from apps.chatbot_rag.state import ChatbotState


# ---------------------------------------------------------------------------
# 라우팅 함수
# ---------------------------------------------------------------------------

def route_after_analysis(state: ChatbotState) -> str:
    if state.get("error") == "missing_analysis":
        return "update_memory"
    return "resolve_pending_selection"


def _route_by_pending(state: ChatbotState) -> str:
    """pending_selection 값에 따라 적절한 핸들러로 분기한다."""
    pending = state.get("pending_selection")
    selected_option = state.get("selected_option")

    if pending == PENDING_SELECTION_MOOD and selected_option:
        return "handle_mood_pending"
    if pending == PENDING_OUTFIT_CONTEXT and selected_option:
        return "handle_outfit_context_pending"
    if pending == PENDING_OUTFIT_SYNTHESIS_CONFIRMATION and selected_option:
        return "handle_synthesis_confirmation"
    if pending == PENDING_OUTFIT_OPTION_SELECTION and selected_option:
        return "handle_outfit_option_pending"
    if pending == PENDING_OUTFIT_USER_IMAGE_REQUIRED:
        return "handle_outfit_user_image_pending"

    return "classify_image_intent"


def _route_after_mood_pending(state: ChatbotState) -> str:
    if state.get("intent") == INTENT_MOOD_CHOICE:
        return "retrieve_context"
    return "classify_intent"


def route_after_image_intent(state: ChatbotState) -> str:
    image_intent = state.get("image_intent", IMAGE_INTENT_NONE)

    if image_intent == IMAGE_INTENT_SYNTHESIS:
        return "handle_image_synthesis_request"

    if image_intent == IMAGE_INTENT_NONE:
        return "classify_intent"

    return "analyze_image_if_needed"


def route_after_intent(state: ChatbotState) -> str:
    intent = state.get("intent")

    if should_bypass_llm(intent):
        return "generate_non_rag_answer"

    if intent == INTENT_MOOD_SELECTION:
        return "ask_mood_selection"

    if intent in OUTFIT_INTENTS:
        if intent == INTENT_OUTFIT_RECOMMENDATION and not state.get("outfit_context"):
            return "ask_outfit_context_selection"
        return "check_hair_makeup_ready"

    if state.get("needs_clarification"):
        return "ask_clarification"

    return "retrieve_context"


def _route_after_hair_makeup_check(state: ChatbotState) -> str:
    if not state.get("outfit_prerequisites_met", True):
        return "update_memory"
    if state.get("image_url") and state.get("outfit_intent") == INTENT_OUTFIT_FIT_CHECK:
        return "analyze_outfit_image"
    return "generate_outfit_answer"


def _route_after_synthesis_confirmation(state: ChatbotState) -> str:
    action = state.get("outfit_synthesis_action")
    if action == "cancel":
        return "update_memory"
    if action == "select_option":
        return "ask_outfit_option_selection"
    return "check_user_image_for_synthesis"


def _route_after_image_check(state: ChatbotState) -> str:
    if state.get("pending_selection") == PENDING_OUTFIT_USER_IMAGE_REQUIRED:
        return "update_memory"
    return "run_outfit_synthesis"


def _route_after_user_image_pending(state: ChatbotState) -> str:
    if state.get("image_url"):
        return "run_outfit_synthesis"
    return "update_memory"


# ---------------------------------------------------------------------------
# Graph 빌더
# ---------------------------------------------------------------------------

def build_chatbot_graph():
    graph = StateGraph(ChatbotState)

    # 기존 노드
    graph.add_node("check_analysis_exists", check_analysis_exists)
    graph.add_node("resolve_pending_selection", resolve_pending_selection)
    graph.add_node("classify_image_intent", classify_image_intent)
    graph.add_node("analyze_image_if_needed", analyze_image_if_needed)
    graph.add_node("handle_image_synthesis_request", handle_image_synthesis_request)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("ask_mood_selection", ask_mood_selection)
    graph.add_node("generate_non_rag_answer", generate_non_rag_answer)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("update_memory", update_memory)

    # mood pending 핸들러
    graph.add_node("handle_mood_pending", handle_mood_pending)

    # outfit 신규 노드
    graph.add_node("check_hair_makeup_ready", check_hair_makeup_ready)
    graph.add_node("analyze_outfit_image", analyze_outfit_image)
    graph.add_node("ask_outfit_context_selection", ask_outfit_context_selection)
    graph.add_node("handle_outfit_context_pending", handle_outfit_context_pending)
    graph.add_node("generate_outfit_answer", generate_outfit_answer)
    graph.add_node("handle_synthesis_confirmation", handle_synthesis_confirmation)
    graph.add_node("ask_outfit_option_selection", ask_outfit_option_selection)
    graph.add_node("handle_outfit_option_pending", handle_outfit_option_pending)
    graph.add_node("check_user_image_for_synthesis", check_user_image_for_synthesis)
    graph.add_node("handle_outfit_user_image_pending", handle_outfit_user_image_pending)
    graph.add_node("run_outfit_synthesis", run_outfit_synthesis)

    # ── 엣지 ──────────────────────────────────────────────────────────────────

    graph.add_edge(START, "check_analysis_exists")

    graph.add_conditional_edges(
        "check_analysis_exists",
        route_after_analysis,
        {
            "resolve_pending_selection": "resolve_pending_selection",
            "update_memory": "update_memory",
        },
    )

    graph.add_conditional_edges(
        "resolve_pending_selection",
        _route_by_pending,
        {
            "handle_mood_pending": "handle_mood_pending",
            "handle_outfit_context_pending": "handle_outfit_context_pending",
            "handle_synthesis_confirmation": "handle_synthesis_confirmation",
            "handle_outfit_option_pending": "handle_outfit_option_pending",
            "handle_outfit_user_image_pending": "handle_outfit_user_image_pending",
            "classify_image_intent": "classify_image_intent",
        },
    )

    # mood pending 처리 후 분기
    graph.add_conditional_edges(
        "handle_mood_pending",
        _route_after_mood_pending,
        {
            "retrieve_context": "retrieve_context",
            "classify_intent": "classify_intent",
        },
    )

    # outfit 상황 선택 완료 → 의상 답변 생성
    graph.add_edge("handle_outfit_context_pending", "generate_outfit_answer")

    # 합성 확인 버튼 처리 후 분기
    graph.add_conditional_edges(
        "handle_synthesis_confirmation",
        _route_after_synthesis_confirmation,
        {
            "update_memory": "update_memory",
            "ask_outfit_option_selection": "ask_outfit_option_selection",
            "check_user_image_for_synthesis": "check_user_image_for_synthesis",
        },
    )

    # 의상 후보 선택 완료 → 유저 사진 확인
    graph.add_edge("handle_outfit_option_pending", "check_user_image_for_synthesis")

    # 유저 사진 확인 후 분기
    graph.add_conditional_edges(
        "check_user_image_for_synthesis",
        _route_after_image_check,
        {
            "update_memory": "update_memory",
            "run_outfit_synthesis": "run_outfit_synthesis",
        },
    )

    # 사진 업로드 대기 처리 후 분기
    graph.add_conditional_edges(
        "handle_outfit_user_image_pending",
        _route_after_user_image_pending,
        {
            "run_outfit_synthesis": "run_outfit_synthesis",
            "update_memory": "update_memory",
        },
    )

    # 기존 image intent 흐름
    graph.add_conditional_edges(
        "classify_image_intent",
        route_after_image_intent,
        {
            "handle_image_synthesis_request": "handle_image_synthesis_request",
            "analyze_image_if_needed": "analyze_image_if_needed",
            "classify_intent": "classify_intent",
        },
    )

    graph.add_edge("analyze_image_if_needed", "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "ask_clarification": "ask_clarification",
            "ask_mood_selection": "ask_mood_selection",
            "ask_outfit_context_selection": "ask_outfit_context_selection",
            "check_hair_makeup_ready": "check_hair_makeup_ready",
            "generate_non_rag_answer": "generate_non_rag_answer",
            "retrieve_context": "retrieve_context",
        },
    )

    # outfit 처리 경로
    graph.add_conditional_edges(
        "check_hair_makeup_ready",
        _route_after_hair_makeup_check,
        {
            "update_memory": "update_memory",
            "analyze_outfit_image": "analyze_outfit_image",
            "generate_outfit_answer": "generate_outfit_answer",
        },
    )

    graph.add_edge("analyze_outfit_image", "generate_outfit_answer")

    # update_memory로 수렴하는 엣지들
    graph.add_edge("handle_image_synthesis_request", "update_memory")
    graph.add_edge("ask_clarification", "update_memory")
    graph.add_edge("ask_mood_selection", "update_memory")
    graph.add_edge("ask_outfit_context_selection", "update_memory")
    graph.add_edge("ask_outfit_option_selection", "update_memory")
    graph.add_edge("generate_non_rag_answer", "update_memory")
    graph.add_edge("generate_outfit_answer", "update_memory")
    graph.add_edge("run_outfit_synthesis", "update_memory")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", "update_memory")
    graph.add_edge("update_memory", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# 외부 진입점
# ---------------------------------------------------------------------------

def run_chatbot(
    *,
    user_message: str | None = None,
    feedback_text: str | None = None,
    image_url: str | None = None,
    target_type: str | None = None,
    applied_style_key: str | None = None,
    selected_option: dict[str, Any] | None = None,
    gender: str,
    face_shape: str,
    face_proportion: str,
    personal_color: str | None = None,
    previous_analysis: str | dict[str, Any] | None = None,
    previous_recommendations: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    graph = build_chatbot_graph()

    normalized_target_type = target_type
    if normalized_target_type not in {CATEGORY_HAIR, CATEGORY_MAKEUP, None}:
        normalized_target_type = None

    message = feedback_text if feedback_text is not None else user_message

    initial_state: ChatbotState = {
        "user_message": message or "",
        "image_url": image_url,
        "target_type": normalized_target_type,
        "applied_style_key": applied_style_key,
        "selected_option": selected_option,
        "gender": gender,
        "face_shape": face_shape,
        "face_proportion": face_proportion,
        "personal_color": personal_color or "",
        "previous_analysis": previous_analysis,
        "previous_recommendations": previous_recommendations or [],
        "user_profile": user_profile or {},
        "chat_history": chat_history or [],
    }

    result = graph.invoke(initial_state)

    return {
        "answer": result.get("answer", ""),
        "intent": result.get("intent"),
        "category": result.get("category"),
        "target_type": result.get("target_type"),
        "applied_style_key": result.get("applied_style_key"),
        "selection": result.get("selection"),
        "pending_selection": result.get("pending_selection"),
        "selected_mood_id": result.get("selected_mood_id"),
        "selected_mood": result.get("selected_mood"),
        "selected_mood_keywords": result.get("selected_mood_keywords", []),
        "needs_clarification": result.get("needs_clarification", False),
        "clarification_options": result.get("clarification_options", []),
        "detected_style": result.get("detected_style"),
        "detected_style_is_recommended": result.get("detected_style_is_recommended", False),
        # outfit 관련
        "outfit_intent": result.get("outfit_intent"),
        "outfit_context": result.get("outfit_context"),
        "outfit_options": result.get("outfit_options", []),
        "selected_outfit_option": result.get("selected_outfit_option"),
        "pending_outfit_synthesis": result.get("pending_outfit_synthesis"),
        # retrieval / memory
        "retrieval_info": result.get(
            "retrieval_info",
            {"retrieved_count": 0, "fallback_stage": "none"},
        ),
        "updated_chat_history": result.get("updated_chat_history", []),
        "updated_user_profile": result.get("updated_user_profile", {}),
        "error": result.get("error"),
        # image
        "image_intent": result.get("image_intent"),
        "image_intent_debug": result.get("image_intent_debug"),
        "image_is_synthesis_request": result.get("image_is_synthesis_request", False),
        "image_analysis": result.get("image_analysis"),
        "image_visual_features": result.get("image_visual_features", []),
        "image_detected_style": result.get("image_detected_style"),
    }
