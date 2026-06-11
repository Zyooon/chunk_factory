from __future__ import annotations

import re


def is_noise(message: str) -> bool:
    """
    LLM/RAG로 보낼 필요가 없는 무의미한 입력을 판별한다.
    """

    stripped = message.strip()
    if len(stripped) <= 1:
        return True
    if re.fullmatch(r"[ㄱ-ㅎㅏ-ㅣ]+", stripped):
        return True
    if re.fullmatch(r"[a-z]{1,4}", stripped):
        return True
    if re.search(r"(.)\1", stripped):
        return True
    if re.fullmatch(r"[\s\W]+", stripped):
        return True
    return False
