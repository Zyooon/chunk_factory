from __future__ import annotations

import re


NOISE_PATTERN = re.compile(
    r"^[ㄱ-ㅎㅏ-ㅣa-zA-Z\s]{1,4}$"
    r"|^[ㅋㄷㅎ]+$"
    r"|^\W+$"
)


def is_noise(message: str) -> bool:
    """
    LLM/RAG로 보낼 필요가 없는 무의미한 입력을 판별한다.
    """

    stripped = message.strip()

    if not stripped:
        return True

    if len(stripped) < 2:
        return True

    if NOISE_PATTERN.match(stripped):
        return True

    return False
