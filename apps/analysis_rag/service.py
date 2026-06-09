from __future__ import annotations

from typing import Any

from apps.rag_core.retriever import retrieve_many_docs
from apps.rag_core.generator import generate_analysis_answer
from apps.rag_core.schemas import AnalysisGenerationInput, RetrievalQuery, RetrievalResult


def _result_contains_style_code(
    retrieval_result: RetrievalResult,
    style_code: str,
) -> bool:
    """
    검색 결과 안에 요청한 style_code 문서가 실제로 포함되어 있는지 확인한다.

    fallback 검색은 후순위 단계에서 category 또는 face_shape만으로도 결과를
    반환할 수 있으므로, retrieved_count만으로는 해당 스타일의 RAG 데이터가
    있다고 판단하기 어렵다.
    """
    for document in retrieval_result.documents:
        metadata = document.metadata or {}
        if metadata.get("style_code") == style_code:
            return True

    return False


def generate_analysis_result(
    gender: str,
    face_shape: str,
    face_proportion: str,
    recommended_hair_styles: list[dict[str, Any]],
) -> dict[str, Any]:
    if not recommended_hair_styles:
        raise ValueError("recommended_hair_styles는 비어 있을 수 없습니다.")

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

    pairs_with_rag_flag = [
        (
            si,
            r,
            _result_contains_style_code(r, si["style_code"]),
        )
        for si, r in paired
    ]

    hair_results: list[dict[str, Any]] = [
        {
            "style_name": si["style_name"],
            "style_code": si["style_code"],
            "retrieved_count": r.retrieved_count,
            "fallback_stage": r.fallback_stage,
            "has_rag_data": has_rag_data,
        }
        for si, r, has_rag_data in pairs_with_rag_flag
    ]

    # 요청한 style_code의 문서가 실제 검색 결과에 포함된 경우만 LLM 분석에 포함
    covered_pairs = [
        (si, r)
        for si, r, has_rag_data in pairs_with_rag_flag
        if has_rag_data
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
