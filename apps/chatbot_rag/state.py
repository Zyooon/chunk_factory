from __future__ import annotations

from typing import Any, TypedDict

from apps.rag_core.schemas import RetrievalResult


class ChatbotState(TypedDict, total=False):
    """
    chatbot_rag LangGraph에서 노드들이 공유하는 상태 구조.

    total=False:
        모든 key를 반드시 처음부터 넣지 않아도 되게 한다.
        각 노드가 필요한 값을 순차적으로 추가할 수 있다.
    """

    # 현재 사용자 피드백 질문
    user_message: str

    # 피드백 대상
    target_type: str | None
    applied_style_key: str | None

    # 사용자 진단 정보
    gender: str
    face_shape: str
    face_proportion: str
    personal_color: str

    # 최초 분석 및 추천 결과
    previous_analysis: str | dict[str, Any] | None
    previous_recommendations: list[dict[str, Any]]

    # 대화 중 누적되는 사용자 취향 정보
    user_profile: dict[str, Any]

    # 최근 대화 기록
    chat_history: list[dict[str, str]]

    # 질문 의도 분류 결과
    intent: str
    category: str

    # 사용자 메시지 또는 applied_style_key에서 감지된 헤어스타일 또는 메이크업 스타일
    detected_style: dict[str, str] | None
    detected_style_is_recommended: bool

    # 문맥이 불명확할 때 객관식 재질문에 사용
    needs_clarification: bool
    clarification_options: list[str]

    # RAG 검색 결과
    retrieval_result: RetrievalResult

    # 최종 답변
    answer: str

    # 처리 중 발생한 상태/오류 정보
    error: str | None

    # 응답 metadata
    retrieval_info: dict[str, Any]

    # 업데이트된 대화 기록/유저 정보
    updated_chat_history: list[dict[str, str]]
    updated_user_profile: dict[str, Any]
