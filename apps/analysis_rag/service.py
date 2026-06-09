from __future__ import annotations

from typing import Any

from apps.rag_core.retriever import get_covered_style_codes, retrieve_many_docs
from apps.rag_core.generator import generate_analysis_answer
from apps.rag_core.schemas import AnalysisGenerationInput, RetrievalQuery


def generate_analysis_result(
    gender: str,
    face_shape: str,
    face_proportion: str,
    recommended_hair_styles: list[dict[str, Any]],
) -> dict[str, Any]:
    if not recommended_hair_styles:
        raise ValueError("recommended_hair_styles는 비어 있을 수 없습니다.")

    covered_codes = get_covered_style_codes()

    retrieval_queries: list[RetrievalQuery] = []
    style_infos: list[dict[str, Any]] = []

    for style in recommended_hair_styles:
        style_name = style.get("style_name")
        style_code = style.get("style_code")

        if not style_name or not style_code:
            raise ValueError("추천 스타일에는 style_name과 style_code가 필요합니다.")

        query = (
            f"{gender} {face_shape} 얼굴형 {face_proportion} 삼정 비율에 "
            f"{style_name} 스타일이 어울리는 이유"
        )

        retrieval_queries.append(
            RetrievalQuery(
                query=query,
                category="hair",
                gender=gender,
                face_shape=face_shape,
                face_proportion=face_proportion,
                style_code=style_code,
                k=3,
            )
        )
        style_infos.append({"style_name": style_name, "style_code": style_code})

    retrieval_results = retrieve_many_docs(retrieval_queries)

    paired = list(zip(style_infos, retrieval_results))

    total_retrieved_count = sum(r.retrieved_count for r in retrieval_results)
    fallback_stages = [r.fallback_stage for r in retrieval_results]

    hair_results: list[dict[str, Any]] = [
        {
            "style_name": si["style_name"],
            "style_code": si["style_code"],
            "retrieved_count": r.retrieved_count,
            "fallback_stage": r.fallback_stage,
            "has_rag_data": si["style_code"] in covered_codes,
        }
        for si, r in paired
    ]

    # ChromaDB 데이터가 있는 스타일만 LLM 분석에 포함
    covered_pairs = [
        (si, r) for si, r in paired if si["style_code"] in covered_codes
    ]

    if covered_pairs:
        analysis_generation_input = AnalysisGenerationInput(
            gender=gender,
            face_shape=face_shape,
            face_proportion=face_proportion,
            recommended_styles=[
                {
                    "style_name": si["style_name"],
                    "style_code": si["style_code"],
                    "retrieved_count": r.retrieved_count,
                    "fallback_stage": r.fallback_stage,
                }
                for si, r in covered_pairs
            ],
            retrieval_results=[r for _, r in covered_pairs],
        )
        analysis_generation_result = generate_analysis_answer(analysis_generation_input)
        analysis_summary = analysis_generation_result.answer
    else:
        analysis_summary = "선택한 헤어스타일에 대한 분석 데이터가 없습니다."

    return {
        "analysis_summary": analysis_summary,
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