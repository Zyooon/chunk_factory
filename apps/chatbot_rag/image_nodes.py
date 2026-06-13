from __future__ import annotations

from typing import Any

from apps.chatbot_rag.state import ChatbotState
from apps.rag_core.schemas import RetrievalResult


# ---------------------------------------------------------------------------
# Image intent 상수
# ---------------------------------------------------------------------------

IMAGE_INTENT_SYNTHESIS = "image_synthesis"
IMAGE_INTENT_FIT_CHECK = "image_fit_check"
IMAGE_INTENT_STYLE_MATCH = "image_style_match"
IMAGE_INTENT_MAKEUP_MATCH = "image_makeup_match"
IMAGE_INTENT_GENERAL_ANALYSIS = "image_general_analysis"
IMAGE_INTENT_NONE = "image_none"

# 합성 키워드 — fallback/debug 참조용으로만 사용한다.
_SYNTHESIS_KEYWORDS = {"합성", "입혀줘", "적용해줘", "바꿔줘"}

_SYNTHESIS_PENDING_ANSWER = (
    "이미지 합성 요청으로 확인되었습니다. 합성 기능은 추후 연결 예정입니다."
)


# ---------------------------------------------------------------------------
# stub: 실제 멀티모달 LLM intent 분류 시 이 함수만 교체하면 된다.
# ---------------------------------------------------------------------------

def classify_image_intent_with_llm(
    image_url: str,
    user_message: str,
    target_type: str | None,
) -> dict[str, Any]:
    """
    멀티모달 LLM으로 이미지 intent를 분류한다.

    현재는 stub 구현이며 추후 Gemini Vision API 호출로 교체한다.

    반환:
        {
            "intent": "image_fit_check",   # IMAGE_INTENT_* 중 하나
            "confidence": "medium",
            "reason": "...",
        }
    """
    # TODO: Gemini Vision API 연동
    # 키워드 기반 fallback으로 stub 동작 확인
    if any(kw in user_message for kw in _SYNTHESIS_KEYWORDS):
        return {
            "intent": IMAGE_INTENT_SYNTHESIS,
            "confidence": "high",
            "reason": "synthesis_keyword_fallback",
        }
    return {
        "intent": IMAGE_INTENT_GENERAL_ANALYSIS,
        "confidence": "low",
        "reason": "stub_default",
    }


# ---------------------------------------------------------------------------
# stub: 실제 Gemini Vision 이미지 분석 시 이 함수만 교체하면 된다.
# ---------------------------------------------------------------------------

def analyze_image_with_llm(image_url: str, user_message: str) -> dict[str, Any]:
    """
    멀티모달 LLM으로 이미지를 분석하고 구조화된 결과를 반환한다.

    현재는 stub 구현이며, 추후 Gemini Vision API 호출로 교체한다.

    반환 예:
        {
            "category": "hair",
            "detected_style_name": "리프",
            "style_code_candidates": ["m-09"],
            "visual_features": ["긴 앞머리", "가르마", "귀 주변 길이감"],
            "rag_query_text": "긴 앞머리와 가르마가 있는 남성 리프 계열 스타일",
            "confidence": "medium",
        }
    """
    # TODO: Gemini Vision API 연동
    return {
        "category": "hair",
        "detected_style_name": "",
        "style_code_candidates": [],
        "visual_features": [],
        "rag_query_text": "",
        "confidence": "low",
    }


# ---------------------------------------------------------------------------
# LangGraph 노드
# ---------------------------------------------------------------------------

def classify_image_intent(state: ChatbotState) -> ChatbotState:
    """
    image_url이 있을 때 멀티모달 LLM으로 이미지 intent를 분류한다.

    image_url이 없으면 image_intent=IMAGE_INTENT_NONE으로 설정하고 반환한다.
    image_is_synthesis_request는 intent 결과에서만 결정한다.
    """
    image_url = state.get("image_url")

    if not image_url:
        state["image_intent"] = IMAGE_INTENT_NONE
        state["image_intent_debug"] = {"reason": "no_image_url"}
        state["image_is_synthesis_request"] = False
        return state

    user_message = state.get("user_message", "")
    target_type = state.get("target_type")

    result = classify_image_intent_with_llm(
        image_url=image_url,
        user_message=user_message,
        target_type=target_type,
    )

    intent = result.get("intent", IMAGE_INTENT_GENERAL_ANALYSIS)
    state["image_intent"] = intent
    state["image_intent_debug"] = result
    state["image_is_synthesis_request"] = intent == IMAGE_INTENT_SYNTHESIS

    return state


def analyze_image_if_needed(state: ChatbotState) -> ChatbotState:
    """
    이미지 LLM 분석을 수행하고 결과를 state에 채운다.

    합성 판단은 classify_image_intent가 담당하므로 이 노드는 순수하게
    이미지 내용을 분석하는 역할만 한다.
    """
    image_url = state.get("image_url")

    if not image_url:
        return state

    user_message = state.get("user_message", "")
    analysis = analyze_image_with_llm(image_url, user_message)

    state["image_analysis"] = analysis
    state["image_visual_features"] = analysis.get("visual_features") or []
    state["image_detected_style"] = {
        "detected_style_name": analysis.get("detected_style_name") or "",
        "style_code_candidates": analysis.get("style_code_candidates") or [],
        "category": analysis.get("category") or "",
        "confidence": analysis.get("confidence") or "low",
    }

    return state


def handle_image_synthesis_request(state: ChatbotState) -> ChatbotState:
    """
    이미지 합성 요청에 대한 임시(pending) 응답을 반환한다.

    실제 합성 기능은 별도 구현 예정이므로 RAG를 타지 않고
    안내 메시지만 반환한다.
    """
    state["answer"] = _SYNTHESIS_PENDING_ANSWER
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
        "skip_reason": "image_synthesis_request",
        "image_intent": state.get("image_intent"),
        "image_intent_debug": state.get("image_intent_debug"),
    }
    return state


# ---------------------------------------------------------------------------
# 사용 예시 (CLI 또는 함수 호출)
# ---------------------------------------------------------------------------
#
# 1) image_url 없이 호출 → 기존 텍스트 챗봇 흐름 유지
#
#     result = run_chatbot(
#         user_message="추천해준 리프 스타일이 내 얼굴형에 어울릴까요?",
#         gender="남성", face_shape="둥근형", face_proportion="균형",
#         previous_analysis="...",
#         previous_recommendations=[{"style_name": "리프", "style_code": "m-09"}],
#     )
#
# 2) image_url + 분석/어울림 요청 → image_fit_check/image_general_analysis
#    → analyze_image_if_needed → RAG 검색 → generate_answer
#
#     result = run_chatbot(
#         user_message="이 스타일이 나한테 어울릴까요?",
#         image_url="http://localhost:8000/uploads/user_photo.jpg",
#         ...
#     )
#     # result["image_intent"] → "image_fit_check" or "image_general_analysis"
#     # result["image_analysis"] → LLM 분석 결과 dict
#
# 3) image_url + 합성 요청 → image_synthesis → pending 안내 응답
#
#     result = run_chatbot(
#         user_message="이 헤어스타일 나한테 입혀줘",
#         image_url="http://localhost:8000/uploads/style_ref.jpg",
#         ...
#     )
#     # result["image_intent"] → "image_synthesis"
#     # result["answer"] → "이미지 합성 요청으로 확인되었습니다. ..."
