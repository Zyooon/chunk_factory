import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.crawler.config import (
    BASE_DIR,
    NAVER_BLOG_OUTPUT_DIR,
    OUTPUT_DIR,
    YOUTUBE_OUTPUT_DIR,
)
from apps.crawler.utils import get_collected_at, sanitize_filename

CRAWL_LOG_PATH = BASE_DIR / "data" / "logs" / "crawl_log.json"


# ============================================================
# storage.py
# ------------------------------------------------------------
# 크롤링 결과를 로컬 txt 파일로 저장하는 기능을 담당합니다.
#
# 저장 파일 형식:
# ./crawled_data/{source_type}/{YYYYMMDD}_{제목}.txt
#
# 예:
# ./crawled_data/naver_blog/20260528_올리브영_추천템.txt
# ./crawled_data/youtube/20260528_봄웜톤_메이크업_자막.txt
# ============================================================


def ensure_directory(path: Path) -> None:
    """
    특정 폴더가 없으면 생성합니다.

    Args:
        path:
            생성할 폴더 경로입니다.
    """
    path.mkdir(parents=True, exist_ok=True)


def prepare_output_directories() -> None:
    """
    크롤링 결과 저장에 필요한 모든 폴더를 생성합니다.

    생성 대상:
    - crawled_data/
    - crawled_data/naver_blog/
    - crawled_data/youtube/
    """
    ensure_directory(OUTPUT_DIR)
    ensure_directory(NAVER_BLOG_OUTPUT_DIR)
    ensure_directory(YOUTUBE_OUTPUT_DIR)


def print_output_directories() -> None:
    """
    현재 저장 폴더 경로를 화면에 출력합니다.
    """
    print(f"Naver output: {NAVER_BLOG_OUTPUT_DIR}")
    print(f"YouTube output: {YOUTUBE_OUTPUT_DIR}")


def get_output_dir_by_source(source_type: str) -> Path:
    """
    source_type에 따라 저장 폴더를 반환합니다.

    Args:
        source_type:
            "naver_blog" 또는 "youtube"만 허용합니다.

    Returns:
        저장 폴더 Path 객체입니다.

    Raises:
        ValueError:
            지원하지 않는 source_type이 들어온 경우 발생합니다.
    """
    if source_type == "naver_blog":
        return NAVER_BLOG_OUTPUT_DIR

    if source_type == "youtube":
        return YOUTUBE_OUTPUT_DIR

    raise ValueError(f"Unsupported source_type: {source_type}")


def make_date_prefix() -> str:
    """
    파일명 앞에 붙일 날짜 문자열을 생성합니다.

    Returns:
        예: "20260528"
    """
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    return now.strftime("%Y%m%d")


def build_file_path(output_dir: Path, title: str) -> Path:
    """
    저장할 txt 파일 경로를 생성합니다.

    파일명 규칙:
    {YYYYMMDD}_{안전하게_정리한_제목}.txt

    같은 파일명이 이미 존재하면 뒤에 번호를 붙입니다.

    예:
    20260528_선크림추천.txt
    20260528_선크림추천_1.txt
    20260528_선크림추천_2.txt

    Args:
        output_dir:
            저장할 폴더입니다.

        title:
            원본 제목입니다.

    Returns:
        중복을 피한 최종 파일 경로입니다.
    """
    date_prefix = make_date_prefix()
    safe_title = sanitize_filename(title)

    base_filename = f"{date_prefix}_{safe_title}"
    file_path = output_dir / f"{base_filename}.txt"

    counter = 1
    while file_path.exists():
        file_path = output_dir / f"{base_filename}_{counter}.txt"
        counter += 1

    return file_path


def build_text_document(
    source_type: str,
    title: str,
    url: str,
    collected_at: str,
    body_text: str,
    extra_metadata: dict[str, str] | None = None,
) -> str:
    """
    txt 파일에 저장할 전체 문서를 만듭니다.

    RAG 전처리를 고려해, 파일 상단에 메타데이터를 넣고
    그 아래에 본문 텍스트를 넣습니다.

    Args:
        source_type:
            데이터 출처 유형입니다.
            예: "naver_blog", "youtube"

        title:
            글 또는 영상 제목입니다.

        url:
            원본 URL입니다.

        collected_at:
            수집 시각입니다.
            예: "2026-05-28T14:30:00+09:00"

        body_text:
            저장할 본문 텍스트입니다.

        extra_metadata:
            추가로 저장하고 싶은 메타데이터입니다.
            예: {"language": "ko", "video_id": "abc123"}

    Returns:
        txt 파일에 들어갈 전체 문자열입니다.
    """
    metadata_lines = [
        f"source_type: {source_type}",
        f"title: {title}",
        f"url: {url}",
        f"collected_at: {collected_at}",
    ]

    if extra_metadata:
        for key, value in extra_metadata.items():
            metadata_lines.append(f"{key}: {value}")

    metadata_block = "\n".join(metadata_lines)

    return f"{metadata_block}\n\n{body_text.strip()}\n"


def save_text_document(
    source_type: str,
    title: str,
    url: str,
    collected_at: str,
    body_text: str,
    extra_metadata: dict[str, str] | None = None,
) -> Path:
    """
    크롤링 결과를 txt 파일로 저장합니다.

    Args:
        source_type:
            "naver_blog" 또는 "youtube"입니다.

        title:
            저장 파일명과 메타데이터에 사용할 제목입니다.

        url:
            원본 URL입니다.

        collected_at:
            수집 시각입니다.

        body_text:
            저장할 순수 텍스트 본문입니다.

        extra_metadata:
            선택 추가 메타데이터입니다.

    Returns:
        저장된 파일 경로입니다.
    """
    output_dir = get_output_dir_by_source(source_type)
    ensure_directory(output_dir)

    file_path = build_file_path(output_dir, title)

    document_text = build_text_document(
        source_type=source_type,
        title=title,
        url=url,
        collected_at=collected_at,
        body_text=body_text,
        extra_metadata=extra_metadata,
    )

    file_path.write_text(document_text, encoding="utf-8")

    return file_path


def load_crawl_log() -> dict:
    if not CRAWL_LOG_PATH.exists():
        return {}
    try:
        return json.loads(CRAWL_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_crawl_log(log: dict) -> None:
    CRAWL_LOG_PATH.write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_already_crawled(url: str, log: dict) -> bool:
    return url in log


def add_crawl_log_entry(url: str, source_type: str, title: str, log: dict) -> dict:
    log[url] = {
        "crawled_at": get_collected_at(),
        "source_type": source_type,
        "title": title,
    }
    return log