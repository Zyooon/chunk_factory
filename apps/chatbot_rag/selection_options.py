from __future__ import annotations

MOOD_OPTIONS = [
    {
        "id": "neat_trustworthy",
        "label": "단정하고 신뢰감 있는 느낌",
        "mood_keywords": ["단정함", "신뢰감", "깔끔함"],
    },
    {
        "id": "soft_comfortable",
        "label": "부드럽고 편안한 느낌",
        "mood_keywords": ["부드러움", "편안함", "자연스러움"],
    },
    {
        "id": "stylish_clean",
        "label": "세련되고 깔끔한 느낌",
        "mood_keywords": ["세련됨", "깔끔함", "정돈됨"],
    },
    {
        "id": "natural_effortless",
        "label": "자연스럽고 꾸미지 않은 느낌",
        "mood_keywords": ["자연스러움", "내추럴", "담백함"],
    },
]


def get_mood_option_by_id(option_id: str | None) -> dict | None:
    if not option_id:
        return None

    for option in MOOD_OPTIONS:
        if option["id"] == option_id:
            return option

    return None


def build_mood_selection_title() -> str:
    return "추천받은 스타일을 어떤 분위기로 가져가고 싶으신가요?"
