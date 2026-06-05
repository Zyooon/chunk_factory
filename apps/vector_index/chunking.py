from typing import Any

from langchain_core.documents import Document


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


def _safe_list(value: Any) -> list:
    """
    값이 리스트가 아니거나 비어 있을 때도 오류가 나지 않도록 리스트로 변환한다.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def format_styles(styles: list, empty_message: str) -> str:
    """
    추천 스타일 또는 비추천 스타일 목록을 page_content에 들어갈 자연어 텍스트로 변환한다.

    처리 가능한 형태:
    1. 문자열 배열
       ["리프", "울프"]

    2. 객체 배열
       [
           {
               "style_name": "리프",
               "style_group": "m-10",
               "style_features": ["비대칭 가르마", "정수리 볼륨"]
           }
       ]
    """
    styles = _safe_list(styles)

    if not styles:
        return empty_message

    lines: list[str] = []

    for style in styles:
        if isinstance(style, str):
            style_name = _safe_text(style, "스타일명 정보 없음")
            lines.append(f"- {style_name}")
            continue

        if isinstance(style, dict):
            style_name = _safe_text(
                style.get("style_name"),
                "스타일명 정보 없음",
            )

            style_group = _safe_text(
                style.get("style_group"),
                "스타일 그룹 정보 없음",
            )

            style_features = _safe_list(style.get("style_features"))

            if style_features:
                feature_text = ", ".join(
                    _safe_text(feature, "특징 정보 없음")
                    for feature in style_features
                )
            else:
                feature_text = "특징 정보 없음"

            lines.append(f"- {style_name}")
            lines.append(f"  스타일 그룹: {style_group}")
            lines.append(f"  특징: {feature_text}")
            continue

        lines.append(f"- {_safe_text(style, '스타일명 정보 없음')}")

    return "\n".join(lines)


def extract_style_names(styles: list) -> str:
    """
    metadata에 저장할 스타일명만 추출한다.

    Chroma metadata에는 list나 dict를 넣지 않는 것이 안전하므로,
    스타일명들을 ',' 로 합친 문자열로 반환한다.

    출력 : "울프컷, 리프컷"

    """
    styles = _safe_list(styles)

    if not styles:
        return ""

    names: list[str] = []

    for style in styles:
        if isinstance(style, str):
            name = style.strip()
            if name:
                names.append(name)
            continue

        if isinstance(style, dict):
            name = _safe_text(style.get("style_name"), "")
            if name:
                names.append(name)
            continue

    return ", ".join(names)

def extract_style_groups(styles: list) -> str:
    """
    metadata에 저장할 스타일 그룹 코드만 추출한다.

    Chroma metadata에는 list나 dict를 넣지 않는 것이 안전하므로,
    그룹 코드들을 콤마로 합친 문자열로 반환한다.

    출력 : "M-09, M-06"
    """
    styles = _safe_list(styles)

    if not styles:
        return ""

    groups: list[str] = []

    for style in styles:
        if isinstance(style, dict):
            group = _safe_text(style.get("style_group"), "")
            if group:
                groups.append(group)

    return ", ".join(groups)

def build_page_content(item: dict) -> str:
    """
    JSON 객체 1개를 임베딩 대상 자연어 텍스트로 변환한다.

    이 함수의 반환값이 Document.page_content에 들어가며,
    실제 임베딩되는 내용이다.
    """
    category = _safe_text(item.get("category"))
    gender = _safe_text(item.get("gender"))

    conditions = item.get("conditions") or {}
    if not isinstance(conditions, dict):
        conditions = {}

    face_shape = _safe_text(conditions.get("face_shape"))
    face_proportion = _safe_text(conditions.get("face_proportion"))

    recommended_styles = item.get("recommended_styles") or []
    worst_styles = item.get("worst_styles") or []

    positive_reason = _safe_text(
        item.get("expert_reasoning_positive"),
        "확인된 추천 이유 없음",
    )
    negative_reason = _safe_text(
        item.get("expert_reasoning_negative"),
        "확인된 비추천 이유 없음",
    )

    recommended_text = format_styles(
        recommended_styles,
        "추천 스타일 정보 없음",
    )
    worst_text = format_styles(
        worst_styles,
        "확인된 비추천 스타일 없음",
    )

    return f"""카테고리: {category}
대상 성별: {gender}
얼굴형 조건: {face_shape}
삼정 비율 조건: {face_proportion}

추천 스타일:
{recommended_text}

추천 이유:
{positive_reason}

피해야 할 스타일:
{worst_text}

비추천 이유:
{negative_reason}
"""


def build_metadata(item: dict, idx: int) -> dict:
    """
    JSON 객체 1개를 ChromaDB metadata로 변환한다.

    metadata는 임베딩되지 않고 검색 필터링에 사용된다.
    따라서 list, dict 같은 복잡한 값은 넣지 않고
    문자열, 숫자, boolean 위주로 저장한다.
    """
    category = _safe_text(item.get("category"))
    gender = _safe_text(item.get("gender"))

    conditions = item.get("conditions") or {}
    if not isinstance(conditions, dict):
        conditions = {}

    face_shape = _safe_text(conditions.get("face_shape"))
    face_proportion = _safe_text(conditions.get("face_proportion"))

    recommended_styles = item.get("recommended_styles") or []
    worst_styles = item.get("worst_styles") or []

    style_names = extract_style_names(recommended_styles)
    style_groups = extract_style_groups(recommended_styles)

    worst_style_names = extract_style_names(worst_styles)
    worst_style_groups = extract_style_groups(worst_styles)

    has_worst_style = len(_safe_list(worst_styles)) > 0

    return {
        "doc_id": f"beauty_doc_{idx + 1:05d}",
        "category": category,
        "gender": gender,
        "face_shape": face_shape,
        "face_proportion": face_proportion,
        "style_names": style_names,
        "style_groups": style_groups,
        "worst_style_names": worst_style_names,
        "worst_style_groups": worst_style_groups,
        "has_worst_style": has_worst_style,
    }


def build_documents_from_items(items: list[dict]) -> list[Document]:
    """
    메인 함수
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