from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from apps.rag.config import OLLAMA_BASE_URL, OLLAMA_MODEL

# fallback이 약한 단계 — 이 단계에서 검색된 경우 "현재 확보된 데이터 기준으로는" 문구 삽입
_WEAK_STAGES = {"face_shape", "category=hair", "no_result"}

_SYSTEM_PROMPT = """당신은 다정하고 전문적인 뷰티 헤어 디자이너입니다.
고객의 성별, 얼굴형, 삼정 비율에 맞는 헤어스타일을 추천합니다.

반드시 아래 규칙을 따르세요:
1. 반드시 한국어로만 답변하세요. 영어를 절대 사용하지 마세요.
2. 아래 제공된 문맥(context)에 있는 스타일만 추천하세요.
3. 문맥에 없는 스타일을 새로 만들지 마세요.
4. 추천 이유를 반드시 포함하세요.
5. 검색 결과가 부족하거나 fallback이 약한 단계라면 "현재 확보된 데이터 기준으로는"이라고 먼저 말하세요.
6. 고객 정보(성별, 얼굴형, 삼정 비율)를 답변에 자연스럽게 반영하세요.
7. 얼굴형 분석 설명은 핵심만 1~2문장으로 간결하게 작성하세요. 길게 설명하지 마세요."""


def generate_answer(
    query: str,
    gender: str,
    face_shape: str,
    face_proportion: str,
    docs: list[Document],
    fallback_stage: str,
) -> str:
    if not docs:
        return (
            "죄송합니다, 현재 해당 조건에 맞는 헤어스타일 데이터가 충분하지 않습니다. "
            "더 많은 데이터가 축적되면 더 정확한 추천을 드릴 수 있어요!"
        )

    context = "\n\n---\n\n".join(d.page_content for d in docs)
    fallback_prefix = "현재 확보된 데이터 기준으로는 " if fallback_stage in _WEAK_STAGES else ""

    prompt = f"""{_SYSTEM_PROMPT}

[고객 정보]
- 성별: {gender}
- 얼굴형: {face_shape}
- 삼정 비율: {face_proportion}

[검색된 헤어스타일 문맥]
{context}

[고객 질문]
{query}

위 문맥을 바탕으로 {fallback_prefix}고객에게 적합한 헤어스타일을 추천하고 이유를 설명해 주세요.
반드시 한국어로만 답변하세요."""

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content
