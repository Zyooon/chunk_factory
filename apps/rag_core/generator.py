# apps/rag_core/generator.py

import logging
import os
import time
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

from apps.rag_core.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL
from apps.rag_core.prompts import build_generation_prompt
from apps.rag_core.schemas import (
    AnalysisGenerationInput,
    ChatGenerationInput,
    GenerationInput,
    GenerationResult,
    RetrievalResult,
)
from apps.rag_core.utils import format_documents_as_context


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

    주의:
    - .env에 GOOGLE_API_KEY가 있어야 한다.
    - 모델명은 GEMINI_CHAT_MODEL 환경변수로 바꿀 수 있다.
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

    user_context에는 analysis_rag 또는 chatbot_rag가 넘겨주는
    추가 맥락이 들어갈 수 있다.

    예:
    - gender
    - face_shape
    - face_proportion
    - previous_analysis
    - previous_recommendation
    - user_profile
    - chat_history
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


def generate_answer(
    generation_input: GenerationInput,
) -> GenerationResult:
    """
    검색 결과와 사용자 맥락을 바탕으로 Gemini 답변을 생성한다.

    처리 흐름:
    1. RetrievalResult.documents를 context 문자열로 변환
    2. user_context를 문자열로 변환
    3. 최종 prompt 생성
    4. Gemini 호출
    5. GenerationResult 반환
    """

    retrieval_result = generation_input.retrieval_result

    retrieved_context = format_documents_as_context(
        retrieval_result.documents
    )

    user_context_text = format_user_context(
        generation_input.user_context
    )

    prompt = build_generation_prompt(
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

def format_retrieval_results_for_analysis(
    retrieval_results: list[RetrievalResult],
) -> str:
    blocks: list[str] = []

    for result_index, retrieval_result in enumerate(retrieval_results, start=1):
        if not retrieval_result.documents:
            blocks.append(
                "\n".join(
                    [
                        f"[검색 결과 {result_index}]",
                        f"query: {retrieval_result.query}",
                        "검색된 문서 없음",
                        f"fallback_stage: {retrieval_result.fallback_stage}",
                    ]
                )
            )
            continue

        for doc_index, document in enumerate(retrieval_result.documents, start=1):
            metadata = document.metadata or {}
            page_content = document.page_content

            blocks.append(
                "\n".join(
                    [
                        f"[검색 결과 {result_index}-{doc_index}]",
                        f"query: {retrieval_result.query}",
                        f"fallback_stage: {retrieval_result.fallback_stage}",
                        f"category: {metadata.get('category', '')}",
                        f"gender: {metadata.get('gender', '')}",
                        f"face_shape: {metadata.get('face_shape', '')}",
                        f"face_proportion: {metadata.get('face_proportion', '')}",
                        f"style_code: {metadata.get('style_code', '')}",
                        f"style_name: {metadata.get('style_name', '')}",
                        "",
                        page_content,
                    ]
                )
            )

    if not blocks:
        return "검색된 근거 문서가 없습니다."

    return "\n\n---\n\n".join(blocks)


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


def build_analysis_generation_prompt(
    generation_input: AnalysisGenerationInput,
) -> str:
    recommended_style_lines = "\n".join(
        [
            f"- {style.get('style_name', '')}"
            for style in generation_input.recommended_styles
        ]
    )

    context = format_retrieval_results_for_analysis(generation_input.retrieval_results)

    return f"""
당신은 뷰티 디자이너처럼 다정하고 전문적으로 설명하는 RAG 어시스턴트입니다.

반드시 아래 검색 문맥에 있는 정보만 사용하세요.
검색 문맥 밖의 헤어스타일을 새로 추천하지 마세요.
추천된 스타일 목록 밖의 스타일을 새로 추가하지 마세요.
근거가 부족하면 "현재 확보된 데이터 기준으로는"이라고 표현하세요.
검색된 근거가 없는 스타일은 단정하지 말고, 근거 부족을 명확히 말하세요.

[사용자 진단 정보]
- 성별: {generation_input.gender}
- 얼굴형: {generation_input.face_shape}
- 삼정 비율: {generation_input.face_proportion}

[알고리즘 추천 헤어스타일]
{recommended_style_lines}

[검색 문맥]
{context}

[요청]
위 정보를 바탕으로 사용자의 얼굴형과 삼정 비율에 대한 종합 분석을 작성하세요.
추천된 헤어스타일들을 각각 짧게 언급하되, 답변은 하나의 자연스러운 종합 설명으로 작성하세요.
스타일별로 별도 답변을 나누지 마세요.
최종 답변은 5~8문장 정도로 작성하세요.
""".strip()


def generate_analysis_answer(
    generation_input: AnalysisGenerationInput,
) -> GenerationResult:
    prompt = build_analysis_generation_prompt(generation_input)

    generator_mode = os.getenv("RAG_GENERATOR_MODE", "gemini")

    if generator_mode == "mock":
        return GenerationResult(
            answer=(
                "현재는 개발용 mock 응답입니다. "
                f"{generation_input.gender} / {generation_input.face_shape} / "
                f"{generation_input.face_proportion} 조건과 추천 헤어스타일 "
                "목록을 바탕으로 하나의 종합 분석문이 생성될 예정입니다."
            ),
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

def format_previous_recommendations_for_prompt(
    previous_recommendations: list[dict[str, Any]],
) -> str:
    """
    이전 추천 스타일 목록을 프롬프트용 문자열로 변환한다.

    주의:
    - style_code는 내부 식별자이므로 최종 답변에 노출하면 안 된다.
    - 프롬프트에 전달하는 추천 목록에서도 style_code를 제거한다.
    """

    if not previous_recommendations:
        return "이전 추천 스타일 정보가 없습니다."

    lines: list[str] = []

    for recommendation in previous_recommendations:
        style_name = recommendation.get("style_name")

        if style_name:
            lines.append(f"- {style_name}")

    if not lines:
        return "이전 추천 스타일 정보가 없습니다."

    return "\n".join(lines)


def format_chat_history_for_prompt(
    chat_history: list[dict[str, str]],
    max_messages: int = 10,
) -> str:
    """
    최근 대화 기록을 프롬프트용 문자열로 변환한다.

    전체 대화를 모두 넣지 않고 최근 max_messages개만 사용한다.
    """

    if not chat_history:
        return "최근 대화 기록이 없습니다."

    recent_history = chat_history[-max_messages:]

    lines: list[str] = []

    for message in recent_history:
        role = message.get("role", "")
        content = message.get("content", "")

        if not content:
            continue

        if role == "user":
            role_label = "사용자"
        elif role == "assistant":
            role_label = "상담사"
        else:
            role_label = role or "알 수 없음"

        lines.append(f"{role_label}: {content}")

    if not lines:
        return "최근 대화 기록이 없습니다."

    return "\n".join(lines)


def build_chat_generation_prompt(
    generation_input: ChatGenerationInput,
) -> str:
    """
    chatbot_rag 답변 생성을 위한 최종 프롬프트를 만든다.
    """

    retrieved_context = format_documents_as_context(
        generation_input.retrieval_result.documents
    )

    previous_recommendations_text = format_previous_recommendations_for_prompt(
        generation_input.previous_recommendations
    )

    chat_history_text = format_chat_history_for_prompt(
        generation_input.chat_history
    )

    return f"""
당신은 뷰티 디자이너처럼 다정하고 전문적으로 상담하는 RAG 챗봇입니다.

[중요 규칙]
1. 사용자의 진단 정보, 최초 분석 결과, 이전 추천 스타일, 최근 대화 흐름을 함께 반영하세요.
2. 검색된 참고 문맥이 있으면 그 내용을 우선 근거로 사용하세요.
3. 검색된 참고 문맥이 부족하면 이전 분석 결과와 이전 추천 스타일을 기준으로 보수적으로 답변하세요.
4. 검색 문맥과 이전 추천 목록 밖의 헤어스타일을 새로 추천하지 마세요.
5. 데이터가 부족하면 "현재 확보된 데이터 기준으로는"이라고 표현하세요.
6. 답변에는 반드시 이유를 포함하세요.
7. style_code, doc_id, metadata key 같은 내부 식별자는 최종 답변에 절대 노출하지 마세요.
8. 현재 1차 구현 범위는 헤어 상담입니다. 메이크업 상담은 아직 확정적으로 답하지 마세요.

[사용자 진단 정보]
- 성별: {generation_input.gender}
- 얼굴형: {generation_input.face_shape}
- 삼정 비율: {generation_input.face_proportion}

[질문 의도]
{generation_input.intent or "분류되지 않음"}

[최초 분석 결과]
{generation_input.previous_analysis or "이전 분석 결과가 없습니다."}

[이전 추천 헤어스타일]
{previous_recommendations_text}

[유저 취향 정보]
{generation_input.user_profile if generation_input.user_profile else "추가 취향 정보가 없습니다."}

[최근 대화 기록]
{chat_history_text}

[검색된 참고 문맥]
{retrieved_context}

[사용자 질문]
{generation_input.user_message}

[답변 작성 지침]
- 사용자의 질문에 직접 답하세요.
- 이전 분석 결과와 추천 스타일을 기준으로 연결감 있게 답하세요.
- 손질, 유지관리, 비교 질문이면 장단점을 쉽게 설명하세요.
- 근거가 부족하면 단정하지 말고 부족하다고 말하세요.
- 최종 답변은 3~6문장 정도로 자연스럽게 작성하세요.
""".strip()


def generate_chat_answer(
    generation_input: ChatGenerationInput,
) -> GenerationResult:
    """
    chatbot_rag용 답변 생성 함수.

    RAG_GENERATOR_MODE=mock이면 Gemini를 호출하지 않고 개발용 응답을 반환한다.
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