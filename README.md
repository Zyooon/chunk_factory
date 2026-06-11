# chunk_factory

뷰티(헤어·메이크업) 텍스트 데이터를 수집하고, Gemini AI로 RAG용 구조화 JSON을 만든 뒤  
ChromaDB에 임베딩하여 LangGraph 기반 챗봇을 구동하는 데이터 파이프라인입니다.

---

## 전체 흐름

```
keywords.txt 작성
       ↓
크롤러 실행 (네이버 블로그, 유튜브)
  data/crawled/**/*.txt
       ↓
hair_factory 실행 (Gemini AI 정제)
  data/cleaned/**/*.json
       ↓
JSON 병합
  data/cleaned/done.json
       ↓
    ┌──────────────────────────────┐
    │                              │
SQLite 적재                  ChromaDB 적재
db_beauty.sqlite3          vector_data/chroma/
    │                              │
    └──────────┬───────────────────┘
               ↓
    rag_test_front (웹 UI)   analysis_rag CLI   chatbot_rag CLI / bulk_test
```

---

## 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.11 이상 |
| [uv](https://docs.astral.sh/uv/) | 최신 |
| [Ollama](https://ollama.com/) | 최신 (임베딩용) |

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
uv sync
```

### 3. Ollama 임베딩 모델 준비

ChromaDB 적재 및 RAG 검색에 [bge-m3](https://ollama.com/library/bge-m3) 모델을 사용합니다.

```bash
# Ollama 설치 후 모델 pull
ollama pull bge-m3
```

> Ollama가 실행 중이어야 ChromaDB 적재 및 RAG 검색이 동작합니다.  
> 기본 URL: `http://localhost:11434`

---

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

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
2. `API 및 서비스` → `라이브러리`에서 `YouTube Data API v3` 검색 후 활성화
3. `사용자 인증 정보` → `API 키 만들기`
4. 발급된 키를 `.env`의 `YOUTUBE_API_KEY`에 입력

> 네이버 블로그만 수집하려면 `GEMINI_API_KEY`만 있어도 됩니다.

---

## 데이터 파이프라인 실행

### Step 1. 크롤링 키워드 설정

`data/config/keywords.txt` 파일을 생성하고 키워드를 한 줄씩 입력합니다.  
`#`으로 시작하는 줄은 주석으로 처리됩니다.

```
# 헤어 관련
얼굴형 헤어스타일
남성 헤어스타일 추천

# 메이크업 관련
봄웜톤 메이크업
```

> 파일이 없으면 크롤러가 경고를 출력하고 아무것도 수집하지 않습니다.

### Step 2. 크롤러 실행

```bash
uv run python -m apps.crawler.runner
```

수집된 텍스트 파일은 아래 경로에 저장됩니다.

```
data/crawled/
├── naver/
│   └── batch_1/
│       └── naver_20260601_143000.txt
└── youtube/
    └── batch_1/
        └── youtube_20260601_143000.txt
```

수집 이력은 `data/logs/crawl_log.json`에 기록됩니다. 같은 URL은 재실행해도 중복 수집하지 않습니다.

### Step 3. AI 정제 실행

```bash
uv run python scripts/hair_factory.py
```

`data/crawled/` 폴더의 txt 파일을 Gemini API로 처리하여 `data/cleaned/**/*.json`에 저장합니다.  
처리 이력은 `data/logs/processed_log.json`에 기록됩니다.

### Step 4. JSON 병합

```bash
uv run python scripts/merge_cleaned_json.py
```

`data/cleaned/**/*.json` 파일들을 하나로 합쳐 `data/cleaned/done.json`을 생성합니다.

### Step 5. SQLite DB 적재

```bash
uv run python scripts/ingest_beauty_data.py --mode import
```

`data/cleaned/done.json`을 `db_beauty.sqlite3`에 저장합니다.  
웹 UI(`rag_test_front`)에서 스타일 목록을 불러오는 데 사용됩니다.

```bash
# 기존 데이터를 비우고 다시 적재하려면
uv run python scripts/ingest_beauty_data.py --mode import --replace
```

### Step 6. ChromaDB 적재 (벡터 DB)

> **이 단계 전에 Ollama가 실행 중이어야 합니다.**

```bash
uv run python -m apps.vector_index.ingest
```

`data/cleaned/done.json`을 읽어 `bge-m3` 임베딩으로 `vector_data/chroma/`에 저장합니다.

---

## 테스트 방법

Step 1–6을 완료한 뒤 아래 중 하나를 실행합니다.

---

### 방법 1. 웹 UI 테스트 (권장)

```bash
uv run python -m apps.rag_test_front.server
```

브라우저에서 아래 URL에 접속합니다.

| URL | 설명 |
|-----|------|
| http://localhost:8000 | 분석 + 챗봇 통합 테스트 UI |
| http://localhost:8000/stats.html | DB 적재 통계 확인 |

**사용 방법:**
1. 성별, 얼굴형, 삼정 비율, (선택) 퍼스널 컬러를 입력
2. DB에서 추천 스타일 목록 불러오기
3. `분석 생성` 버튼 클릭 → RAG 기반 헤어/메이크업 분석 결과 확인
4. 분석 결과를 바탕으로 챗봇에 후속 질문

---

### 방법 2. 챗봇 CLI 샘플 테스트

사전에 준비된 샘플 3가지 케이스를 실행합니다. (ChromaDB 필요)

```bash
uv run python -m apps.chatbot_rag.cli
```

**실행되는 케이스:**
| 케이스 | 질문 | 설명 |
|--------|------|------|
| CASE 1 | "리프 손질 어려워?" | 정상 질문 |
| CASE 2 | "이거" | 애매한 질문 → 재질문 |
| CASE 3 | "리프 손질 어려워?" (분석 없음) | 분석 결과 없는 상태 |

---

### 방법 3. 대량 질문 Bulk 테스트

`data/test/bulk_questions.txt`에 있는 질문들을 일괄 실행하고 로그를 저장합니다.

```bash
uv run python -m apps.chatbot_rag.bulk_test
```

결과는 `logs/chatbot_rag_bulk_test.log`에 저장됩니다.

**bulk_questions.txt 형식:**
```
# 주석은 이렇게
안녕          ← greeting intent 테스트
리프 손질 어려워?  ← styling_method intent 테스트
데이트 갈 건데 어떤 머리가 좋아?  ← occasion_advice intent 테스트
```

각 질문에 대해 아래 항목이 출력됩니다.

| 항목 | 설명 |
|------|------|
| `intent` | 분류된 의도 |
| `category` | hair / makeup |
| `needs_clarification` | 재질문 여부 |
| `detected_occasion` | 감지된 상황 (데이트, 면접 등) |
| `retrieved_count` | ChromaDB에서 가져온 문서 수 |
| `answer` | 챗봇 답변 |

> 마지막에 2턴 상황 선택 테스트도 자동으로 실행됩니다.  
> (1턴: 상황 질문 → 2턴: 분위기 선택 후 추천)

---

### 방법 4. 분석 RAG CLI 테스트

헤어 분석 결과 생성만 단독으로 테스트합니다.

```bash
uv run python -m apps.analysis_rag.cli
```

**입력값 (코드 내 하드코딩):**
- 성별: 남성 / 얼굴형: 둥근형 / 삼정 비율: 균형
- 추천 스타일: 리프(m-09), 퀴프(m-10), 댄디(m-08)

---

## 챗봇 intent 목록

| intent | 설명 | 예시 |
|--------|------|------|
| `style_fit` | 스타일 어울림 질문 | "이 스타일이 나한테 잘 어울려?" |
| `styling_method` | 손질·연출 방법 | "리프 손질 어려워?" |
| `maintenance` | 유지관리 질문 | "유지관리 쉬운 스타일 뭐야?" |
| `comparison` | 스타일 비교 | "리프랑 퀴프 중 뭐가 나아?" |
| `general_followup` | 일반 후속 질문 | "조금 더 설명해줘" |
| `occasion_advice` | 상황별 추천 | "데이트 갈 건데 어떤 머리가 좋아?" |
| `greeting` | 인사 | "안녕" |
| `smalltalk` | 잡담 | "고마워" |
| `irrelevant` | 무관한 질문 | "파이썬 코드 알려줘" |
| `noise` | 노이즈 입력 | "ㅋㅋㅋ", "이거", "그거" |
| `unclear` | 의도 불명확 → 재질문 |  |

---

## 생성 파일 목록

| 파일/폴더 | 위치 | 설명 |
|-----------|------|------|
| `data/config/keywords.txt` | 프로젝트 루트 | 크롤링 키워드 (수동 작성) |
| `data/crawled/` | 프로젝트 루트 | 크롤링 원본 txt |
| `data/cleaned/` | 프로젝트 루트 | AI 정제 JSON + done.json |
| `data/logs/crawl_log.json` | 프로젝트 루트 | 크롤링 완료 URL 이력 |
| `data/logs/processed_log.json` | 프로젝트 루트 | AI 처리 완료 파일 이력 |
| `db_beauty.sqlite3` | 프로젝트 루트 | 정규화 스타일 DB |
| `vector_data/chroma/` | 프로젝트 루트 | ChromaDB 임베딩 |
| `logs/chatbot_rag_bulk_test.log` | 프로젝트 루트 | bulk_test 결과 로그 |

위 파일과 폴더는 모두 `.gitignore`에 포함되어 있습니다.

---

## 환경 변수 전체 목록

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `GEMINI_API_KEY` | (필수) | Gemini API 키 |
| `YOUTUBE_API_KEY` | (유튜브 수집 시 필수) | YouTube Data API 키 |
| `CHROMA_DIR` | `./vector_data/chroma` | ChromaDB 저장 경로 |
| `CHROMA_COLLECTION_NAME` | `beauty_rag` | ChromaDB 컬렉션 이름 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | 임베딩 모델 이름 |
| `GEMINI_CHAT_MODEL` | `gemini-2.5-flash` | 챗봇·분석 생성 모델 |
| `DEFAULT_RETRIEVAL_K` | `5` | ChromaDB 검색 문서 수 |

---

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요.
- 네이버 블로그 크롤링은 요청 간 2~3초 딜레이가 적용됩니다. 과도한 수집은 자제해 주세요.
- YouTube Data API는 일일 무료 할당량(10,000 units)이 있습니다.
- Gemini API Free Tier 사용 시 분당 요청 수 제한이 있습니다.
- ChromaDB 적재 및 RAG 검색은 Ollama(`bge-m3`)가 실행 중이어야 합니다.
