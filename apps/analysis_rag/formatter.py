from typing import Any


def format_docs_for_prompt(docs: list[Any]) -> str:
    if not docs:
        return "검색된 근거 문서가 없습니다."

    blocks: list[str] = []

    for idx, doc in enumerate(docs, start=1):
        metadata = getattr(doc, "metadata", {}) or {}
        page_content = getattr(doc, "page_content", str(doc))

        blocks.append(
            "\n".join(
                [
                    f"[문서 {idx}]",
                    f"category: {metadata.get('category', '')}",
                    f"gender: {metadata.get('gender', '')}",
                    f"face_shape: {metadata.get('face_shape', '')}",
                    f"face_proportion: {metadata.get('face_proportion', '')}",
                    f"style_code: {metadata.get('style_code', '')}",
                    f"style_name: {metadata.get('style_name', '')}",
                    "",
                    page_content,
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)