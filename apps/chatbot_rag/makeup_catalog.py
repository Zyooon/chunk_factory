from __future__ import annotations


MAKEUP_STYLES = [
    {
        "style_code": "mk-sp-peach",
        "style_name": "피치 메이크업",
        "makeup_group": "peach",
        "personal_color": "봄웜",
        "aliases": ["피치", "peach"],
    },
    {
        "style_code": "mk-sp-coral",
        "style_name": "코랄 메이크업",
        "makeup_group": "coral",
        "personal_color": "봄웜",
        "aliases": ["코랄", "coral"],
    },
    {
        "style_code": "mk-sp-juicy",
        "style_name": "주시 메이크업",
        "makeup_group": "juicy",
        "personal_color": "봄웜",
        "aliases": ["주시", "쥬시", "juicy"],
    },
    {
        "style_code": "mk-su-dewy",
        "style_name": "듀이 메이크업",
        "makeup_group": "dewy",
        "personal_color": "여름쿨",
        "aliases": ["듀이", "dewy"],
    },
    {
        "style_code": "mk-su-natural",
        "style_name": "내추럴 메이크업",
        "makeup_group": "natural",
        "personal_color": "여름쿨",
        "aliases": ["내추럴", "네추럴", "natural"],
    },
    {
        "style_code": "mk-su-rose",
        "style_name": "로즈 메이크업",
        "makeup_group": "rose",
        "personal_color": "여름쿨",
        "aliases": ["로즈", "rose"],
    },
    {
        "style_code": "mk-au-brown",
        "style_name": "브라운 메이크업",
        "makeup_group": "brown",
        "personal_color": "가을웜",
        "aliases": ["브라운", "brown"],
    },
    {
        "style_code": "mk-au-chic",
        "style_name": "시크 메이크업",
        "makeup_group": "chic",
        "personal_color": "가을웜",
        "aliases": ["시크", "chic"],
    },
    {
        "style_code": "mk-au-office",
        "style_name": "오피스 메이크업",
        "makeup_group": "office",
        "personal_color": "가을웜",
        "aliases": ["오피스", "office"],
    },
    {
        "style_code": "mk-wi-burgundy",
        "style_name": "버건디 메이크업",
        "makeup_group": "burgundy",
        "personal_color": "겨울쿨",
        "aliases": ["버건디", "burgundy"],
    },
    {
        "style_code": "mk-wi-glam",
        "style_name": "글램 메이크업",
        "makeup_group": "glam",
        "personal_color": "겨울쿨",
        "aliases": ["글램", "glam"],
    },
    {
        "style_code": "mk-wi-red",
        "style_name": "레드 메이크업",
        "makeup_group": "red",
        "personal_color": "겨울쿨",
        "aliases": ["레드", "red"],
    },
]


def get_makeup_styles(personal_color: str | None = None) -> list[dict[str, str]]:
    """
    퍼스널컬러 기준 메이크업 스타일 목록을 반환한다.

    personal_color가 없으면 전체 메이크업 스타일을 반환한다.
    """
    if not personal_color:
        return MAKEUP_STYLES

    return [
        style
        for style in MAKEUP_STYLES
        if style.get("personal_color") == personal_color
    ]


def find_makeup_style_in_message(
    message: str,
    personal_color: str | None = None,
) -> dict[str, str] | None:
    """
    사용자 메시지에 포함된 메이크업 스타일을 찾는다.

    반환 예:
    {
        "style_code": "mk-sp-peach",
        "style_name": "피치 메이크업",
        "makeup_group": "peach",
        "personal_color": "봄웜",
    }
    """
    normalized_message = message.strip().lower()

    if not normalized_message:
        return None

    for style in get_makeup_styles(personal_color):
        style_name = style["style_name"].lower()
        aliases = [alias.lower() for alias in style.get("aliases", [])]

        if style_name in normalized_message:
            return {
                "style_code": style["style_code"],
                "style_name": style["style_name"],
                "makeup_group": style["makeup_group"],
                "personal_color": style["personal_color"],
            }

        if any(alias in normalized_message for alias in aliases):
            return {
                "style_code": style["style_code"],
                "style_name": style["style_name"],
                "makeup_group": style["makeup_group"],
                "personal_color": style["personal_color"],
            }

    return None


def contains_makeup_style(
    message: str,
    personal_color: str | None = None,
) -> bool:
    """
    사용자 메시지에 메이크업 스타일명이 포함되어 있는지 여부를 반환한다.
    """
    return find_makeup_style_in_message(
        message=message,
        personal_color=personal_color,
    ) is not None
