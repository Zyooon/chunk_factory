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
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

MENU = {
    "1": {
        "label": "크롤링 실행",
        "cmd": [PYTHON, "-m", "apps.crawler.runner"],
    },
    "2": {
        "label": "전처리 실행  (hair_factory → data/cleaned/*.json 생성)",
        "cmd": [PYTHON, str(SCRIPTS_DIR / "hair_factory.py")],
    },
    "3": {
        "label": "JSON 병합    (data/cleaned/** → done.json)",
        "cmd": [PYTHON, str(SCRIPTS_DIR / "merge_cleaned_json.py")],
    },
    "4": {
        "label": "DB 저장 실행 (done.json → SQLite)",
        "cmd": [PYTHON, str(SCRIPTS_DIR / "ingest_beauty_data.py")],
    },
    "5": {
        "label": "ChromaDB 적재 (done.json → 벡터 DB)",
        "cmd": [PYTHON, "-m", "apps.vector_index.ingest"],
    },
    "6": {
        "label": "CLI 챗봇 실행",
        "cmd": [PYTHON, "-m", "apps.chatbot_rag.cli"],
    },
    "7": {
        "label": "테스트 화면 실행  (RAG 프론트 서버)",
        "cmd": [PYTHON, "-m", "apps.rag_test_front.server"],
    },
    "8": {
        "label": "챗봇 질문 테스트  (bulk_test)",
        "cmd": [PYTHON, "-m", "apps.chatbot_rag.bulk_test"],
    },
}


def print_menu() -> None:
    print()
    print("=" * 52)
    print("   chunk-factory  ·  파이프라인 허브")
    print("=" * 52)
    for key, item in MENU.items():
        print(f"   [{key}]  {item['label']}")
    print("   [s]  스크립트 실행  (scripts/ 폴더)")
    print("   [0]  종료")
    print("=" * 52)


def confirm(label: str) -> bool:
    """실행 전 확인 프롬프트. y/Y 입력 시 True, 나머지는 False."""
    print()
    print(f"  실행 항목 : {label}")
    answer = input("  정말 실행하시겠습니까? (y/n): ").strip().lower()
    return answer == "y"


def run(cmd: list[str]) -> None:
    """자식 프로세스를 현재 터미널에 붙여서 실행합니다."""
    print()
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        print("\n[인터럽트] 실행이 중단됐습니다.")
    print()
    input("엔터를 누르면 메뉴로 돌아갑니다...")


def run_scripts_menu() -> None:
    """scripts/ 폴더의 .py 파일을 동적으로 나열하고 실행합니다."""
    while True:
        scripts = sorted(SCRIPTS_DIR.glob("*.py"))

        print()
        print("=" * 52)
        print("   scripts/ 폴더  ·  스크립트 실행")
        print("=" * 52)
        if not scripts:
            print("   (실행할 스크립트가 없습니다)")
        else:
            for idx, path in enumerate(scripts, start=1):
                print(f"   [{idx}]  {path.name}")
        print("   [0]  메인 메뉴로 돌아가기")
        print("=" * 52)

        if not scripts:
            input("엔터를 누르면 메인 메뉴로 돌아갑니다...")
            return

        choice = input("번호를 입력하세요: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not (1 <= int(choice) <= len(scripts)):
            print(f"  → '{choice}' 는 없는 번호입니다. 다시 입력해 주세요.")
            continue

        selected = scripts[int(choice) - 1]
        if not confirm(selected.name):
            print("  → 취소되었습니다.")
            continue

        run([PYTHON, str(selected)])


def main() -> None:
    while True:
        print_menu()
        choice = input("번호를 입력하세요: ").strip().lower()

        if choice == "0":
            print("종료합니다.")
            break

        if choice == "s":
            run_scripts_menu()
            continue

        item = MENU.get(choice)
        if item is None:
            print(f"  → '{choice}' 는 없는 번호입니다. 다시 입력해 주세요.")
            continue

        if not confirm(item["label"]):
            print("  → 취소되었습니다.")
            continue

        run(item["cmd"])


if __name__ == "__main__":
    main()
