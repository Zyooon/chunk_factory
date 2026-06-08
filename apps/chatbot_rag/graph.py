from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.chatbot_rag.nodes import (
    ask_clarification,
    check_analysis_exists,
    classify_intent,
    generate_answer_node,
    retrieve_context,
    update_memory,
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

    질문 의도가 불명확하면 객관식 재질문으로 이동한다.
    """

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
            "retrieve_context": "retrieve_context",
        },
    )

    graph.add_edge("ask_clarification", "update_memory")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", "update_memory")
    graph.add_edge("update_memory", END)

    return graph.compile()


def run_chatbot(
    *,
    user_message: str,
    gender: str,
    face_shape: str,
    face_proportion: str,
    previous_analysis: str | dict[str, Any] | None = None,
    previous_recommendations: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    외부에서 chatbot_rag를 실행할 때 사용하는 대표 함수.

    API나 CLI에서는 이 함수만 호출하면 된다.
    """

    graph = build_chatbot_graph()

    initial_state: ChatbotState = {
        "user_message": user_message,
        "gender": gender,
        "face_shape": face_shape,
        "face_proportion": face_proportion,
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
        "needs_clarification": result.get("needs_clarification", False),
        "clarification_options": result.get("clarification_options", []),
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