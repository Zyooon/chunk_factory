from __future__ import annotations

from typing import Any

from apps.rag_core.retriever import retrieve_many_docs
from apps.rag_core.generator import generate_analysis_answer
from apps.rag_core.schemas import AnalysisGenerationInput, RetrievalQuery, RetrievalResult


CATEGORY_HAIR = "hair"
CATEGORY_MAKEUP = "makeup"


def _result_contains_style_code(
    retrieval_result: RetrievalResult,
    style_code: str,
) -> bool:
    """
    검색 결과 안에 요청한 style_code 문서가 실제로 포함되어 있는지 확인한다.

    fallback 검색은 후순위 단계에서 category 같은 넓은 조건만으로도 결과를
    반환할 수 있으므로, retrieved_count만으로는 해당 스타일의 RAG 데이터가
    있다고 판단하기 어렵다.
    """
    for document in retrieval_result.documents:
        metadata = document.metadata or {}
        if metadata.get("style_code") == style_code:
            return True

    return False


def _validate_style(style: dict[str, Any], label: str) -> tuple[str, str]:
    """
    추천 스타일 객체에서 style_name, style_code를 검증하고 반환한다.
    """
    style_name = style.get("style_name")
    style_code = style.get("style_code")

    if not style_name or not style_code:
        raise ValueError(f"{label}에는 style_name과 style_code가 필요합니다.")

    return str(style_name), str(style_code)


def _build_hair_retrieval_queries(
    *,
    gender: str,
    face_shape: str,
    face_proportion: str,
    recommended_hair_styles: list[dict[str, Any]],
) -> tuple[list[RetrievalQuery], list[dict[str, Any]]]:
    """
    추천 헤어스타일 목록을 hair RetrievalQuery 목록으로 변환한다.
    """
    retrieval_queries: list[RetrievalQuery] = []
    style_infos: list[dict[str, Any]] = []

    for style in recommended_hair_styles:
        style_name, style_code = _validate_style(style, "추천 헤어스타일")

        query = (
            f"{gender} {face_shape} 얼굴형 {face_proportion} 삼정 비율에 "
            f"{style_name} 스타일이 어울리는 이유"
        )

        retrieval_queries.append(
            RetrievalQuery(
                query=query,
                category=CATEGORY_HAIR,
                gender=gender,
                face_shape=face_shape,
                face_proportion=face_proportion,
                style_code=style_code,
                k=3,
            )
        )
        style_infos.append(
            {
                "style_name": style_name,
                "style_code": style_code,
            }
        )

    return retrieval_queries, style_infos


def _build_makeup_retrieval_queries(
    *,
    gender: str,
    personal_color: str,
    recommended_makeup_styles: list[dict[str, Any]],
) -> tuple[list[RetrievalQuery], list[dict[str, Any]]]:
    """
    추천 메이크업 목록을 makeup RetrievalQuery 목록으로 변환한다.

    메이크업 검색은 얼굴형/삼정 비율을 사용하지 않고,
    gender + personal_color + style_code/makeup_group을 사용한다.
    """
    retrieval_queries: list[RetrievalQuery] = []
    style_infos: list[dict[str, Any]] = []

    for style in recommended_makeup_styles:
        style_name, style_code = _validate_style(style, "추천 메이크업")
        makeup_group = style.get("makeup_group")

        query = (
            f"{gender} {personal_color} 퍼스널컬러에 "
            f"{style_name}이 어울리는 이유"
        )

        retrieval_queries.append(
            RetrievalQuery(
                query=query,
                category=CATEGORY_MAKEUP,
                gender=gender,
                personal_color=personal_color,
                makeup_group=str(makeup_group) if makeup_group else None,
                style_code=style_code,
                k=3,
            )
        )
        style_infos.append(
            {
                "style_name": style_name,
                "style_code": style_code,
                "personal_color": personal_color,
                "makeup_group": str(makeup_group) if makeup_group else None,
            }
        )

    return retrieval_queries, style_infos


def _build_recommendation_results(
    style_infos: list[dict[str, Any]],
    retrieval_results: list[RetrievalResult],
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], RetrievalResult]]]:
    """
    스타일 정보와 검색 결과를 프론트 반환용 추천 결과로 묶는다.

    요청한 style_code가 검색 결과에 실제 포함된 경우만 covered_pairs에 넣는다.
    """
    paired = list(zip(style_infos, retrieval_results))

    pairs_with_rag_flag = [
        (
            style_info,
            retrieval_result,
            _result_contains_style_code(
                retrieval_result,
                style_info["style_code"],
            ),
        )
        for style_info, retrieval_result in paired
    ]

    recommendation_results: list[dict[str, Any]] = []
    covered_pairs: list[tuple[dict[str, Any], RetrievalResult]] = []

    for style_info, retrieval_result, has_rag_data in pairs_with_rag_flag:
        result = {
            "style_name": style_info["style_name"],
            "style_code": style_info["style_code"],
            "retrieved_count": retrieval_result.retrieved_count,
            "fallback_stage": retrieval_result.fallback_stage,
            "has_rag_data": has_rag_data,
        }

        if "personal_color" in style_info:
            result["personal_color"] = style_info.get("personal_color")

        if "makeup_group" in style_info:
            result["makeup_group"] = style_info.get("makeup_group")

        recommendation_results.append(result)

        if has_rag_data:
            covered_pairs.append((style_info, retrieval_result))

    return recommendation_results, covered_pairs


