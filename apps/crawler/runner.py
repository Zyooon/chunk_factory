from apps.crawler.config import load_shared_keywords
from apps.crawler.naver_blog import collect_naver_blogs
from apps.crawler.storage import (
    prepare_output_directories,
    print_output_directories,
)
from apps.crawler.youtube_transcript import collect_youtube_transcripts


def run_crawler_app(platform: list[str], limit: int, pages: int) -> None:
    print("crawler app started.")

    prepare_output_directories()
    print("Output directories are ready.")
    print_output_directories()

    naver_success_count = naver_fail_count = 0
    youtube_success_count = youtube_fail_count = 0

    if "naver" in platform:
        naver_success_count, naver_fail_count = collect_naver_blogs(
            limit=limit, pages=pages
        )

    if "youtube" in platform:
        youtube_success_count, youtube_fail_count = collect_youtube_transcripts(
            limit=limit, pages=pages
        )

    print("crawler app summary:")
    if "naver" in platform:
        print(f"- naver success: {naver_success_count}")
        print(f"- naver fail: {naver_fail_count}")
    if "youtube" in platform:
        print(f"- youtube success: {youtube_success_count}")
        print(f"- youtube fail: {youtube_fail_count}")

    print("crawler app finished.")


def _ask_platform() -> list[str]:
    while True:
        raw = input(
            "[1/4] 크롤링할 플랫폼을 선택하세요 (1: naver, 2: youtube, 3: 둘 다) [기본값: 3]: "
        ).strip()
        if raw == "" or raw == "3":
            return ["naver", "youtube"]
        if raw == "1":
            return ["naver"]
        if raw == "2":
            return ["youtube"]
        print("  → 1, 2, 3 중 하나를 입력하거나 엔터를 눌러 주세요.")


def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return default
        try:
            value = int(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("  → 숫자만 입력해 주세요.")


def main() -> None:
    print()
    print("=" * 50)
    print("  뷰티 데이터 크롤러 — 대화형 설정")
    print("=" * 50)
    print()

    platform = _ask_platform()
    limit    = _ask_int("[2/4] 키워드당 최대 수집할 개수를 입력하세요 [기본값: 10]: ", 10)
    pages    = _ask_int("[3/4] 수집할 페이지 수를 입력하세요 [기본값: 1]: ", 1)

    print("[4/4] keywords.txt 로드 중...", end=" ")
    keywords = load_shared_keywords()
    print(f"{len(keywords)}개 완료")

    platform_label = " + ".join(platform)

    print()
    print("=" * 50)
    print("  크롤링 실행 설정 확인 (사용자 정의)")
    print("=" * 50)
    print(f"  플랫폼     : {platform_label}")
    print(f"  키워드 수  : {len(keywords)}개 (data/config/keywords.txt 로드 완료)")
    print(f"  키워드당   : 최대 {limit}개 수집")
    print(f"  페이지 수  : {pages}페이지")
    print(f"  예상 최대  : {len(keywords) * limit}건")
    print("=" * 50)

    answer = input("위 설정으로 크롤링을 시작하시겠습니까? (y/N): ").strip().lower()
    if answer != "y":
        print("크롤링을 취소했습니다.")
        return

    run_crawler_app(platform=platform, limit=limit, pages=pages)


if __name__ == "__main__":
    main()
