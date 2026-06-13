from __future__ import annotations

from typing import Any

from apps.chatbot_rag.state import ChatbotState
from apps.rag_core.schemas import RetrievalResult


# 합성 요청으로 간주할 키워드
_SYNTHESIS_KEYWORDS = {"합성", "입혀줘", "적용해줘", "바꿔줘"}

_SYNTHESIS_PENDING_ANSWER = (
    "이미지 합성 요청으로 확인되었습니다. 합성 기능은 추후 연결 예정입니다."
)


# ---------------------------------------------------------------------------
# stub: 실제 Gemini Vision 연동 시 이 함수만 교체하면 된다.
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
            "confidence": "medium",
        }
    """
    # TODO: Gemini Vision API 연동
    # response = gemini_client.generate_content([image_url, user_message])
    # return parse_image_analysis(response)
    return {
        "category": "hair",
        "detected_style_name": "",
        "style_code_candidates": [],
        "visual_features": [],
        "confidence": "low",
    }


# ---------------------------------------------------------------------------
# LangGraph 노드
# ---------------------------------------------------------------------------

def analyze_image_if_needed(state: ChatbotState) -> ChatbotState:
    """
    image_url이 있을 때만 이미지 분석을 수행한다.

    - image_url이 없으면 기존 흐름 그대로 통과한다.
    - 합성 키워드가 포함된 메시지면 image_is_synthesis_request=True를 설정하고
      LLM 호출 없이 반환한다.
    - 일반 이미지 질문이면 analyze_image_with_llm()을 호출해 state를 채운다.
    """
    image_url = state.get("image_url")

    if not image_url:
        state["image_is_synthesis_request"] = False
        return state

    user_message = state.get("user_message", "")

    if any(kw in user_message for kw in _SYNTHESIS_KEYWORDS):
        state["image_is_synthesis_request"] = True
        return state

    analysis = analyze_image_with_llm(image_url, user_message)

    state["image_analysis"] = analysis
    state["image_visual_features"] = analysis.get("visual_features") or []
    state["image_detected_style"] = {
        "detected_style_name": analysis.get("detected_style_name") or "",
        "style_code_candidates": analysis.get("style_code_candidates") or [],
        "category": analysis.get("category") or "",
        "confidence": analysis.get("confidence") or "low",
    }
    state["image_is_synthesis_request"] = False

    return state


def handle_image_synthesis_request(state: ChatbotState) -> ChatbotState:
    """
    이미지 합성 요청에 대한 임시(pending) 응답을 반환한다.

    실제 합성 기능은 별도 팀에서 구현 예정이므로 RAG를 타지 않고
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
        "intent_debug": state.get("intent_debug"),
    }
    return state


# ---------------------------------------------------------------------------
# 사용 예시 (CLI 또는 함수 호출)
# ---------------------------------------------------------------------------
#
# 1) image_url 없이 호출 → 기존 동작 유지
#
#     from apps.chatbot_rag.graph import run_chatbot
#     result = run_chatbot(
#         user_message="추천해준 리프 스타일이 내 얼굴형에 어울릴까요?",
#         gender="남성",
#         face_shape="둥근형",
#         face_proportion="균형",
#         previous_analysis="...",
#         previous_recommendations=[{"style_name": "리프", "style_code": "m-09"}],
#     )
#
# 2) image_url + 일반 질문 → image_analysis 생성 후 RAG query에 반영
#
#     result = run_chatbot(
#         user_message="이 스타일이 나한테 어울릴까요?",
#         image_url="http://localhost:8000/uploads/user_photo.jpg",
#         gender="남성",
#         face_shape="둥근형",
#         face_proportion="균형",
#         previous_analysis="...",
#         previous_recommendations=[...],
#     )
#     # result["image_analysis"]  → LLM 분석 결과 dict
#
# 3) image_url + 합성 요청 → RAG 생략, 임시 안내 응답 반환
#
#     result = run_chatbot(
#         user_message="이 헤어스타일 나한테 입혀줘",
#         image_url="http://localhost:8000/uploads/style_ref.jpg",
#         gender="남성",
#         face_shape="둥근형",
#         face_proportion="균형",
#         previous_analysis="...",
#         previous_recommendations=[...],
#     )
#     # result["answer"] → "이미지 합성 요청으로 확인되었습니다. 합성 기능은 추후 연결 예정입니다."
#     # result["image_is_synthesis_request"] → True
