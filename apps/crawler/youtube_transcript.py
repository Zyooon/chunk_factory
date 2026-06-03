import re
import html
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

import requests
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from apps.crawler.config import (
    CRAWL_PERIOD_DAYS,
    CRAWL_SORT_MODE,
    MIN_TEXT_LENGTH,
    RELEVANCE_LANGUAGE,
    REQUEST_TIMEOUT,
    USER_AGENT,
    YOUTUBE_API_KEY,
    YOUTUBE_MIN_DURATION_SECONDS,
    YOUTUBE_SEARCH_MAX_RESULTS_PER_KEYWORD,
    YOUTUBE_SEARCH_ORDER,
    YOUTUBE_SEARCH_VIDEO_DURATION,
    YOUTUBE_TRANSCRIPT_LANGUAGES,
    load_shared_keywords,
)
from apps.crawler.storage import (
    add_crawl_log_entry,
    is_already_crawled,
    load_crawl_log,
    save_crawl_log,
    save_text_document,
)
from apps.crawler.utils import get_collected_at, normalize_whitespace, polite_sleep


# ============================================================
# youtube_transcript.py
# ------------------------------------------------------------
# 유튜브 검색어를 기반으로 영상을 찾고,
# 각 영상의 자막/스크립트를 추출해 txt 파일로 저장하는 모듈입니다.
#
# 전체 흐름:
#
# 1. config.py의 YOUTUBE_SEARCH_KEYWORDS를 읽음
# 2. YouTube Data API search.list 호출
# 3. 영상 제목, video_id, URL 추출
# 4. youtube-transcript-api로 자막 조회
# 5. 자막 segment를 하나의 텍스트로 병합
# 6. crawled_data/youtube/에 txt 저장
# ============================================================


YOUTUBE_SEARCH_API_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos"

_YOUTUBE_ORDER_MAP = {
    "relevance": "relevance",
    "latest": "date",
    "popular": "viewCount",
}


def _get_youtube_order_param() -> str:
    """CRAWL_SORT_MODE를 YouTube API order 파라미터 값으로 변환합니다.

    CRAWL_SORT_MODE가 매핑 테이블에 없으면 YOUTUBE_SEARCH_ORDER(기존 설정값)로 fallback합니다.
    """
    return _YOUTUBE_ORDER_MAP.get(CRAWL_SORT_MODE, YOUTUBE_SEARCH_ORDER)


def _get_published_after_param() -> str | None:
    """CRAWL_PERIOD_DAYS를 YouTube API publishedAfter 파라미터 값(ISO 8601)으로 변환합니다.

    CRAWL_PERIOD_DAYS가 0이면 None을 반환해 파라미터를 추가하지 않습니다.
    """
    if not CRAWL_PERIOD_DAYS:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=CRAWL_PERIOD_DAYS)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class YouTubeVideoSearchResult:
    """
    YouTube Data API 검색 결과에서 필요한 정보만 담는 클래스입니다.

    Attributes:
        video_id:
            유튜브 영상 ID입니다.

        title:
            유튜브 영상 제목입니다.

        url:
            표준 유튜브 영상 URL입니다.

        channel_title:
            채널명입니다.

        published_at:
            영상 게시 시각입니다.
    """

    video_id: str
    title: str
    url: str
    channel_title: str
    published_at: str
    duration_seconds: int = 0


@dataclass
class YouTubeTranscriptDocument:
    """
    유튜브 자막 수집 결과입니다.

    Attributes:
        video_id:
            유튜브 영상 ID입니다.

        title:
            영상 제목입니다.

        url:
            표준 유튜브 영상 URL입니다.

        language:
            자막 요청 언어 우선순위입니다.
            실제 반환 언어를 정밀하게 판별하지는 않고, 설정값을 메타데이터로 남깁니다.

        body_text:
            자막 segment들을 병합한 순수 텍스트입니다.
    """

    video_id: str
    title: str
    url: str
    language: str
    body_text: str


