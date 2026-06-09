from __future__ import annotations

from typing import Any

from apps.chatbot_rag.memory import (
    append_chat_history,
    extract_simple_user_preferences,
    merge_user_profile,
)
from apps.chatbot_rag.prompts import (
    CATEGORY_HAIR,
    CLARIFICATION_OPTIONS,
    GREETING_MESSAGE,
    INTENT_GENERAL_FOLLOWUP,
    INTENT_GREETING,
    INTENT_IRRELEVANT,
    INTENT_MISSING_ANALYSIS,
    INTENT_NOISE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR,
    IRRELEVANT_MESSAGE,
    MISSING_ANALYSIS_MESSAGE,
    NOISE_MESSAGE,
    SMALLTALK_MESSAGE,
    build_clarification_message,
    get_intent_by_keyword,
)

from apps.chatbot_rag.state import ChatbotState
from apps.rag_core.generator import generate_chat_answer
from apps.rag_core.retriever import retrieve_docs
from apps.rag_core.schemas import ChatGenerationInput, RetrievalResult
from apps.chatbot_rag.style_catalog import find_hair_style_in_message


def check_analysis_exists(state: ChatbotState) -> ChatbotState:
    """
    chatbot_rag 실행 전제 조건을 확인한다.

    chatbot_rag는 최초 분석 이후의 후속 상담 기능이므로
    previous_analysis와 previous_recommendations가 없으면
    RAG 검색이나 Gemini 호출을 하지 않고 조기 반환한다.
    """

    previous_analysis = state.get("previous_analysis")
    previous_recommendations = state.get("previous_recommendations") or []

    if previous_analysis and previous_recommendations:
        state["error"] = None
        return state

    state["intent"] = INTENT_MISSING_ANALYSIS
    state["category"] = CATEGORY_HAIR
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
    }

    return state


def classify_intent(state: ChatbotState) -> ChatbotState:
    """
    사용자 질문의 의도를 keyword 기반으로 분류한다.

    현재 1차 구현은 hair chatbot이므로 category는 hair로 고정한다.
    """

    if state.get("error") == "missing_analysis":
        return state

    user_message = state.get("user_message", "")

    intent = get_intent_by_keyword(user_message)

    state["intent"] = intent
    state["category"] = CATEGORY_HAIR

    if intent == INTENT_UNCLEAR:
        state["needs_clarification"] = True
        state["clarification_options"] = CLARIFICATION_OPTIONS
    else:
        state["needs_clarification"] = False
        state["clarification_options"] = []

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
    }

    return state

def generate_non_rag_answer(state: ChatbotState) -> ChatbotState:
    """
    RAG 검색이나 Gemini 호출이 필요 없는 입력에 대해 고정 응답을 반환한다.

    예:
    - greeting: 인사
    - smalltalk: 간단 반응
    - irrelevant: 헤어 상담 범위 밖 질문
    - noise: 의미 없는 입력
    """

    intent = state.get("intent")

    if intent == INTENT_GREETING:
        answer = GREETING_MESSAGE
    elif intent == INTENT_SMALLTALK:
        answer = SMALLTALK_MESSAGE
    elif intent == INTENT_IRRELEVANT:
        answer = IRRELEVANT_MESSAGE
    elif intent == INTENT_NOISE:
        answer = NOISE_MESSAGE
    else:
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
    }

    return state


def _find_style_code_from_message(
    user_message: str,
    previous_recommendations: list[dict[str, Any]],
) -> str | None:
    """
    사용자 질문에 이전 추천 스타일명이 포함되어 있으면 해당 style_code를 찾는다.

    style_code는 검색 filter에만 사용하고,
    최종 답변에는 노출하지 않는다.
    """

    for recommendation in previous_recommendations:
        style_name = recommendation.get("style_name")
        style_code = recommendation.get("style_code")

        if not style_name or not style_code:
            continue

        if style_name in user_message:
            return style_code

    return None


