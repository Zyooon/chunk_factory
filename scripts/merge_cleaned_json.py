"""
data/cleaned 하위 naver_blog / youtube 폴더의 JSON 파일을 하나로 병합합니다.

실행:
    uv run python scripts/merge_cleaned_json.py

결과:
    data/cleaned/done.json
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEANED_DIR  = PROJECT_ROOT / "data" / "cleaned"
OUTPUT_FILE  = CLEANED_DIR / "done.json"

SOURCE_DIRS = [
    CLEANED_DIR / "naver_blog",
    CLEANED_DIR / "youtube",
]


def load_json_file(path: Path) -> list[dict]:
    """JSON 파일 하나를 읽어 레코드 목록으로 반환합니다. 배열/단일 객체 모두 처리."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [경고] 파싱 실패 — {path.name}: {e}")
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    print(f"  [경고] 지원하지 않는 JSON 형식 — {path.name}")
    return []


def main() -> None:
    merged: list[dict] = []
    total_files = 0

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            print(f"[스킵] 폴더 없음: {source_dir.relative_to(PROJECT_ROOT)}")
            continue

        json_files = sorted(source_dir.glob("*.json"))
        if not json_files:
            print(f"[스킵] JSON 파일 없음: {source_dir.relative_to(PROJECT_ROOT)}")
            continue

        print(f"\n[{source_dir.name}] {len(json_files)}개 파일 처리 중...")
        for f in json_files:
            records = load_json_file(f)
            print(f"  {f.name}  →  {len(records)}건")
            merged.extend(records)
            total_files += 1

    if not merged:
        print("\n[오류] 병합할 데이터가 없습니다.")
        sys.exit(1)

    OUTPUT_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(f"  병합 완료")
    print(f"{'=' * 50}")
    print(f"  처리 파일 수  : {total_files}개")
    print(f"  총 레코드 수  : {len(merged)}건")
    print(f"  저장 위치     : {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
