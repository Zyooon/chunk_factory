# chunk_factory

뷰티 관련 텍스트 데이터를 수집하고, AI를 활용해 RAG용 구조화 JSON으로 변환하는 데이터 파이프라인입니다.

현재 지원 소스: 네이버 블로그, 유튜브 자막

---

## 전체 흐름

```
크롤러 실행 → crawled_data/ (txt 파일)
                    ↓
hair_factory 실행 → cleaned_data/ (JSON 파일)
```

---

## 환경 요구사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/) (패키지 관리)

---

## 설치

### 1. uv 설치 (최초 1회)

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/Zyooon/chunk_factory.git
cd chunk_factory
uv venv
uv sync
```

---

## API 키 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 키를 입력합니다.

```
GEMINI_API_KEY=your_gemini_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### Gemini API Key 발급

1. [Google AI Studio](https://aistudio.google.com/) 접속
2. 로그인 후 `Get API key` 클릭
3. 발급된 키를 `.env`의 `GEMINI_API_KEY`에 입력

### YouTube Data API Key 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. `API 및 서비스` → `라이브러리`에서 `YouTube Data API v3` 검색 후 활성화
4. `사용자 인증 정보` → `API 키 만들기`
5. 발급된 키를 `.env`의 `YOUTUBE_API_KEY`에 입력

> 유튜브 자막 수집만 사용하는 경우 `YOUTUBE_API_KEY`는 필수입니다.  
> 네이버 블로그만 수집하는 경우 `GEMINI_API_KEY`만 있어도 됩니다.

---

## 사용 방법

### Step 1. 크롤러 설정

`apps/crawler/config.py`에서 수집할 키워드와 수량을 설정합니다.

```python
# 네이버 블로그 검색 키워드
NAVER_BLOG_SEARCH_KEYWORDS = [
    "얼굴형 헤어스타일",
    "봄웜톤 메이크업",
]

# 키워드당 최대 수집 수
NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD = 3

# 유튜브 검색 키워드
YOUTUBE_SEARCH_KEYWORDS = [
    "얼굴형 헤어스타일",
]

# 키워드당 최대 수집 수
YOUTUBE_SEARCH_MAX_RESULTS_PER_KEYWORD = 3
```

### Step 2. 크롤러 실행

```bash
uv run main.py
```

수집된 txt 파일은 아래 경로에 저장됩니다.

```
crawled_data/
├── naver_blog/
│   └── 20260528_제목.txt
└── youtube/
    └── 20260528_영상제목.txt
```

수집 이력은 프로젝트 루트의 `crawl_log.json`에 기록됩니다. 같은 URL은 재실행해도 중복 수집하지 않습니다.

### Step 3. 데이터 정제 실행

```bash
uv run hair_factory.py
```

`crawled_data/` 폴더의 txt 파일을 읽어 Gemini API로 처리한 뒤, 아래 경로에 저장됩니다.

```
cleaned_data/
└── cleaned_rag_data_20260528_143000.json
```

처리 이력은 `processed_log.json`에 기록됩니다. 이미 처리된 파일은 재실행해도 건너뜁니다.

---

## 출력 JSON 구조 (헤어)

```json
[
  {
    "category": "hair",
    "gender": "여성",
    "conditions": {
      "face_shape": "둥근형",
      "face_proportion": "균형"
    },
    "recommended_styles": ["시스루 뱅 굵은 히피펌", "사이드 뱅 젤리펌"],
    "worst_styles": ["5:5 가르마 긴 생머리"],
    "expert_reasoning_positive": "추천 이유 설명",
    "expert_reasoning_negative": "워스트 이유 설명"
  }
]
```

**face_shape 허용값:** `계란형` `둥근형` `각진형` `장방형` `역삼각형`

**face_proportion 허용값:** `균형` `상안부_긴형` `중안부_긴형` `하안부_긴형`

---

## 생성 파일 정리

| 파일 | 위치 | 설명 |
|------|------|------|
| `crawl_log.json` | 프로젝트 루트 | 크롤링 완료 URL 이력 |
| `processed_log.json` | 프로젝트 루트 | AI 처리 완료 파일 이력 |
| `crawled_data/` | 프로젝트 루트 | 크롤링 원본 txt |
| `cleaned_data/` | 프로젝트 루트 | 정제된 RAG용 JSON |

위 파일과 폴더는 모두 `.gitignore`에 포함되어 있습니다.

---

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요.
- 네이버 블로그 크롤링은 요청 간 2~3초 딜레이가 적용됩니다. 과도한 수집은 자제해 주세요.
- YouTube Data API는 일일 무료 할당량(10,000 units)이 있습니다. 키워드당 수집 수를 적게 유지하는 것을 권장합니다.
- Gemini API Free Tier 사용 시 분당 요청 수 제한이 있습니다. `SLEEP_BETWEEN_REQUESTS` 값을 올려서 조절할 수 있습니다.