def _generate_hair_analysis_summary(
    *,
    gender: str,
    face_shape: str,
    face_proportion: str,
    personal_color: str | None,
    covered_hair_pairs: list[tuple[dict[str, Any], RetrievalResult]],
) -> str:
    """
    헤어 전용 분석 문장을 생성한다.
    """
    if not covered_hair_pairs:
        return "선택한 헤어스타일에 대한 분석 데이터가 없습니다."

    generation_input = AnalysisGenerationInput(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        personal_color=personal_color,
        recommended_styles=[
            {
                "style_name": style_info["style_name"],
                "style_code": style_info["style_code"],
                "retrieved_count": retrieval_result.retrieved_count,
                "fallback_stage": retrieval_result.fallback_stage,
            }
            for style_info, retrieval_result in covered_hair_pairs
        ],
        recommended_hair_styles=[
            style_info for style_info, _ in covered_hair_pairs
        ],
        recommended_makeup_styles=[],
        retrieval_results=[
            retrieval_result for _, retrieval_result in covered_hair_pairs
        ],
    )

    return generate_analysis_answer(generation_input).answer


def _generate_makeup_analysis_summary(
    *,
    gender: str,
    face_shape: str,
    face_proportion: str,
    personal_color: str | None,
    covered_makeup_pairs: list[tuple[dict[str, Any], RetrievalResult]],
) -> str | None:
    """
    메이크업 전용 분석 문장을 생성한다.
    """
    if not covered_makeup_pairs:
        return None

    generation_input = AnalysisGenerationInput(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        personal_color=personal_color,
        recommended_styles=[
            {
                "style_name": style_info["style_name"],
                "style_code": style_info["style_code"],
                "personal_color": style_info.get("personal_color"),
                "makeup_group": style_info.get("makeup_group"),
                "retrieved_count": retrieval_result.retrieved_count,
                "fallback_stage": retrieval_result.fallback_stage,
            }
            for style_info, retrieval_result in covered_makeup_pairs
        ],
        recommended_hair_styles=[],
        recommended_makeup_styles=[
            style_info for style_info, _ in covered_makeup_pairs
        ],
        retrieval_results=[
            retrieval_result for _, retrieval_result in covered_makeup_pairs
        ],
    )

    return generate_analysis_answer(generation_input).answer


def generate_analysis_result(
    gender: str,
    face_shape: str,
    face_proportion: str,
    recommended_hair_styles: list[dict[str, Any]],
    personal_color: str | None = None,
    recommended_makeup_styles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    최초 분석 결과를 생성한다.

    추천 자체는 이 함수에서 만들지 않는다.
    이미 알고리즘이 추천한 hair/makeup 목록에 대해 RAG 근거를 검색하고,
    프론트에서 사용할 수 있는 결과 구조로 반환한다.

    헤어 분석 결과와 메이크업 분석 결과는 서로 다른 결과로 분리해 반환한다.
    """
    if not recommended_hair_styles:
        raise ValueError("recommended_hair_styles는 비어 있을 수 없습니다.")

    recommended_makeup_styles = recommended_makeup_styles or []

    if recommended_makeup_styles and not personal_color:
        raise ValueError(
            "recommended_makeup_styles가 있으면 personal_color가 필요합니다."
        )

    hair_queries, hair_style_infos = _build_hair_retrieval_queries(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        recommended_hair_styles=recommended_hair_styles,
    )

    makeup_queries: list[RetrievalQuery] = []
    makeup_style_infos: list[dict[str, Any]] = []
    if recommended_makeup_styles and personal_color:
        makeup_queries, makeup_style_infos = _build_makeup_retrieval_queries(
            gender=gender,
            personal_color=personal_color,
            recommended_makeup_styles=recommended_makeup_styles,
        )

    retrieval_queries = hair_queries + makeup_queries
    retrieval_results = retrieve_many_docs(retrieval_queries)

    hair_retrieval_results = retrieval_results[: len(hair_queries)]
    makeup_retrieval_results = retrieval_results[len(hair_queries) :]

    hair_results, covered_hair_pairs = _build_recommendation_results(
        hair_style_infos,
        hair_retrieval_results,
    )
    makeup_results, covered_makeup_pairs = _build_recommendation_results(
        makeup_style_infos,
        makeup_retrieval_results,
    )

    hair_analysis_summary = _generate_hair_analysis_summary(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        personal_color=personal_color,
        covered_hair_pairs=covered_hair_pairs,
    )
    makeup_analysis_summary = _generate_makeup_analysis_summary(
        gender=gender,
        face_shape=face_shape,
        face_proportion=face_proportion,
        personal_color=personal_color,
        covered_makeup_pairs=covered_makeup_pairs,
    )

    hair_docs_count = sum(r.retrieved_count for r in hair_retrieval_results)
    makeup_docs_count = sum(r.retrieved_count for r in makeup_retrieval_results)

    return {
        # 기존 클라이언트 호환용. 신규 클라이언트는 hair_analysis_summary 사용 권장.
        "analysis_summary": hair_analysis_summary,
        "hair_analysis_summary": hair_analysis_summary,
        "makeup_analysis_summary": makeup_analysis_summary,
        "hair_recommendations": hair_results,
        "makeup_recommendations": makeup_results,
        "cautions": [
            "현재 결과는 확보된 RAG 데이터 기준으로 생성되었습니다.",
            "검색 근거가 부족한 스타일은 단정하지 않고 보수적으로 설명합니다.",
        ],
        "retrieval_info": {
            "hair_docs": hair_docs_count,
            "makeup_docs": makeup_docs_count,
            "hair_fallback_stages": [
                result.fallback_stage for result in hair_retrieval_results
            ],
            "makeup_fallback_stages": [
                result.fallback_stage for result in makeup_retrieval_results
            ],
            "fallback_stages": [
                result.fallback_stage for result in retrieval_results
            ],
        },
    }
