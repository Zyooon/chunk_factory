from __future__ import annotations

from typing import Any

from apps.rag_core.retriever import retrieve_docs
from apps.rag_core.generator import generate_analysis_answer
from apps.rag_core.schemas import AnalysisGenerationInput


def generate_analysis_result(
    gender: str,
    face_shape: str,
    face_proportion: str,
    recommended_hair_styles: list[dict[str, Any]],
) -> dict[str, Any]:
    if not recommended_hair_styles:
        raise ValueError("recommended_hair_styles는 비어 있을 수 없습니다.")

    retrieval_results = []
    hair_results: list[dict[str, Any]] = []
    total_retrieved_count = 0
    fallback_stages: list[str] = []

    for style in recommended_hair_styles:
        style_name = style.get("style_name")
        style_code = style.get("style_code")

        if not style_name or not style_code:
            raise ValueError("추천 스타일에는 style_name과 style_code가 필요합니다.")

        query = (
            f"{gender} {face_shape} 얼굴형 {face_proportion} 삼정 비율에 "
            f"{style_name} 스타일이 어울리는 이유"
        )

        retrieval_result = retrieve_docs(
            query=query,
            category="hair",
            gender=gender,
            face_shape=face_shape,
            face_proportion=face_proportion,
            style_code=style_code,
            k=3,
        )

        retrieval_results.append(retrieval_result)
        total_retrieved_count += retrieval_result.retrieved_count
        fallback_stages.append(retrieval_result.fallback_stage)

        hair_results.append(
            {
                "style_name": style_name,
                "style_code": style_code,
                "retrieved_count": retrieval_result.retrieved_count,
                "fallback_stage": retrieval_result.fallback_stage,
            }
        )

    analysis_generation_input = AnalysisGenerationInput(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        recommended_styles=hair_results,
        retrieval_results=retrieval_results,
    )

    analysis_generation_result = generate_analysis_answer(analysis_generation_input)

    return {
        "analysis_summary": analysis_generation_result.answer,
        "hair_recommendations": hair_results,
        "makeup_recommendations": [],
        "cautions": [
            "현재 결과는 확보된 헤어 RAG 데이터 기준으로 생성되었습니다.",
            "검색 근거가 부족한 스타일은 단정하지 않고 보수적으로 설명합니다.",
        ],
        "retrieval_info": {
            "hair_docs": total_retrieved_count,
            "makeup_docs": 0,
            "fallback_stages": fallback_stages,
        },
    }