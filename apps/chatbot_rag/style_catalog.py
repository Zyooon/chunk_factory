from __future__ import annotations


HAIR_STYLES_BY_GENDER = {
    "남성": [
        {"style_code": "m-01", "style_name": "버즈"},
        {"style_code": "m-02", "style_name": "하이앤타이트"},
        {"style_code": "m-03", "style_name": "아이비리그"},
        {"style_code": "m-04", "style_name": "크롭"},
        {"style_code": "m-05", "style_name": "드롭"},
        {"style_code": "m-06", "style_name": "슬릭"},
        {"style_code": "m-07", "style_name": "허밍"},
        {"style_code": "m-08", "style_name": "댄디"},
        {"style_code": "m-09", "style_name": "리프"},
        {"style_code": "m-10", "style_name": "퀴프"},
        {"style_code": "m-11", "style_name": "울프"},
        {"style_code": "m-12", "style_name": "애즈"},
        {"style_code": "m-13", "style_name": "시스루"},
        {"style_code": "m-14", "style_name": "쉐도우"},
        {"style_code": "m-15", "style_name": "베이비"},
        {"style_code": "m-16", "style_name": "포마드"},
        {"style_code": "m-17", "style_name": "히피"},
        {"style_code": "m-18", "style_name": "그런지"},
        {"style_code": "m-19", "style_name": "리젠트"},
    ],
    "여성": [
        {"style_code": "f-01", "style_name": "픽시"},
        {"style_code": "f-02", "style_name": "프리다"},
        {"style_code": "f-03", "style_name": "보브"},
        {"style_code": "f-04", "style_name": "태슬"},
        {"style_code": "f-05", "style_name": "원랭스"},
        {"style_code": "f-06", "style_name": "허그"},
        {"style_code": "f-07", "style_name": "빌드"},
        {"style_code": "f-08", "style_name": "레이어드"},
        {"style_code": "f-09", "style_name": "허쉬"},
        {"style_code": "f-10", "style_name": "샌드"},
        {"style_code": "f-11", "style_name": "샤기"},
        {"style_code": "f-12", "style_name": "울프"},
        {"style_code": "f-13", "style_name": "버드"},
        {"style_code": "f-14", "style_name": "히메"},
        {"style_code": "f-15", "style_name": "다이앤"},
        {"style_code": "f-16", "style_name": "레아"},
        {"style_code": "f-17", "style_name": "레인"},
        {"style_code": "f-18", "style_name": "그레이스"},
        {"style_code": "f-19", "style_name": "엘리자벳"},
        {"style_code": "f-20", "style_name": "페미닌"},
        {"style_code": "f-21", "style_name": "벌룬"},
        {"style_code": "f-22", "style_name": "코튼"},
        {"style_code": "f-23", "style_name": "발롱"},
        {"style_code": "f-24", "style_name": "구름"},
        {"style_code": "f-25", "style_name": "젤리"},
        {"style_code": "f-26", "style_name": "러플"},
        {"style_code": "f-27", "style_name": "바그"},
        {"style_code": "f-28", "style_name": "프릴"},
        {"style_code": "f-29", "style_name": "윈드"},
        {"style_code": "f-30", "style_name": "그런지"},
    ],
}


def get_hair_styles(gender: str | None = None) -> list[dict[str, str]]:
    """
    성별 기준 헤어스타일 목록을 반환한다.

    gender가 없으면 남성/여성 전체 스타일을 반환한다.
    """

    if gender in HAIR_STYLES_BY_GENDER:
        return HAIR_STYLES_BY_GENDER[gender]

    styles: list[dict[str, str]] = []

    for gender_styles in HAIR_STYLES_BY_GENDER.values():
        styles.extend(gender_styles)

    return styles


def find_hair_style_in_message(
    message: str,
    gender: str | None = None,
) -> dict[str, str] | None:
    """
    사용자 메시지에 포함된 헤어스타일을 찾는다.

    반환 예:
    {"style_code": "m-09", "style_name": "리프"}
    """

    normalized_message = message.strip().lower()

    if not normalized_message:
        return None

    for style in get_hair_styles(gender):
        style_name = style["style_name"].lower()

        if style_name in normalized_message:
            return style

    return None


def contains_hair_style(
    message: str,
    gender: str | None = None,
) -> bool:
    """
    사용자 메시지에 헤어스타일명이 포함되어 있는지 여부를 반환한다.
    """

    return find_hair_style_in_message(
        message=message,
        gender=gender,
    ) is not None