# apps/rag_core/generator.py

from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from apps.rag_core.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL
from apps.rag_core.prompts import build_generation_prompt
from apps.rag_core.schemas import GenerationInput, GenerationResult
from apps.rag_core.utils import format_documents_as_context


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
    response = chat_model.invoke(prompt)

    answer = getattr(response, "content", str(response))

    return GenerationResult(
        answer=answer,
        retrieval_result=retrieval_result,
        model_name=GEMINI_CHAT_MODEL,
    )