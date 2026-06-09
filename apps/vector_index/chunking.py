from typing import Any

from langchain_core.documents import Document


METADATA_DEFAULTS: dict[str, Any] = {
    "category": "정보 없음",
    "gender": "정보 없음",
    "face_shape": "정보 없음",
    "face_proportion": "정보 없음",
    "style_code": "정보 없음",
    "style_name": "정보 없음",
    "relation": "recommended",
    "source_type": "정보 없음",
    "confidence_level": "정보 없음",
    "reason_source": "정보 없음",
    "needs_reason_fill": False,
    "needs_review": False,
}


def _safe_text(value: Any, default: str = "정보 없음") -> str:
    """
    None, 빈 문자열, 빈 리스트 같은 값을 안전한 문자열로 변환한다.
    """
    if value is None:
        return default

    if isinstance(value, str):
        value = value.strip()
        return value if value else default

    return str(value)


def _safe_bool(value: Any, default: bool = False) -> bool:
    """
    metadata에 넣을 boolean 값을 안전하게 변환한다.
    """
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False

    return bool(value)


def _safe_list(value: Any) -> list:
    """
    값이 리스트가 아니거나 비어 있을 때도 오류가 나지 않도록 리스트로 변환한다.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _format_list(title: str, values: Any, empty_message: str) -> str:
    """
    배열 필드를 page_content에 적합한 bullet 텍스트로 변환한다.
    """
    items = _safe_list(values)

    if not items:
        return f"{title}:\n- {empty_message}"

    lines = [f"{title}:"]
    for item in items:
        lines.append(f"- {_safe_text(item, empty_message)}")

    return "\n".join(lines)


def build_page_content(item: dict) -> str:
    """
    JSON 객체 1개를 임베딩 대상 자연어 텍스트로 변환한다.

    새 done.json 스키마는 스타일 1개가 JSON 객체 1개로 저장되는 flat 구조다.
    따라서 추천/비추천 목록을 펼치지 않고, 단일 스타일의 조건과 설명 필드를
    자연어 문서로 구성한다.
    """
    category = _safe_text(item.get("category"))
    gender = _safe_text(item.get("gender"))
    face_shape = _safe_text(item.get("face_shape"))
    face_proportion = _safe_text(item.get("face_proportion"))

    style_code = _safe_text(item.get("style_code"))
    style_name = _safe_text(item.get("style_name"))
    relation = _safe_text(item.get("relation"), "recommended")

    reason_summary = _safe_text(
        item.get("reason_summary"),
        "확인된 한 줄 이유 없음",
    )
    reason_detail = _safe_text(
        item.get("reason_detail"),
        "확인된 상세 이유 없음",
    )

    style_features = _format_list(
        "스타일 특징",
        item.get("style_features"),
        "확인된 스타일 특징 없음",
    )
    styling_tips = _format_list(
        "스타일링 팁",
        item.get("styling_tips"),
        "확인된 스타일링 팁 없음",
    )
    cautions = _format_list(
        "주의사항",
        item.get("cautions"),
        "확인된 주의사항 없음",
    )
    good_variants = _format_list(
        "추천 변형",
        item.get("good_variants"),
        "확인된 추천 변형 없음",
    )
    avoid_variants = _format_list(
        "피하면 좋은 변형",
        item.get("avoid_variants"),
        "확인된 회피 변형 없음",
    )

    return f"""카테고리: {category}
대상 성별: {gender}
얼굴형 조건: {face_shape}
삼정 비율 조건: {face_proportion}

스타일 관계: {relation}
스타일 코드: {style_code}
스타일명: {style_name}

추천/비추천 이유 요약:
{reason_summary}

추천/비추천 이유 상세:
{reason_detail}

{style_features}

{styling_tips}

{cautions}

{good_variants}

{avoid_variants}
"""


def build_metadata(item: dict, idx: int) -> dict:
    """
    JSON 객체 1개를 ChromaDB metadata로 변환한다.

    metadata는 임베딩되지 않고 검색 필터링에 사용된다.
    따라서 list, dict 같은 복잡한 값은 넣지 않고
    문자열, 숫자, boolean 위주로 저장한다.
    """
    metadata = {
        "doc_id": f"beauty_doc_{idx + 1:05d}",
        "category": _safe_text(item.get("category"), METADATA_DEFAULTS["category"]),
        "gender": _safe_text(item.get("gender"), METADATA_DEFAULTS["gender"]),
        "face_shape": _safe_text(
            item.get("face_shape"),
            METADATA_DEFAULTS["face_shape"],
        ),
        "face_proportion": _safe_text(
            item.get("face_proportion"),
            METADATA_DEFAULTS["face_proportion"],
        ),
        "style_code": _safe_text(
            item.get("style_code"),
            METADATA_DEFAULTS["style_code"],
        ),
        "style_name": _safe_text(
            item.get("style_name"),
            METADATA_DEFAULTS["style_name"],
        ),
        "relation": _safe_text(
            item.get("relation"),
            METADATA_DEFAULTS["relation"],
        ),
        "source_type": _safe_text(
            item.get("source_type"),
            METADATA_DEFAULTS["source_type"],
        ),
        "confidence_level": _safe_text(
            item.get("confidence_level"),
            METADATA_DEFAULTS["confidence_level"],
        ),
        "reason_source": _safe_text(
            item.get("reason_source"),
            METADATA_DEFAULTS["reason_source"],
        ),
        "needs_reason_fill": _safe_bool(
            item.get("needs_reason_fill"),
            METADATA_DEFAULTS["needs_reason_fill"],
        ),
        "needs_review": _safe_bool(
            item.get("needs_review"),
            METADATA_DEFAULTS["needs_review"],
        ),
    }

    return metadata


def build_documents_from_items(items: list[dict]) -> list[Document]:
    """
    메인 함수.
    정제 JSON 객체 리스트를 LangChain Document 리스트로 변환한다.

    핵심 원칙:
    JSON 객체 1개 = Document 1개
    """
    documents: list[Document] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        page_content = build_page_content(item)
        metadata = build_metadata(item, idx)

        documents.append(
            Document(
                page_content=page_content,
                metadata=metadata,
            )
        )

    return documents