def build_youtube_watch_url(video_id: str) -> str:
    """
    video_id로 표준 유튜브 시청 URL을 생성합니다.

    Args:
        video_id:
            유튜브 영상 ID입니다.

    Returns:
        표준 유튜브 영상 URL입니다.
    """
    return f"https://www.youtube.com/watch?v={video_id}"

def parse_iso8601_duration_to_seconds(duration: str) -> int:
    """
    YouTube Data API의 ISO 8601 duration 문자열을 초 단위로 변환합니다.

    예:
    PT45S       -> 45
    PT3M20S     -> 200
    PT1H2M10S   -> 3730

    Args:
        duration:
            YouTube Data API contentDetails.duration 값입니다.

    Returns:
        초 단위 영상 길이입니다.
    """
    pattern = r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
    match = re.match(pattern, duration)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def validate_youtube_api_key() -> bool:
    """
    YouTube API Key가 설정되어 있는지 확인합니다.

    Returns:
        API Key가 있으면 True, 없으면 False입니다.
    """
    if YOUTUBE_API_KEY:
        return True

    print("[YOUTUBE][ERROR] YOUTUBE_API_KEY is missing.")
    print("[YOUTUBE][ERROR] Create .env file in project root and add:")
    print("YOUTUBE_API_KEY=your_api_key_here")

    return False


