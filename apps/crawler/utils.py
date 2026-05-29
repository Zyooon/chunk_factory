import random
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from apps.crawler.config import REQUEST_DELAY_MAX, REQUEST_DELAY_MIN


# ============================================================
# utils.py
# ------------------------------------------------------------
# 크롤러 앱 전체에서 재사용할 공통 유틸 함수 모음입니다.
#
# 여기에는 다음과 같은 기능을 둡니다.
# - 텍스트 공백 정리
# - 파일명 안전 처리
# - 현재 수집 시각 생성
# - 요청 간 랜덤 대기
# ============================================================


def normalize_whitespace(text: str) -> str:
    """
    텍스트 안의 불필요한 공백과 줄바꿈을 정리합니다.

    크롤링한 HTML 본문은 보통 줄바꿈, 탭, 여러 칸 공백이 섞여 있습니다.
    이 함수는 그런 텍스트를 RAG 전처리에 넣기 좋은 형태로 정리합니다.

    Args:
        text:
            정리할 원본 텍스트입니다.

    Returns:
        정리된 텍스트입니다.

    Example:
        "안녕\\n\\n  하세요\\t반갑습니다"
        → "안녕 하세요 반갑습니다"
    """
    if not text:
        return ""

    # 모든 연속 공백, 줄바꿈, 탭을 공백 하나로 변경합니다.
    cleaned_text = re.sub(r"\s+", " ", text)

    # 앞뒤 공백을 제거합니다.
    return cleaned_text.strip()


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """
    문자열을 Windows 파일명으로 안전하게 사용할 수 있게 정리합니다.

    Windows 파일명에는 아래 문자를 사용할 수 없습니다.
    \\ / : * ? " < > |

    또한 제목이 너무 길면 파일 경로 제한 문제나 가독성 문제가 생기므로
    기본적으로 80자까지만 사용합니다.

    Args:
        title:
            파일명으로 사용할 원본 제목입니다.

        max_length:
            파일명 최대 길이입니다.

    Returns:
        안전하게 정리된 파일명 문자열입니다.

    Example:
        "올리브영 추천템: 선크림/쿠션?"
        → "올리브영 추천템_ 선크림_쿠션"
    """
    if not title:
        return "untitled"

    # Windows 파일명 금지 문자를 밑줄로 치환합니다.
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)

    # 줄바꿈/탭/연속 공백을 공백 하나로 정리합니다.
    safe_title = normalize_whitespace(safe_title)

    # 파일명 양끝의 점/공백은 Windows에서 문제를 만들 수 있어 제거합니다.
    safe_title = safe_title.strip(" .")

    # 너무 긴 제목은 잘라냅니다.
    safe_title = safe_title[:max_length].strip()

    return safe_title or "untitled"


def get_collected_at() -> str:
    """
    현재 수집 시각을 한국 시간 기준 ISO 문자열로 반환합니다.

    Returns:
        예: "2026-05-28T14:30:00+09:00"
    """
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    return now.isoformat(timespec="seconds")


def polite_sleep() -> None:
    """
    크롤링 요청 사이에 2~3초 랜덤 대기합니다.

    너무 빠른 연속 요청은 대상 서버에 부담을 줄 수 있고,
    차단 가능성도 높아집니다.

    실제 대기 범위는 config.py의
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX 값을 사용합니다.
    """
    delay_seconds = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    print(f"Waiting {delay_seconds:.2f} seconds before next request...")
    time.sleep(delay_seconds)