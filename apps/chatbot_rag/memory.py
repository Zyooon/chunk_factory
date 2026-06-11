from __future__ import annotations

from typing import Any


DEFAULT_MAX_HISTORY_MESSAGES = 10


def trim_chat_history(
    chat_history: list[dict[str, str]] | None,
    max_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
) -> list[dict[str, str]]:
    """
    최근 대화 기록 max_messages개만 유지한다.

    chat_history는 아래 형태를 기준으로 한다.
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ]
    """

    if not chat_history:
        return []

    return list(chat_history)[-max_messages:]


def append_chat_history(
    chat_history: list[dict[str, str]] | None,
    user_message: str,
    assistant_answer: str,
    max_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
) -> list[dict[str, str]]:
    """
    현재 사용자 메시지와 assistant 답변을 chat_history에 추가한다.
    """

    updated_history = list(chat_history or [])

    if user_message:
        updated_history.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

    if assistant_answer:
        updated_history.append(
            {
                "role": "assistant",
                "content": assistant_answer,
            }
        )

    return trim_chat_history(
        updated_history,
        max_messages=max_messages,
    )


def extract_simple_user_preferences(
    user_message: str,
) -> dict[str, Any]:
    """
    사용자 메시지에서 간단한 취향 정보를 추출한다.

    초기 구현에서는 LLM을 사용하지 않고 keyword 기반으로만 처리한다.
    추후 DB 저장 또는 요약 모델을 붙일 수 있다.
    """

    preferences: dict[str, Any] = {}

    message = user_message.strip()

    if not message:
        return preferences

    if any(keyword in message for keyword in ["손질 오래", "손질 많이", "귀찮", "바빠", "시간 없어"]):
        preferences["prefers_easy_styling"] = True

    if any(keyword in message for keyword in ["짧은 머리", "짧게", "짧은 스타일"]):
        preferences["prefers_short_style"] = True

    if any(keyword in message for keyword in ["긴 머리", "길게", "긴 스타일"]):
        preferences["prefers_long_style"] = True

    if any(keyword in message for keyword in ["앞머리 싫", "이마 보이", "이마 드러"]):
        preferences["prefers_forehead_exposed"] = True

    if any(keyword in message for keyword in ["앞머리 있", "이마 가리", "이마 덮"]):
        preferences["prefers_bangs"] = True

    if any(keyword in message for keyword in ["단정", "깔끔", "회사", "면접", "직장"]):
        preferences["prefers_neat_style"] = True

    if any(keyword in message for keyword in ["힙", "개성", "트렌디", "튀는", "유니크"]):
        preferences["prefers_trendy_style"] = True

    return preferences

def clear_pending_selection(user_profile: dict[str, Any]) -> dict[str, Any]:
    updated_profile = dict(user_profile)

    updated_profile.pop("pending_selection", None)

    return updated_profile


def merge_user_profile(
    user_profile: dict[str, Any] | None,
    new_preferences: dict[str, Any],
) -> dict[str, Any]:
    """
    기존 user_profile에 새로 추출한 취향 정보를 병합한다.

    같은 key가 있으면 최신 값을 우선한다.
    """

    merged = dict(user_profile)

    for key, value in new_preferences.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value

    return merged