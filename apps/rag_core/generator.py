# apps/rag_core/generator.py

from __future__ import annotations

import logging
import os
import time
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from apps.analysis_rag.prompts import build_analysis_generation_prompt
from apps.chatbot_rag.prompts import build_chat_generation_prompt
from apps.rag_core.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL
from apps.rag_core.schemas import (
    AnalysisGenerationInput,
    ChatGenerationInput,
    GenerationInput,
    GenerationResult,
    RetrievalResult,
)
from apps.rag_core.utils import format_documents_as_context

logger = logging.getLogger(__name__)


def _is_503(e: Exception) -> bool:
    text = str(e).lower()
    return "503" in text or "service unavailable" in text or "unavailable" in text


def invoke_with_retry(chat_model: ChatGoogleGenerativeAI, prompt: str, max_retries: int = 3) -> Any:
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 2):
        try:
            return chat_model.invoke(prompt)
        except Exception as e:
            if not _is_503(e):
                raise
            last_exc = e
            if attempt <= max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "Gemini 503 오류 (시도 %d/%d), %d초 후 재시도: %s",
                    attempt, max_retries + 1, wait, e,
                )
                time.sleep(wait)

    raise last_exc


def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Gemini Chat Model을 생성한다.
    """

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY가 설정되어 있지 않습니다. "
            ".env 또는 환경변수에 GEMINI_API_KEY를 추가해 주세요."
        )

    return ChatGoogleGenerativeAI(
        model=GEMINI_CHAT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    )


def format_user_context(user_context: dict[str, Any] | None) -> str:
    """
    GenerationInput.user_context를 prompt에 넣기 좋은 문자열로 변환한다.

    이 함수는 generate_answer() 호환용이다.
    analysis_rag와 chatbot_rag는 각 앱의 prompts.py에서 프롬프트를 관리한다.
    """

    if not user_context:
        return ""

    lines: list[str] = []

    gender = user_context.get("gender")
    face_shape = user_context.get("face_shape")
    face_proportion = user_context.get("face_proportion")
    previous_analysis = user_context.get("previous_analysis")
    previous_recommendation = user_context.get("previous_recommendation")
    user_profile = user_context.get("user_profile")
    chat_history = user_context.get("chat_history")

    if gender:
        lines.append(f"- 성별: {gender}")

    if face_shape:
        lines.append(f"- 얼굴형: {face_shape}")

    if face_proportion:
        lines.append(f"- 삼정 비율: {face_proportion}")

    if previous_analysis:
        lines.append("")
        lines.append("[이전 분석 결과]")
        lines.append(str(previous_analysis))

    if previous_recommendation:
        lines.append("")
        lines.append("[이전 추천 결과]")
        lines.append(str(previous_recommendation))

    if user_profile:
        lines.append("")
        lines.append("[유저 취향 정보]")
        lines.append(str(user_profile))

    if chat_history:
        lines.append("")
        lines.append("[최근 대화 히스토리]")
        lines.append(str(chat_history))

    return "\n".join(lines)


def build_direct_generation_prompt(
    *,
    user_question: str,
    retrieved_context: str,
    user_context_text: str = "",
    system_instruction: str,
) -> str:
    """
    generate_answer() 호환용 직접 프롬프트 생성 함수.

    공통 프롬프트는 사용하지 않는다.
    호출자가 명시적으로 전달한 system_instruction만 사용한다.
    """

    return f"""
[시스템 지시문]
{system_instruction}

[사용자 정보 및 이전 맥락]
{user_context_text if user_context_text else "추가 사용자 맥락 없음"}

[검색된 참고 문맥]
{retrieved_context}

