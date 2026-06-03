"""
chunk-factory 메인 허브

실행:
    uv run python main.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable  # 현재 venv의 python

MENU = {
    "1": {
        "label": "크롤링 실행",
        "cmd": [PYTHON, "-m", "apps.crawler.runner"],
    },
    "2": {
        "label": "전처리 실행  (hair_factory → data/cleaned/*.json 생성)",
        "cmd": [PYTHON, str(PROJECT_ROOT / "hair_factory.py")],
    },
    "3": {
        "label": "JSON 병합    (data/cleaned/** → done.json)",
        "cmd": [PYTHON, str(PROJECT_ROOT / "scripts" / "merge_cleaned_json.py")],
    },
    "4": {
        "label": "DB 저장 실행 (done.json → SQLite)",
        "cmd": [PYTHON, str(PROJECT_ROOT / "scripts" / "ingest_beauty_data.py")],
    },
    "5": {
        "label": "ChromaDB 적재 (done.json → 벡터 DB)",
        "cmd": [PYTHON, "-m", "apps.rag.ingest"],
    },
    "6": {
        "label": "CLI 챗봇 실행",
        "cmd": [PYTHON, "-m", "apps.rag.cli_chat"],
    },
}


def print_menu() -> None:
    print()
    print("=" * 52)
    print("   chunk-factory  ·  파이프라인 허브")
    print("=" * 52)
    for key, item in MENU.items():
        print(f"   [{key}]  {item['label']}")
    print("   [0]  종료")
    print("=" * 52)


def run(cmd: list[str]) -> None:
    """자식 프로세스를 현재 터미널에 붙여서 실행합니다."""
    print()
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        print("\n[인터럽트] 실행이 중단됐습니다.")
    print()
    input("엔터를 누르면 메뉴로 돌아갑니다...")


def main() -> None:
    while True:
        print_menu()
        choice = input("번호를 입력하세요: ").strip()

        if choice == "0":
            print("종료합니다.")
            break

        item = MENU.get(choice)
        if item is None:
            print(f"  → '{choice}' 는 없는 번호입니다. 다시 입력해 주세요.")
            continue

        print(f"\n  ▶  {item['label']} 시작합니다...")
        run(item["cmd"])


if __name__ == "__main__":
    main()
