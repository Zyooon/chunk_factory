from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.chatbot_rag.bypass_gate import should_bypass_llm
from apps.chatbot_rag.nodes import (
    ask_clarification,
    ask_mood_selection,
    check_analysis_exists,
    classify_intent,
    generate_answer_node,
    generate_non_rag_answer,
    retrieve_context,
    update_memory,
)

from apps.chatbot_rag.intents import (
    CATEGORY_HAIR,
    CATEGORY_MAKEUP,
    INTENT_MOOD_SELECTION,
)

from apps.chatbot_rag.state import ChatbotState


def route_after_analysis(state: ChatbotState) -> str:
    """
    분석 결과 존재 여부 확인 후 다음 노드를 결정한다.

    missing_analysis 상태이면 검색/생성을 하지 않고 update_memory로 이동한다.
    """

    if state.get("error") == "missing_analysis":
        return "update_memory"

    return "classify_intent"


def route_after_intent(state: ChatbotState) -> str:
    """
    intent 분류 후 다음 노드를 결정한다.

    - bypass intent는 고정 응답으로 보낸다.
    - mood_selection은 선택 UI를 반환한다.
    - unclear는 객관식 재질문으로 보낸다.
    - 나머지 피드백 상담 intent는 RAG 검색으로 보낸다.
    """

    intent = state.get("intent")

    if should_bypass_llm(intent):
        return "generate_non_rag_answer"

    if intent == INTENT_MOOD_SELECTION:
        return "ask_mood_selection"

    if state.get("needs_clarification"):
        return "ask_clarification"

    return "retrieve_context"


def build_chatbot_graph():
    """
    chatbot_rag LangGraph를 생성한다.
    """

    graph = StateGraph(ChatbotState)

    graph.add_node("check_analysis_exists", check_analysis_exists)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("ask_mood_selection", ask_mood_selection)
    graph.add_node("generate_non_rag_answer", generate_non_rag_answer)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("update_memory", update_memory)

    graph.add_edge(START, "check_analysis_exists")

    graph.add_conditional_edges(
        "check_analysis_exists",
        route_after_analysis,
        {
            "classify_intent": "classify_intent",
            "update_memory": "update_memory",
        },
    )

    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "ask_clarification": "ask_clarification",
            "ask_mood_selection": "ask_mood_selection",
            "generate_non_rag_answer": "generate_non_rag_answer",
            "retrieve_context": "retrieve_context",
        },
    )

    graph.add_edge("ask_clarification", "update_memory")
    graph.add_edge("ask_mood_selection", "update_memory")
    graph.add_edge("generate_non_rag_answer", "update_memory")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", "update_memory")
    graph.add_edge("update_memory", END)

    return graph.compile()


def run_chatbot(
    *,
    user_message: str | None = None,
    feedback_text: str | None = None,
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
    """
    외부에서 chatbot_rag를 실행할 때 사용하는 대표 함수.

    현재 챗봇은 추천 결과에 대한 피드백/후속 질문 전용이다.
    feedback_text를 우선 사용하고, 기존 호출 호환을 위해 user_message도 허용한다.
    """

    graph = build_chatbot_graph()

    normalized_target_type = target_type
    if normalized_target_type not in {CATEGORY_HAIR, CATEGORY_MAKEUP, None}:
        normalized_target_type = None

    message = feedback_text if feedback_text is not None else user_message

    initial_state: ChatbotState = {
        "user_message": message or "",
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
        "detected_style_is_recommended": result.get(
            "detected_style_is_recommended",
            False,
        ),
        "retrieval_info": result.get(
            "retrieval_info",
            {
                "retrieved_count": 0,
                "fallback_stage": "none",
            },
        ),
        "updated_chat_history": result.get("updated_chat_history", []),
        "updated_user_profile": result.get("updated_user_profile", {}),
        "error": result.get("error"),
    }
