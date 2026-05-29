# hair_factory.py
#
# ============================================================
# [실행 가이드 - uv 사용]
# ============================================================
# 1. uv 설치 (최초 1회, PowerShell):
#    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
#
# 2. 가상환경 생성 및 의존성 설치:
#    uv venv
#    uv sync
#    # 또는 개별 설치:
#    uv pip install google-genai python-dotenv
#
# 3. .env 파일 생성 (프로젝트 루트):
#    GEMINI_API_KEY=여기에_발급받은_키_입력
#
# 4. input_texts/ 폴더에 .txt 파일을 넣은 뒤 실행:
#    uv run hair_factory.py
#    # 또는 가상환경 활성화 후:
#    .venv\Scripts\activate   (Windows)
#    python hair_factory.py
# ============================================================

import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# ── 환경 변수 로드 ──────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        ".env 파일에 GEMINI_API_KEY가 설정되지 않았습니다.\n"
        "프로젝트 루트에 .env 파일을 만들고 GEMINI_API_KEY=<your_key> 를 추가하세요."
    )

client = genai.Client()

# ── 경로 설정 ───────────────────────────────────────────────
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
INPUT_DIR = Path("./data/crawled")
OUTPUT_FILE = Path(f"./data/cleaned/cleaned_rag_data_{timestamp}.json")
PROCESSED_LOG_FILE = Path("./data/logs/processed_log.json")

# ── API 설정 ────────────────────────────────────────────────
MODEL_NAME = "gemini-2.5-flash"
SLEEP_BETWEEN_REQUESTS = 3  # 초 (Free Tier Rate Limit 방지)
MAX_CHARS_PER_BATCH = 30_000

# ── 마스터 프롬프트 ─────────────────────────────────────────
SYSTEM_PROMPT = """
[System]
당신은 15년 차 청담동 뷰티 살롱 수석 디자이너이자 텍스트 파싱 전문가입니다.
주어진 뷰티 관련 스크립트 원문(블로그/유튜브 대본)을 분석하여, '조건에 따른 헤어스타일 추천 팩트'만 추출해 지정된 JSON 배열 포맷으로 변환하는 것이 당신의 목표입니다.

[저작권 회피 및 데이터 재창조 원칙 (CRITICAL)]
1. 팩트(아이디어)만 추출: 원작자의 '표현(고유한 문장, 비유, 억양)'은 절대 그대로 복사하지 마세요. '어떤 얼굴형/비율에 어떤 머리가 어울리고/안 어울린다'는 뷰티 업계의 객관적인 사실(도메인 지식)만 추출하세요.
2. 페르소나 재작성 (Rewrite): 추출된 팩트를 바탕으로, 15년 차 수석 디자이너의 다정하고 전문적인 말투("~해요", "~추천해 드려요")로 'expert_reasoning_positive'와 'expert_reasoning_negative'를 완전히 새롭게 창작하세요.
3. 특정 인물 언급 금지: 원문에 특정 연예인이나 인플루언서의 이름이 있더라도, 결과물(JSON)에는 법적 보호를 위해 절대 포함하지 마세요. 오직 스타일의 조형적 특징과 원리만 설명하세요.

[데이터 매핑 규격 (Mapping Rules)]
다음 지정된 카테고리 내에서만 값을 매핑하세요.
- category: "hair" 고정
- gender: "여성" 또는 "남성" (문맥 파악, 기본 "여성")
- face_shape: 반드시 ["계란형", "둥근형", "각진형", "장방형", "역삼각형"] 중 1개 선택
    * [강제 정규화 규칙]: 원문에 아래와 같은 비표준 단어가 등장하면, 반드시 지정된 표준 단어로 강제 변환(치환)하여 출력하세요.
        > 하트형, 당근형 ➡️ "역삼각형"
        > 다이아몬드형, 육각형, 땅콩형, 사각형 ➡️ "각진형"
        > 긴형, 세로형, 직사각형, 말상 ➡️ "장방형"
        > 갸름한형, 타원형 ➡️ "계란형"
        > 짧은형, 동그란형 ➡️ "둥근형"
- face_proportion: ["균형", "상안부_긴형", "중안부_긴형", "하안부_긴형"] 중 1개 선택

[추론 제한 규칙]
원문에 특정 얼굴형, 스타일, 추천/비추천 이유가 명확히 연결되어 있지 않다면 새로운 추천 조합을 만들지 마세요.
단순히 스타일명만 등장하고 조건이 부족한 경우에는 JSON 객체로 만들지 않습니다.

[출력 포맷]
분석된 내용을 바탕으로 아래의 JSON 배열(Array) 형식만 엄격하게 출력하세요. 마크다운 코드 블록(```json) 내부에 작성하며, 그 외에 어떠한 인사말이나 부가 설명도 덧붙이지 마세요. 하나의 원문에서 여러 개의 얼굴형 조건이 분석된다면 JSON 객체(Object)를 배열 안에 여러 개 추가하세요.

[
  {
    "category": "hair",
    "gender": "여성",
    "conditions": {
      "face_shape": "장방형",
      "face_proportion": "중안부_긴형"
    },
    "recommended_styles": [
      {
        "style_name": "시스루 뱅 히피펌",
        "style_group": "",
        "style_features": ["가벼운 앞머리", "풍성한 컬", "세로 길이 분산"]
      }
    ],
    "worst_styles": [
      {
        "style_name": "5:5 가르마 긴 생머리",
        "style_group": "",
        "style_features": ["중앙 가르마", "긴 직선 실루엣", "세로감 강조"]
      }
    ],
    "expert_reasoning_positive": "장방형 얼굴은 세로 길이가 강조되기 쉬워서, 앞머리와 컬감으로 시선을 부드럽게 분산해 주는 스타일이 잘 어울려요. 가벼운 앞머리와 풍성한 웨이브를 더하면 얼굴 비율이 한층 안정적으로 보여요.",
    "expert_reasoning_negative": "정중앙 가르마와 긴 생머리는 얼굴의 세로선을 더 길어 보이게 만들 수 있어요. 특히 볼륨 없이 차분하게 떨어지는 스타일은 긴 인상을 더 강조할 수 있어 주의가 필요해요."
  }
]

[헤어스타일 필드 구조화 규칙]
recommended_styles와 worst_styles는 문자열 배열이 아니라 객체 배열로 출력하세요.

각 스타일 객체는 아래 필드를 포함합니다.

- style_name: 원문에서 확인된 스타일을 서비스에서 사용할 수 있도록 짧고 일반적인 명칭으로 재작성한 값
- style_group: 추후 스타일 그룹 분류를 위해 비워두는 필드. 현재는 반드시 빈 문자열("")로 출력
- style_features: 해당 스타일의 조형적 특징을 2~4개의 짧은 키워드로 작성

주의:
- style_name에는 연예인명, 인플루언서명, 브랜드명, 블로그 특유의 표현, 감탄사, 비유를 넣지 마세요.
- style_name은 원문 표현을 그대로 복사하지 말고, 뷰티 스타일명으로 자연스럽게 정규화하세요.
- style_group은 아직 분류 체계가 확정되지 않았으므로 절대 임의로 채우지 말고 빈 문자열("")로 둡니다.
"""


