import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.crawler.config import (
    BASE_DIR,
    NAVER_BLOG_OUTPUT_DIR,
    OUTPUT_DIR,
    YOUTUBE_OUTPUT_DIR,
)
from apps.crawler.utils import get_collected_at

CRAWL_LOG_PATH = BASE_DIR / "data" / "logs" / "crawl_log.json"

BATCH_SIZE = 10

_PLATFORM_DIR: dict[str, Path] = {
    "naver_blog": NAVER_BLOG_OUTPUT_DIR,
    "youtube":    YOUTUBE_OUTPUT_DIR,
}

_PLATFORM_LABEL: dict[str, str] = {
    "naver_blog": "naver",
    "youtube":    "youtube",
}


# ============================================================
# storage.py
# ------------------------------------------------------------
# 저장 구조:
#   data/crawled/naver/batch_1/naver_20260603_204230.txt
#   data/crawled/youtube/batch_1/youtube_20260603_204230.txt
#
# batch 폴더는 .txt 파일이 BATCH_SIZE(10)개 차면 자동으로 다음 번호로 전환됩니다.
# ============================================================


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def prepare_output_directories() -> None:
    ensure_directory(OUTPUT_DIR)
    ensure_directory(NAVER_BLOG_OUTPUT_DIR)
    ensure_directory(YOUTUBE_OUTPUT_DIR)


def print_output_directories() -> None:
    print(f"Naver  output : {NAVER_BLOG_OUTPUT_DIR}")
    print(f"YouTube output: {YOUTUBE_OUTPUT_DIR}")


def resolve_batch_dir(platform_dir: Path) -> Path:
    """
    platform_dir 아래에서 현재 저장할 batch_N 폴더를 결정합니다.

    - batch 폴더가 하나도 없으면 batch_1 생성
    - 마지막 batch 폴더의 .txt 파일이 BATCH_SIZE 이상이면 batch_N+1 생성
    - BATCH_SIZE 미만이면 그 폴더 그대로 반환
    """
    ensure_directory(platform_dir)

    batch_dirs = sorted(
        [
            d for d in platform_dir.iterdir()
            if d.is_dir() and re.fullmatch(r"batch_\d+", d.name)
        ],
        key=lambda d: int(d.name.split("_")[1]),
    )

    if not batch_dirs:
        target = platform_dir / "batch_1"
        target.mkdir(exist_ok=True)
        return target

    latest = batch_dirs[-1]
    txt_count = len(list(latest.glob("*.txt")))

    if txt_count >= BATCH_SIZE:
        next_num = int(latest.name.split("_")[1]) + 1
        target = platform_dir / f"batch_{next_num}"
        target.mkdir(exist_ok=True)
        return target

    return latest


def make_timestamped_filename(platform_label: str, batch_dir: Path) -> Path:
    """
    {platform_label}_{YYYYMMDD}_{HHMMSS}.txt 형식의 중복 없는 파일 경로를 반환합니다.
    같은 초에 여러 파일이 생성될 경우 _1, _2 ... 접미사를 붙입니다.
    """
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    base = f"{platform_label}_{timestamp}"

    file_path = batch_dir / f"{base}.txt"
    counter = 1
    while file_path.exists():
        file_path = batch_dir / f"{base}_{counter}.txt"
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
    keyword: str = "",
) -> Path:
    """
    크롤링 결과를 batch 구조로 저장합니다.

    Args:
        source_type : "naver_blog" 또는 "youtube"
        title       : 메타데이터용 제목
        url         : 원본 URL
        collected_at: 수집 시각
        body_text   : 본문 텍스트
        extra_metadata: 추가 메타데이터
        keyword     : (호환성 유지용, 저장 경로에는 미사용)

    Returns:
        저장된 파일 경로
    """
    platform_dir = _PLATFORM_DIR.get(source_type)
    if platform_dir is None:
        raise ValueError(f"Unsupported source_type: {source_type}")

    platform_label = _PLATFORM_LABEL[source_type]
    batch_dir      = resolve_batch_dir(platform_dir)
    file_path      = make_timestamped_filename(platform_label, batch_dir)

    document_text = build_text_document(
        source_type=source_type,
        title=title,
        url=url,
        collected_at=collected_at,
        body_text=body_text,
        extra_metadata=extra_metadata,
    )

    file_path.write_text(document_text, encoding="utf-8")

    current_count = len(list(batch_dir.glob("*.txt")))
    try:
        display_path = file_path.relative_to(BASE_DIR)
    except ValueError:
        display_path = file_path

    print(f"[적재 완료] {display_path} (현재 폴더 내 {current_count}/{BATCH_SIZE}개)")

    return file_path


# ============================================================
# crawl log
# ============================================================

def load_crawl_log() -> dict:
    if not CRAWL_LOG_PATH.exists():
        return {}
    try:
        return json.loads(CRAWL_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_crawl_log(log: dict) -> None:
    ensure_directory(CRAWL_LOG_PATH.parent)
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
