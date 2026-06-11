from __future__ import annotations

import re


KOREAN_JAMO_PATTERN = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]+")
SHORT_ALPHA_PATTERN = re.compile(r"[a-z]{1,4}")
SYMBOL_PATTERN = re.compile(r"[\s\W]+")
LAUGHTER_PATTERN = re.compile(r"[ㅋㅎㅠㅜ]{2,}")
REPEATED_SHORT_PATTERN = re.compile(r"(.+)\1{1,}")


def is_noise(message: str) -> bool:
    """
    LLM/RAG로 보낼 필요가 없는 무의미한 입력을 판별한다.

    정상 한국어 문장을 noise로 오판하지 않도록 짧은 입력에만 보수적으로 적용한다.
    """

    stripped = message.strip()

    if not stripped:
        return True

    if len(stripped) <= 1:
        return True

    if len(stripped) <= 6 and KOREAN_JAMO_PATTERN.fullmatch(stripped):
        return True

    if SHORT_ALPHA_PATTERN.fullmatch(stripped.lower()):
        return True

    if len(stripped) <= 8 and LAUGHTER_PATTERN.fullmatch(stripped):
        return True

    if len(stripped) <= 8 and REPEATED_SHORT_PATTERN.fullmatch(stripped):
        return True

    if len(stripped) <= 6 and SYMBOL_PATTERN.fullmatch(stripped):
        return True

    return False