def load_processed_log() -> dict:
    if not PROCESSED_LOG_FILE.exists():
        return {}
    try:
        return json.loads(PROCESSED_LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_processed_log(log: dict) -> None:
    PROCESSED_LOG_FILE.write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_batches(txt_files: list[Path]) -> list[list[Path]]:
    batches: list[list[Path]] = []
    current_batch: list[Path] = []
    current_chars = 0

    for txt_path in txt_files:
        file_chars = len(txt_path.read_text(encoding="utf-8"))
        if current_batch and current_chars + file_chars > MAX_CHARS_PER_BATCH:
            batches.append(current_batch)
            current_batch = [txt_path]
            current_chars = file_chars
        else:
            current_batch.append(txt_path)
            current_chars += file_chars

    if current_batch:
        batches.append(current_batch)

    return batches


def process_batch(batch_files: list[Path]) -> list[dict]:
    """배치 내 파일들을 이어붙여 Gemini API로 처리 후 파싱된 항목 리스트를 반환."""
    parts = []
    for i, txt_path in enumerate(batch_files, start=1):
        text = txt_path.read_text(encoding="utf-8")
        parts.append(f"[파일 {i}: {txt_path.name}]\n{text}")
    batch_text = "\n".join(parts)
    full_prompt = f"{SYSTEM_PROMPT}\n\n[분석할 스크립트 원문]\n{batch_text}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


def main():
    if not INPUT_DIR.exists():
        INPUT_DIR.mkdir(parents=True)
        print(f"[안내] {INPUT_DIR} 폴더를 생성했습니다. .txt 파일을 넣고 다시 실행하세요.")
        return

    all_txt_files = sorted(INPUT_DIR.rglob("*.txt"))
    if not all_txt_files:
        print(f"[안내] {INPUT_DIR} 폴더에 처리할 .txt 파일이 없습니다.")
        return

    processed_log = load_processed_log()
    new_files = [f for f in all_txt_files if f.name not in processed_log]
    skipped_count = len(all_txt_files) - len(new_files)

    print(f"[시작] 새로 처리할 파일 {len(new_files)}개 / 이미 처리된 파일 {skipped_count}개 건너뜀\n")

    if not new_files:
        print("[안내] 새로 처리할 파일이 없습니다.")
        return

    batches = build_batches(new_files)
    master_list: list[dict] = []
    total_batches = len(batches)

    for batch_idx, batch_files in enumerate(batches, start=1):
        file_names = ", ".join(f.name for f in batch_files)
        print(f"[배치 {batch_idx}/{total_batches}] 처리 중: {file_names}")
        try:
            entries = process_batch(batch_files)
            master_list.extend(entries)

            now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            for txt_path in batch_files:
                processed_log[txt_path.name] = {
                    "processed_at": now_str,
                    "extracted_count": len(entries),
                }
            save_processed_log(processed_log)

            print(f"  → {len(entries)}개 항목 추출 완료 (누적: {len(master_list)}개)")
        except json.JSONDecodeError as e:
            print(f"  [오류] JSON 파싱 실패 (배치 {batch_idx}): {e}")
        except Exception as e:
            print(f"  [오류] API 호출 또는 처리 실패 (배치 {batch_idx}): {type(e).__name__}: {e}")

        if batch_idx < total_batches:
            print(f"  → Rate Limit 방지: {SLEEP_BETWEEN_REQUESTS}초 대기 중...")
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    OUTPUT_FILE.write_text(
        json.dumps(master_list, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[완료] 총 {len(master_list)}개 항목을 '{OUTPUT_FILE}'에 저장했습니다.")


if __name__ == "__main__":
    main()
