from apps.crawler.naver_blog import collect_naver_blogs
from apps.crawler.storage import (
    prepare_output_directories,
    print_output_directories,
)
from apps.crawler.youtube_transcript import collect_youtube_transcripts


def run_crawler_app() -> None:
    print("crawler app started.")

    prepare_output_directories()
    print("Output directories are ready.")
    print_output_directories()

    naver_success_count, naver_fail_count = collect_naver_blogs()
    youtube_success_count, youtube_fail_count = collect_youtube_transcripts()

    print("crawler app summary:")
    print(f"- naver success: {naver_success_count}")
    print(f"- naver fail: {naver_fail_count}")
    print(f"- youtube success: {youtube_success_count}")
    print(f"- youtube fail: {youtube_fail_count}")

    print("crawler app finished.")


if __name__ == "__main__":
    run_crawler_app()