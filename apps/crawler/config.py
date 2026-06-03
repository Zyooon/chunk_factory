import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# config.py
# ------------------------------------------------------------
# crawler 앱 전체 설정값을 관리하는 파일입니다.
#
# 이번 버전에서는 네이버 블로그 검색 기반 수집을 지원합니다.
# 즉, 개별 블로그 URL을 몰라도 키워드만 넣으면 검색 결과에서
# 블로그 글 URL을 찾아 수집합니다.
# ============================================================


# 현재 파일:
# chunk_factory/apps/crawler/config.py
CURRENT_FILE = Path(__file__).resolve()

# 프로젝트 루트:
# chunk_factory/
BASE_DIR = CURRENT_FILE.parents[2]

# .env 파일 로드
load_dotenv(BASE_DIR / ".env")

# YouTube Data API Key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


# ------------------------------------------------------------
# 저장 경로 설정
# ------------------------------------------------------------

OUTPUT_DIR = BASE_DIR / "data" / "crawled"

NAVER_BLOG_OUTPUT_DIR = OUTPUT_DIR / "naver"

YOUTUBE_OUTPUT_DIR = OUTPUT_DIR / "youtube"

# ------------------------------------------------------------
# 통합 키워드 파일 경로
# ------------------------------------------------------------
KEYWORDS_FILE = BASE_DIR / "data" / "config" / "keywords.txt"


def load_shared_keywords() -> list[str]:
    """
    data/config/keywords.txt 에서 공통 키워드 목록을 로드합니다.

    - 앞뒤 공백 제거
    - 빈 줄 및 '#' 시작 줄(주석) 제외

    Returns:
        키워드 문자열 목록. 파일이 없으면 빈 리스트.
    """
    if not KEYWORDS_FILE.exists():
        print(f"[경고] 통합 키워드 파일을 찾을 수 없습니다: {KEYWORDS_FILE}")
        return []

    keywords: list[str] = []
    for line in KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keywords.append(line)
    return keywords


# 키워드 하나당 최대 몇 개의 블로그 글을 저장할지 설정합니다.
# 처음 테스트는 3개 정도가 적당합니다.
NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD = 20


# 검색 결과 페이지를 몇 페이지까지 볼지 설정합니다.
# 처음에는 1페이지만 권장합니다.
NAVER_BLOG_SEARCH_MAX_PAGES = 100


# ------------------------------------------------------------
# 직접 URL 수집 옵션
# ------------------------------------------------------------
# 검색 기능과 별개로, 특정 네이버 블로그 글 URL을 직접 넣어 수집할 수도 있습니다.
# 지금은 비워둬도 됩니다.
NAVER_BLOG_URLS: list[str] = [
    # "https://blog.naver.com/블로그아이디/글번호",
]


# ------------------------------------------------------------
# 유튜브 URL 설정
# ------------------------------------------------------------
# 다음 단계에서 사용할 예정입니다.
YOUTUBE_VIDEO_URLS: list[str] = [
    # "https://www.youtube.com/watch?v=VIDEO_ID",
]

# 키워드 하나당 최대 몇 개의 유튜브 영상을 가져올지 설정합니다.
# YouTube Data API quota를 아끼기 위해 처음에는 3개 정도를 권장합니다.
YOUTUBE_SEARCH_MAX_RESULTS_PER_KEYWORD = 10


# 유튜브 검색 정렬 방식입니다.
#
# 사용 예:
# "relevance"  → 관련도순
# "date"       → 최신순
# "viewCount"  → 조회수순
#
# 뷰티 트렌드 수집 목적이면 "date" 또는 "relevance"를 권장합니다.
YOUTUBE_SEARCH_ORDER = "date"


# 자막 언어 우선순위입니다.
# 한국어 자막을 먼저 찾고, 없으면 영어 자막을 찾습니다.
YOUTUBE_TRANSCRIPT_LANGUAGES: list[str] = ["ko", "en"]

# ------------------------------------------------------------
# 유튜브 길이 필터 설정
# ------------------------------------------------------------
# Shorts나 너무 짧은 영상을 제외하기 위한 최소 영상 길이입니다.
# 단위는 초입니다.
#
# 예:
# 180  → 3분 이상
# 300  → 5분 이상
# 600  → 10분 이상
YOUTUBE_MIN_DURATION_SECONDS = 180


# YouTube search.list의 videoDuration 필터입니다.
#
# "any"     → 모든 길이
# "short"   → 4분 미만
# "medium"  → 4분 이상 20분 미만
# "long"    → 20분 이상
#
# Shorts 제외 목적이면 "medium"을 추천합니다.
YOUTUBE_SEARCH_VIDEO_DURATION = "medium"


# ------------------------------------------------------------
# HTTP 요청 설정
# ------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 10

REQUEST_DELAY_MIN = 2

REQUEST_DELAY_MAX = 3


# ------------------------------------------------------------
# 수집 다양성 설정
# ------------------------------------------------------------
# 동일 키워드를 반복 실행해도 매번 다른 데이터가 수집되도록 제어하는 설정값들입니다.

# 수집 정렬 모드
# 'relevance' : 관련도순 (기본)
# 'latest'    : 최신 등록순
# 'popular'   : 조회수/인기순 (네이버는 인기순 API 미지원으로 관련도순 fallback)
CRAWL_SORT_MODE = "relevance"

# 네이버 검색 시작 위치 랜덤화
# True이면 1, 11, 21, 31, 41 중 무작위 위치에서 수집을 시작해 매번 다른 페이지를 읽음
# False이면 항상 첫 페이지(start=1)부터 시작 (기존 동작 유지)
USE_RANDOM_START = False

# 수집 기간 제한 (일수)
# 0  : 기간 제한 없음 (기존 동작 유지)
# 7  : 최근 7일 이내 게시물만 수집
# 30 : 최근 30일 이내 게시물만 수집
# 유튜브 API의 publishedAfter 파라미터에 동적으로 적용됩니다.
CRAWL_PERIOD_DAYS = 0

# 유튜브 우선 수집 언어
# 유튜브 API의 relevanceLanguage 파라미터에 적용되어 해당 언어권 영상이 우선 노출됩니다.
# 예: 'ko' (한국어), 'en' (영어), 'ja' (일본어)
RELEVANCE_LANGUAGE = "ko"


# ------------------------------------------------------------
# 저장 조건
# ------------------------------------------------------------
# 본문 길이가 너무 짧으면 정상 블로그 글이 아닐 가능성이 높으므로 저장하지 않습니다.
MIN_TEXT_LENGTH = 100