[사용자 요청]
{user_question}
""".strip()


def generate_answer(
    generation_input: GenerationInput,
) -> GenerationResult:
    """
    범용 Gemini 답변 생성 함수.

    공통 프롬프트를 제거했기 때문에 이 함수는 system_instruction을
    명시적으로 받은 경우에만 사용한다.
    analysis_rag와 chatbot_rag는 전용 generate 함수를 사용한다.
    """

    if not generation_input.system_instruction:
        raise ValueError(
            "generate_answer()는 공통 프롬프트를 사용하지 않습니다. "
            "system_instruction을 명시적으로 전달하거나, "
            "analysis_rag/chatbot_rag 전용 생성 함수를 사용하세요."
        )

    retrieval_result = generation_input.retrieval_result

    retrieved_context = format_documents_as_context(
        retrieval_result.documents
    )

    user_context_text = format_user_context(
        generation_input.user_context
    )

    prompt = build_direct_generation_prompt(
        user_question=generation_input.user_question,
        retrieved_context=retrieved_context,
        user_context_text=user_context_text,
        system_instruction=generation_input.system_instruction,
    )

    chat_model = get_chat_model()
    response = invoke_with_retry(chat_model, prompt)

    answer = normalize_model_content(getattr(response, "content", response))

    return GenerationResult(
        answer=answer,
        retrieval_result=retrieval_result,
        model_name=GEMINI_CHAT_MODEL,
    )


def normalize_model_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts: list[str] = []

        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(str(item["text"]))
            else:
                texts.append(str(item))

        return "\n".join(texts)

    return str(content)


def _get_analysis_category(generation_input: AnalysisGenerationInput) -> str:
    for retrieval_result in generation_input.retrieval_results:
        for document in retrieval_result.documents:
            category = (document.metadata or {}).get("category")
            if category in {"hair", "makeup"}:
                return str(category)

    return "hair"


def generate_analysis_answer(
    generation_input: AnalysisGenerationInput,
) -> GenerationResult:
    """
    analysis_rag용 답변 생성 함수.

    프롬프트 본문은 apps.analysis_rag.prompts에서만 관리한다.
    """

    prompt = build_analysis_generation_prompt(generation_input)

    generator_mode = os.getenv("RAG_GENERATOR_MODE", "gemini")

    if generator_mode == "mock":
        category = _get_analysis_category(generation_input)
        if category == "makeup":
            answer = (
                "현재는 개발용 mock 메이크업 분석 응답입니다. "
                f"{generation_input.gender} / {generation_input.personal_color} 조건과 "
                "추천 메이크업 목록을 바탕으로 별도 분석문이 생성될 예정입니다."
            )
        else:
            answer = (
                "현재는 개발용 mock 헤어 분석 응답입니다. "
                f"{generation_input.gender} / {generation_input.face_shape} / "
                f"{generation_input.face_proportion} 조건과 추천 헤어스타일 "
                "목록을 바탕으로 별도 분석문이 생성될 예정입니다."
            )

        return GenerationResult(
            answer=answer,
            retrieval_result=RetrievalResult(query="analysis_rag"),
            model_name="mock",
        )

    chat_model = get_chat_model()
    response = invoke_with_retry(chat_model=chat_model, prompt=prompt)

    return GenerationResult(
        answer=normalize_model_content(response.content),
        retrieval_result=RetrievalResult(query="analysis_rag"),
        model_name=GEMINI_CHAT_MODEL,
    )


def generate_chat_answer(
    generation_input: ChatGenerationInput,
) -> GenerationResult:
    """
    chatbot_rag용 답변 생성 함수.

    프롬프트 본문은 apps.chatbot_rag.prompts에서만 관리한다.
    """

    prompt = build_chat_generation_prompt(generation_input)

    generator_mode = os.getenv("RAG_GENERATOR_MODE", "gemini")

    if generator_mode == "mock":
        return GenerationResult(
            answer=(
                "현재는 개발용 mock 챗봇 응답입니다. "
                f"{generation_input.gender} / {generation_input.face_shape} / "
                f"{generation_input.face_proportion} 조건과 이전 분석 결과를 바탕으로 "
                f"'{generation_input.user_message}' 질문에 답변할 예정입니다."
            ),
            retrieval_result=generation_input.retrieval_result,
            model_name="mock",
        )

    chat_model = get_chat_model()
    response = invoke_with_retry(chat_model=chat_model, prompt=prompt)

    return GenerationResult(
        answer=normalize_model_content(response.content),
        retrieval_result=generation_input.retrieval_result,
        model_name=GEMINI_CHAT_MODEL,
    )
