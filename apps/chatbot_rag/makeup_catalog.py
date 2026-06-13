from __future__ import annotations


MAKEUP_STYLES = [
    {
        "style_code": "mk-sp-peach",
        "style_name": "피치 메이크업",
        "makeup_group": "peach",
        "personal_color": "봄웜",
        "gender": "여성",
        "aliases": ["피치", "peach"],
    },
    {
        "style_code": "mk-sp-coral",
        "style_name": "코랄 메이크업",
        "makeup_group": "coral",
        "personal_color": "봄웜",
        "gender": "여성",
        "aliases": ["코랄", "coral"],
    },
    {
        "style_code": "mk-sp-juicy",
        "style_name": "주시 메이크업",
        "makeup_group": "juicy",
        "personal_color": "봄웜",
        "gender": "여성",
        "aliases": ["주시", "쥬시", "juicy"],
    },
    {
        "style_code": "mk-su-dewy",
        "style_name": "듀이 메이크업",
        "makeup_group": "dewy",
        "personal_color": "여름쿨",
        "gender": "여성",
        "aliases": ["듀이", "dewy"],
    },
    {
        "style_code": "mk-su-natural",
        "style_name": "내추럴 메이크업",
        "makeup_group": "natural",
        "personal_color": "여름쿨",
        "gender": "여성",
        "aliases": ["내추럴", "네추럴", "natural"],
    },
    {
        "style_code": "mk-su-rose",
        "style_name": "로즈 메이크업",
        "makeup_group": "rose",
        "personal_color": "여름쿨",
        "gender": "여성",
        "aliases": ["로즈", "rose"],
    },
    {
        "style_code": "mk-au-brown",
        "style_name": "브라운 메이크업",
        "makeup_group": "brown",
        "personal_color": "가을웜",
        "gender": "여성",
        "aliases": ["브라운", "brown"],
    },
    {
        "style_code": "mk-au-chic",
        "style_name": "시크 메이크업",
        "makeup_group": "chic",
        "personal_color": "가을웜",
        "gender": "여성",
        "aliases": ["시크", "chic"],
    },
    {
        "style_code": "mk-au-office",
        "style_name": "오피스 메이크업",
        "makeup_group": "office",
        "personal_color": "가을웜",
        "gender": "여성",
        "aliases": ["오피스", "office"],
    },
    {
        "style_code": "mk-wi-burgundy",
        "style_name": "버건디 메이크업",
        "makeup_group": "burgundy",
        "personal_color": "겨울쿨",
        "gender": "여성",
        "aliases": ["버건디", "burgundy"],
    },
    {
        "style_code": "mk-wi-glam",
        "style_name": "글램 메이크업",
        "makeup_group": "glam",
        "personal_color": "겨울쿨",
        "gender": "여성",
        "aliases": ["글램", "glam"],
    },
    {
        "style_code": "mk-wi-red",
        "style_name": "레드 메이크업",
        "makeup_group": "red",
        "personal_color": "겨울쿨",
        "gender": "여성",
        "aliases": ["레드", "red"],
    },
    {
        "style_code": "mk-m-sp-natural",
        "style_name": "봄웜 내추럴 메이크업",
        "makeup_group": "male_spring_natural",
        "personal_color": "봄웜",
        "gender": "남성",
        "aliases": ["봄웜 내추럴", "남성 내추럴", "내추럴 그루밍"],
    },
    {
        "style_code": "mk-m-su-clean",
        "style_name": "여름쿨 클린 메이크업",
        "makeup_group": "male_summer_clean",
        "personal_color": "여름쿨",
        "gender": "남성",
        "aliases": ["여름쿨 클린", "남성 클린", "클린 그루밍"],
    },
    {
        "style_code": "mk-m-au-soft",
        "style_name": "가을웜 소프트 메이크업",
        "makeup_group": "male_autumn_soft",
        "personal_color": "가을웜",
        "gender": "남성",
        "aliases": ["가을웜 소프트", "남성 소프트", "소프트 그루밍"],
    },
    {
        "style_code": "mk-m-wi-sharp",
        "style_name": "겨울쿨 샤프 메이크업",
        "makeup_group": "male_winter_sharp",
        "personal_color": "겨울쿨",
        "gender": "남성",
        "aliases": ["겨울쿨 샤프", "남성 샤프", "샤프 그루밍"],
    },
]


def get_makeup_styles(
    personal_color: str | None = None,
    gender: str | None = None,
) -> list[dict[str, str]]:
    """
    퍼스널컬러/성별 기준 메이크업 스타일 목록을 반환한다.

    personal_color, gender 모두 없으면 전체 반환한다.
    """
    result = MAKEUP_STYLES

    if personal_color:
        result = [s for s in result if s.get("personal_color") == personal_color]

    if gender:
        result = [s for s in result if s.get("gender") == gender]

    return result


def find_makeup_style_in_message(
    message: str,
    personal_color: str | None = None,
    gender: str | None = None,
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

    for style in get_makeup_styles(personal_color, gender):
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
    gender: str | None = None,
) -> bool:
    """
    사용자 메시지에 메이크업 스타일명이 포함되어 있는지 여부를 반환한다.
    """
    return find_makeup_style_in_message(
        message=message,
        personal_color=personal_color,
        gender=gender,
    ) is not None
