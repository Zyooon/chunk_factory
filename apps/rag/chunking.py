from langchain_core.documents import Document


def _style_name(style) -> str:
    if isinstance(style, str):
        return style
    return style.get("style_name", "")


def _style_features(style) -> list[str]:
    if isinstance(style, str):
        return []
    return style.get("style_features", [])


def _format_style_list(styles: list, empty_msg: str) -> str:
    if not styles:
        return empty_msg
    lines = []
    for s in styles:
        name = _style_name(s)
        features = _style_features(s)
        lines.append(f"- {name}")
        if features:
            lines.append(f"  특징: {', '.join(features)}")
    return "\n".join(lines)


def build_documents_from_items(items: list[dict]) -> list[Document]:
    docs = []
    for i, item in enumerate(items, 1):
        category = item.get("category", "hair")
        gender = item.get("gender", "")
        conditions = item.get("conditions", {})
        face_shape = conditions.get("face_shape", "")
        face_proportion = conditions.get("face_proportion", "")

        recommended = item.get("recommended_styles", [])
        worst = item.get("worst_styles", [])
        reason_pos = item.get("expert_reasoning_positive", "")
        reason_neg = item.get("expert_reasoning_negative", "")

        style_names = ", ".join(
            _style_name(s) for s in recommended if _style_name(s)
        )

        rec_text = _format_style_list(recommended, "추천 스타일 정보 없음")
        worst_text = _format_style_list(worst, "확인된 비추천 스타일 없음")
        reason_neg_text = reason_neg if reason_neg else "확인된 비추천 이유 없음"

        content = (
            f"카테고리: {category}\n"
            f"대상 성별: {gender}\n"
            f"얼굴형 조건: {face_shape}\n"
            f"삼정 비율 조건: {face_proportion}\n"
            f"\n추천 스타일:\n{rec_text}\n"
            f"\n추천 이유:\n{reason_pos}\n"
            f"\n피해야 할 스타일:\n{worst_text}\n"
            f"\n비추천 이유:\n{reason_neg_text}"
        )

        metadata = {
            "category": category,
            "gender": gender,
            "face_shape": face_shape,
            "face_proportion": face_proportion,
            "style_names": style_names,
            "has_worst_style": len(worst) > 0,
            "doc_id": f"beauty_hair_{i:05d}",
        }

        docs.append(Document(page_content=content, metadata=metadata))

    return docs