def retrieve_context(state: ChatbotState) -> ChatbotState:
    """
    현재 질문과 사용자 진단 정보를 바탕으로 ChromaDB에서 hair 문서를 검색한다.

    검색 실패는 치명적인 오류로 보지 않는다.
    검색 결과가 없어도 generate_answer_node에서 이전 분석 결과 기반으로 답변할 수 있다.
    """

    if state.get("error") == "missing_analysis":
        return state

    if state.get("needs_clarification"):
        return state

    user_message = state.get("user_message", "")
    gender = state.get("gender")
    face_shape = state.get("face_shape")
    face_proportion = state.get("face_proportion")
    previous_recommendations = state.get("previous_recommendations") or []

    detected_style = state.get("detected_style")

    if detected_style:
        style_code = detected_style.get("style_code")
    else:
        style_code = _find_style_code_from_message(
            user_message=user_message,
            previous_recommendations=previous_recommendations,
        )

    detected_style_name = ""
    if detected_style:
        detected_style_name = detected_style.get("style_name", "")

    query = (
        f"{gender or ''} {face_shape or ''} 얼굴형 "
        f"{face_proportion or ''} 삼정 비율 "
        f"{detected_style_name} "
        f"{user_message}"
    ).strip()

    try:
        retrieval_result = retrieve_docs(
            query=query,
            category=CATEGORY_HAIR,
            gender=gender,
            face_shape=face_shape,
            face_proportion=face_proportion,
            style_code=style_code,
            k=3,
        )

        state["retrieval_result"] = retrieval_result
        state["retrieval_info"] = {
            "retrieved_count": retrieval_result.retrieved_count,
            "fallback_stage": retrieval_result.fallback_stage
            if retrieval_result.fallback_stage is not None
            else "none",
            "used_filter": retrieval_result.used_filter,
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
            "retrieved_count": 0,
            "fallback_stage": "none",
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

    generation_input = ChatGenerationInput(
        user_message=state.get("user_message", ""),
        gender=state.get("gender", ""),
        face_shape=state.get("face_shape", ""),
        face_proportion=state.get("face_proportion", ""),
        previous_analysis=state.get("previous_analysis"),
        previous_recommendations=state.get("previous_recommendations") or [],
        user_profile=state.get("user_profile") or {},
        chat_history=state.get("chat_history") or [],
        retrieval_result=retrieval_result,
        intent=state.get("intent"),
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
        "retrieved_count": generation_result.retrieval_result.retrieved_count,
        "fallback_stage": generation_result.retrieval_result.fallback_stage
        if generation_result.retrieval_result.fallback_stage is not None
        else "none",
        "used_filter": generation_result.retrieval_result.used_filter,
        "model_name": generation_result.model_name,
    }

    return state


def update_memory(state: ChatbotState) -> ChatbotState:
    """
    답변 생성 후 chat_history와 user_profile을 업데이트한다.

    초기 구현에서는 DB 저장 없이 state 안의 값만 갱신한다.
    """

    user_message = state.get("user_message", "")
    answer = state.get("answer", "")

    updated_chat_history = append_chat_history(
        chat_history=state.get("chat_history") or [],
        user_message=user_message,
        assistant_answer=answer,
    )

    new_preferences = extract_simple_user_preferences(user_message)

    updated_user_profile = merge_user_profile(
        user_profile=state.get("user_profile") or {},
        new_preferences=new_preferences,
    )

    state["updated_chat_history"] = updated_chat_history
    state["updated_user_profile"] = updated_user_profile

    return state

def classify_intent(state: ChatbotState) -> ChatbotState:
    """
    사용자 질문의 의도를 분류한다.

    1차는 keyword 기반으로 빠르게 분류한다.
    사용자가 전체 헤어스타일 목록 중 특정 스타일을 물어보면,
    추천 목록 밖 스타일이라도 hair follow-up으로 처리한다.
    """

    if state.get("error") == "missing_analysis":
        return state

    user_message = state.get("user_message", "")
    gender = state.get("gender")
    previous_recommendations = state.get("previous_recommendations") or []

    intent = get_intent_by_keyword(user_message)

    detected_style = find_hair_style_in_message(
        message=user_message,
        gender=gender,
    )

    detected_style_is_recommended = _is_recommended_style(
        detected_style=detected_style,
        previous_recommendations=previous_recommendations,
    )

    # 추천 목록 밖 스타일이라도 사용자가 명시적으로 물어본 경우 hair 상담으로 처리한다.
    if detected_style and intent in {
        INTENT_UNCLEAR,
        INTENT_GREETING,
        INTENT_SMALLTALK,
        INTENT_IRRELEVANT,
        INTENT_NOISE,
    }:
        intent = INTENT_GENERAL_FOLLOWUP

    state["intent"] = intent
    state["category"] = CATEGORY_HAIR
    state["detected_style"] = detected_style
    state["detected_style_is_recommended"] = detected_style_is_recommended

    if intent == INTENT_UNCLEAR:
        state["needs_clarification"] = True
        state["clarification_options"] = CLARIFICATION_OPTIONS
    else:
        state["needs_clarification"] = False
        state["clarification_options"] = []

    return state

def _is_recommended_style(
    detected_style: dict[str, str] | None,
    previous_recommendations: list[dict[str, Any]],
) -> bool:
    """
    감지된 스타일이 이전 추천 목록에 포함되어 있는지 확인한다.
    """

    if not detected_style:
        return False

    detected_style_code = detected_style.get("style_code")
    detected_style_name = detected_style.get("style_name")

    for recommendation in previous_recommendations:
        if detected_style_code and recommendation.get("style_code") == detected_style_code:
            return True

        if detected_style_name and recommendation.get("style_name") == detected_style_name:
            return True

    return False