def search_youtube_videos(
    keyword: str,
    limit: int = YOUTUBE_SEARCH_MAX_RESULTS_PER_KEYWORD,
    pages: int = 1,
) -> list[YouTubeVideoSearchResult]:
    """
    YouTube Data API search.list를 호출해 키워드에 맞는 영상 목록을 가져옵니다.

    Args:
        keyword:
            유튜브 검색 키워드입니다.
        limit:
            API 한 페이지당 요청할 최대 영상 수입니다.
        pages:
            pageToken을 이용해 순회할 최대 페이지 수입니다.

    Returns:
        YouTubeVideoSearchResult 목록입니다.
    """
    if not validate_youtube_api_key():
        return []

    print(f"[YOUTUBE][SEARCH] keyword={keyword}, limit={limit}, pages={pages}")

    order_param = _get_youtube_order_param()
    published_after = _get_published_after_param()

    print(f"[YOUTUBE][SEARCH] sort_mode={CRAWL_SORT_MODE} → order={order_param}")
    if published_after:
        print(f"[YOUTUBE][SEARCH] period_limit={CRAWL_PERIOD_DAYS}days → publishedAfter={published_after}")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    raw_videos: list[YouTubeVideoSearchResult] = []
    page_token: str | None = None

    for page_num in range(1, pages + 1):
        params: dict[str, Any] = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": limit,
            "order": order_param,
            "key": YOUTUBE_API_KEY,
            "regionCode": "KR",
            "relevanceLanguage": RELEVANCE_LANGUAGE,
            "safeSearch": "moderate",
            "videoDuration": YOUTUBE_SEARCH_VIDEO_DURATION,
        }
        if published_after:
            params["publishedAfter"] = published_after
        if page_token:
            params["pageToken"] = page_token

        print(f"[YOUTUBE][SEARCH] page={page_num}/{pages}")

        try:
            polite_sleep()
            response = requests.get(
                YOUTUBE_SEARCH_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except requests.RequestException as error:
            print(f"[YOUTUBE][SEARCH ERROR] keyword={keyword}")
            print(f"[YOUTUBE][SEARCH ERROR] detail={error}")
            break
        except ValueError as error:
            print(f"[YOUTUBE][SEARCH ERROR] failed to parse JSON. keyword={keyword}")
            print(f"[YOUTUBE][SEARCH ERROR] detail={error}")
            break

        for item in data.get("items", []):
            id_info = item.get("id", {})
            snippet = item.get("snippet", {})
            video_id = id_info.get("videoId", "")
            if not video_id:
                continue
            title = normalize_whitespace(html.unescape(snippet.get("title", "")))
            channel_title = normalize_whitespace(html.unescape(snippet.get("channelTitle", "")))
            published_at = snippet.get("publishedAt", "")
            if not title:
                title = f"youtube_video_{video_id}"
            raw_videos.append(YouTubeVideoSearchResult(
                video_id=video_id,
                title=title,
                url=build_youtube_watch_url(video_id),
                channel_title=channel_title,
                published_at=published_at,
            ))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    video_ids = [v.video_id for v in raw_videos]
    duration_map = fetch_video_durations(video_ids)

    filtered_videos: list[YouTubeVideoSearchResult] = []

    for video in raw_videos:
        duration_seconds = duration_map.get(video.video_id, 0)
        video.duration_seconds = duration_seconds

        if duration_seconds < YOUTUBE_MIN_DURATION_SECONDS:
            print(
                f"[YOUTUBE][SKIP] too short video. "
                f"title={video.title}, duration={duration_seconds}s"
            )
            continue

        filtered_videos.append(video)

    print(f"[YOUTUBE][SEARCH] found={len(raw_videos)}, after_duration_filter={len(filtered_videos)}")

    for index, video in enumerate(filtered_videos, start=1):
        print(
            f"[YOUTUBE][SEARCH] {index}. "
            f"{video.title} ({video.duration_seconds}s) ({video.url})"
        )

    return filtered_videos

def fetch_video_durations(video_ids: list[str]) -> dict[str, int]:
    """
    YouTube Data API videos.list로 영상들의 실제 길이를 조회합니다.

    search.list 결과에는 실제 영상 길이가 없으므로,
    videos.list의 contentDetails.duration을 추가로 조회해야 합니다.

    Args:
        video_ids:
            영상 ID 목록입니다.

    Returns:
        {video_id: duration_seconds} 형태의 딕셔너리입니다.
    """
    if not video_ids:
        return {}

    if not validate_youtube_api_key():
        return {}

    params = {
        "part": "contentDetails",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        polite_sleep()

        response = requests.get(
            YOUTUBE_VIDEOS_API_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data: dict[str, Any] = response.json()

    except requests.RequestException as error:
        print("[YOUTUBE][DURATION ERROR] failed to fetch video durations.")
        print(f"[YOUTUBE][DURATION ERROR] detail={error}")
        return {}

    except ValueError as error:
        print("[YOUTUBE][DURATION ERROR] failed to parse JSON.")
        print(f"[YOUTUBE][DURATION ERROR] detail={error}")
        return {}

    durations: dict[str, int] = {}

    for item in data.get("items", []):
        video_id = item.get("id", "")
        content_details = item.get("contentDetails", {})
        duration = content_details.get("duration", "")

        if not video_id or not duration:
            continue

        durations[video_id] = parse_iso8601_duration_to_seconds(duration)

    return durations


def fetch_transcript_segments(video_id: str) -> list[dict[str, Any]] | None:
    """
    유튜브 영상의 자막 segment 목록을 가져옵니다.

    최신 youtube-transcript-api 버전에서는
    YouTubeTranscriptApi.get_transcript()가 아니라
    YouTubeTranscriptApi().fetch() 방식을 사용합니다.

    Args:
        video_id:
            유튜브 영상 ID입니다.

    Returns:
        자막 segment 목록 또는 None입니다.
    """
    try:
        api = YouTubeTranscriptApi()

        fetched_transcript = api.fetch(
            video_id,
            languages=YOUTUBE_TRANSCRIPT_LANGUAGES,
        )

        transcript_segments: list[dict[str, Any]] = []

        for segment in fetched_transcript:
            transcript_segments.append(
                {
                    "text": segment.text,
                    "start": segment.start,
                    "duration": segment.duration,
                }
            )

        return transcript_segments

    except NoTranscriptFound:
        print(f"[YOUTUBE][SKIP] no transcript found. video_id={video_id}")
        return None

    except TranscriptsDisabled:
        print(f"[YOUTUBE][SKIP] transcripts disabled. video_id={video_id}")
        return None

    except Exception as error:
        print(f"[YOUTUBE][ERROR] failed to fetch transcript. video_id={video_id}")
        print(f"[YOUTUBE][ERROR] detail={error}")
        return None

def normalize_transcript_text(transcript_segments: list[dict[str, Any]]) -> str:
    """
    유튜브 자막 segment 목록을 하나의 텍스트로 병합합니다.

    Args:
        transcript_segments:
            youtube-transcript-api가 반환한 자막 segment 목록입니다.

    Returns:
        정리된 자막 텍스트입니다.
    """
    texts: list[str] = []

    for segment in transcript_segments:
        text = segment.get("text", "")

        if not text:
            continue

        text = text.replace("\n", " ")
        texts.append(text)

    merged_text = " ".join(texts)

    return normalize_whitespace(merged_text)


def collect_single_youtube_video(
    video: YouTubeVideoSearchResult, log: dict, keyword: str = ""
) -> bool:
    """
    검색된 유튜브 영상 하나의 자막을 수집하고 txt 파일로 저장합니다.

    Args:
        video:
            YouTube Data API 검색 결과 영상 객체입니다.
        log:
            crawl_log dict입니다.
        keyword:
            검색 키워드입니다. 키워드 이름의 서브폴더에 저장됩니다.

    Returns:
        저장 성공 여부입니다.
    """
    print(f"[YOUTUBE] collecting transcript: {video.title}")
    print(f"[YOUTUBE] url: {video.url}")

    transcript_segments = fetch_transcript_segments(video.video_id)

    if transcript_segments is None:
        return False

    body_text = normalize_transcript_text(transcript_segments)

    if len(body_text) < MIN_TEXT_LENGTH:
        print(
            f"[YOUTUBE][SKIP] transcript too short. "
            f"video_id={video.video_id}, length={len(body_text)}"
        )
        return False

    language_priority = ",".join(YOUTUBE_TRANSCRIPT_LANGUAGES)

    saved_path = save_text_document(
        source_type="youtube",
        title=video.title,
        url=video.url,
        collected_at=get_collected_at(),
        body_text=body_text,
        extra_metadata={
            "collector": "youtube_transcript_search",
            "video_id": video.video_id,
            "channel_title": video.channel_title,
            "published_at": video.published_at,
            "language_priority": language_priority,
            "duration_seconds": str(video.duration_seconds),
        },
        keyword=keyword,
    )

    print(f"[YOUTUBE] saved: {saved_path}")

    add_crawl_log_entry(video.url, "youtube", video.title, log)
    save_crawl_log(log)

    return True


def collect_youtube_transcripts(
    limit: int = YOUTUBE_SEARCH_MAX_RESULTS_PER_KEYWORD,
    pages: int = 1,
) -> tuple[int, int]:
    """
    config.py의 YOUTUBE_SEARCH_KEYWORDS 기준으로 유튜브 영상을 검색하고,
    검색된 영상들의 자막을 저장합니다.

    Args:
        limit:
            키워드당 API 한 페이지에서 가져올 최대 영상 수입니다.
        pages:
            키워드당 순회할 최대 API 페이지 수입니다.

    Returns:
        (성공 개수, 실패 개수)
    """
    keywords = load_shared_keywords()
    if not keywords:
        print("[YOUTUBE][SEARCH] no keywords configured.")
        return 0, 0

    print(f"[로그] 통합 config 파일에서 총 {len(keywords)}개의 키워드를 로드하여 [유튜브] 크롤링을 시작합니다.")

    success_count = 0
    fail_count = 0
    log = load_crawl_log()
    global_seen_video_ids: set[str] = set()

    for keyword in keywords:
        videos = search_youtube_videos(keyword, limit=limit, pages=pages)

        if not videos:
            print(f"[YOUTUBE][SEARCH] no videos found. keyword={keyword}")
            continue

        for video in videos:
            if is_already_crawled(video.url, log):
                print(f"[YOUTUBE][SKIP] already crawled: {video.url}")
                continue

            if video.video_id in global_seen_video_ids:
                print(f"[YOUTUBE][SKIP] duplicated video_id={video.video_id}")
                continue

            global_seen_video_ids.add(video.video_id)

            if collect_single_youtube_video(video, log, keyword=keyword):
                success_count += 1
            else:
                fail_count += 1

    print(f"[YOUTUBE] completed. success={success_count}, fail={fail_count}")

    return success_count, fail_count