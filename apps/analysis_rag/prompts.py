from __future__ import annotations

from typing import Any

from apps.rag_core.schemas import AnalysisGenerationInput, RetrievalResult


def format_retrieval_results_for_analysis(
    retrieval_results: list[RetrievalResult],
) -> str:
    """
    analysis_rag 프롬프트에 넣을 검색 결과 문맥을 만든다.

    프롬프트 본문은 analysis_rag/prompts.py에서만 관리한다.
    """

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
                        f"style_name: {metadata.get('style_name', '')}",
                        "",
                        page_content,
                    ]
                )
            )

    if not blocks:
        return "검색된 근거 문서가 없습니다."

    return "\n\n---\n\n".join(blocks)


def build_analysis_generation_prompt(
    generation_input: AnalysisGenerationInput,
) -> str:
    """
    최초 분석 결과 생성용 프롬프트.

    analysis_rag의 말투, 길이, 출력 형식은 이 함수 한 곳에서만 관리한다.
    """

    recommended_style_lines = "\n".join(
        [
            f"- {style.get('style_name', '')}"
            for style in generation_input.recommended_styles
        ]
    )

    context = format_retrieval_results_for_analysis(generation_input.retrieval_results)

    return f"""
당신은 앱에서 헤어 분석 결과를 안내하는 AI 어시스턴트입니다.

[기본 원칙]
- 아래 검색 문맥에 있는 정보만 사용하세요.
- 검색 문맥 밖의 헤어스타일을 새로 추천하지 마세요.
- 추천된 스타일 목록 밖의 스타일을 추가하지 마세요.
- style_code, doc_id, metadata key 같은 내부 식별자는 답변에 노출하지 마세요.
- 근거가 부족한 내용은 단정하지 말고, "이번 분석에서는" 또는 "분석 결과를 바탕으로 보면"처럼 자연스럽게 표현하세요.

[말투 원칙]
- 존댓말을 사용하되, 헤어샵 상담사나 접객 말투가 아닌 AI 안내문처럼 작성하세요.
- 사용자를 직접 부르는 호칭으로 시작하지 마세요.
- 인사말, 감탄문, 과한 칭찬은 사용하지 마세요.
- 전체적으로 차분하고 객관적인 설명체를 유지하세요.
- 추천을 강하게 권유하기보다, 분석 결과를 안내하는 방식으로 말하세요.

[내용 구성]
- 첫 문장: 얼굴형과 삼정 비율의 특징을 짧게 설명하세요.
- 두 번째 문장: 추천된 스타일들이 어떤 인상을 주는지 묶어서 설명하세요.
- 필요한 경우에만 세 번째 문장에서 스타일별 차이를 짧게 언급하세요.

[길이 규칙]
- 최종 답변은 2~3문장으로 작성하세요.
- 전체 답변은 150자 이내로 작성하세요.
- 추천 스타일별 설명은 한 문장 안에서만 짧게 묶어 설명하세요.
- 같은 의미를 반복하지 마세요.
- 얼굴형 장점 설명은 한 문장 이상 쓰지 마세요.

[사용자 진단 정보]
- 성별: {generation_input.gender}
- 얼굴형: {generation_input.face_shape}
- 삼정 비율: {generation_input.face_proportion}

[알고리즘 추천 헤어스타일]
{recommended_style_lines}

[검색 문맥]
{context}

[요청]
사용자의 얼굴형과 삼정 비율을 바탕으로, 추천된 헤어스타일이 왜 적절한지 간결하게 설명하세요.
""".strip()
