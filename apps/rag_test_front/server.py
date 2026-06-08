"""로컬 테스트용 HTTP 서버 (Python 표준 라이브러리 기반)

실행:
    uv run python -m apps.rag_test_front.server

접속:
    http://localhost:8000

실제 확인한 hair_analysis_log 컬럼:
    id, gender, face_shape, style_name, style_type('recommended'/'worst'), face_proportion
    ※ style_code 컬럼 없음 → 서버의 STYLE_CODE_MAP으로 보완
    ※ face_shape='남성' 오류 row 3건 존재 → 조회 시 제외
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_PROJECT_ROOT / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    import django
    django.setup()
except Exception as _django_err:
    print(f"[경고] Django setup 실패 (계속 진행): {_django_err}")

from apps.analysis_rag.service import generate_analysis_result  # noqa: E402
from apps.chatbot_rag.graph import run_chatbot  # noqa: E402

_STATIC_DIR = Path(__file__).parent / "static"
_DB_PATH = _PROJECT_ROOT / "db_beauty.sqlite3"
_PORT = 8000

_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

# (gender, style_name) → style_code 매핑
# DB에는 style_code 컬럼이 없으므로 서버에서 보완
# DB에만 있는 스타일(크루, 가일, 보니 등)은 None 처리됨
_STYLE_CODE_MAP: dict[tuple[str, str], str] = {
    # 남성
    ("남성", "버즈"):       "m-01",
    ("남성", "하이앤타이트"): "m-02",
    ("남성", "아이비리그"):  "m-03",
    ("남성", "크롭"):       "m-04",
    ("남성", "드롭"):       "m-05",
    ("남성", "슬릭"):       "m-06",
    ("남성", "허밍"):       "m-07",
    ("남성", "댄디"):       "m-08",
    ("남성", "리프"):       "m-09",
    ("남성", "퀴프"):       "m-10",
    ("남성", "울프"):       "m-11",
    ("남성", "애즈"):       "m-12",
    ("남성", "시스루"):     "m-13",
    ("남성", "쉐도우"):     "m-14",
    ("남성", "베이비"):     "m-15",
    ("남성", "포마드"):     "m-16",
    ("남성", "히피"):       "m-17",
    ("남성", "그런지"):     "m-18",
    ("남성", "리젠트"):     "m-19",
    # 여성
    ("여성", "픽시"):       "f-01",
    ("여성", "프리다"):     "f-02",
    ("여성", "보브"):       "f-03",
    ("여성", "태슬"):       "f-04",
    ("여성", "원랭스"):     "f-05",
    ("여성", "허그"):       "f-06",
    ("여성", "빌드"):       "f-07",
    ("여성", "레이어드"):   "f-08",
    ("여성", "허쉬"):       "f-09",
    ("여성", "샌드"):       "f-10",
    ("여성", "샤기"):       "f-11",
    ("여성", "울프"):       "f-12",
    ("여성", "버드"):       "f-13",
    ("여성", "히메"):       "f-14",
    ("여성", "다이앤"):     "f-15",
    ("여성", "레아"):       "f-16",
    ("여성", "레인"):       "f-17",
    ("여성", "그레이스"):   "f-18",
    ("여성", "엘리자벳"):  "f-19",
    ("여성", "페미닌"):     "f-20",
    ("여성", "벌룬"):       "f-21",
    ("여성", "코튼"):       "f-22",
    ("여성", "발롱"):       "f-23",
    ("여성", "구름"):       "f-24",
    ("여성", "젤리"):       "f-25",
    ("여성", "러플"):       "f-26",
    ("여성", "바그"):       "f-27",
    ("여성", "프릴"):       "f-28",
    ("여성", "윈드"):       "f-29",
    ("여성", "그런지"):     "f-30",
}

# 유효한 face_shape 값 (face_shape='남성' 같은 오류 row 제외용)
_VALID_FACE_SHAPES = {"각진형", "계란형", "둥근형", "역삼각형", "장방형"}

# style_name으로 올 수 없는 값 (얼굴형명, 성별명이 잘못 들어간 오류 row 제외용)
_INVALID_STYLE_NAMES = {"각진형", "계란형", "둥근형", "역삼각형", "장방형", "남성", "여성"}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _lookup_style_code(gender: str, style_name: str) -> str | None:
    return _STYLE_CODE_MAP.get((gender, style_name))


def _query_hair_options(gender: str, face_shape: str, face_proportion: str) -> dict:
    """DB에서 조건에 맞는 추천/비추천 스타일 목록을 반환한다."""
    if face_shape not in _VALID_FACE_SHAPES:
        return {
            "recommended_styles": [],
            "worst_styles": [],
            "source": {"table": "hair_analysis_log", "matched_count": 0},
            "warning": f"유효하지 않은 face_shape: {face_shape}",
        }

    with _get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT DISTINCT style_name, style_type
            FROM hair_analysis_log
            WHERE gender = ?
              AND face_shape = ?
              AND face_proportion = ?
              AND face_shape != gender
            ORDER BY style_name
            """,
            (gender, face_shape, face_proportion),
        )
        # 오류 row 필터: style_name에 얼굴형·성별명이 잘못 들어간 케이스 제거
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT COUNT(*) FROM hair_analysis_log
            WHERE gender = ? AND face_shape = ? AND face_proportion = ?
              AND face_shape != gender
            """,
            (gender, face_shape, face_proportion),
        )
        total = cur.fetchone()[0]

    recommended: list[dict] = []
    worst: list[dict] = []
    seen_rec: set[str] = set()
    seen_worst: set[str] = set()

    for row in rows:
        name = row["style_name"]
        stype = row["style_type"]

        # 얼굴형·성별명이 style_name에 잘못 들어간 오류 row 건너뜀
        if name in _INVALID_STYLE_NAMES:
            continue

        code = _lookup_style_code(gender, name)

        if stype == "recommended" and name not in seen_rec:
            seen_rec.add(name)
            recommended.append({"style_name": name, "style_code": code})
        elif stype == "worst" and name not in seen_worst:
            seen_worst.add(name)
            worst.append({"style_name": name, "style_code": code})

    return {
        "recommended_styles": recommended,
        "worst_styles": worst,
        "source": {
            "table": "hair_analysis_log",
            "matched_count": total,
        },
    }


def _query_hair_stats() -> dict:
    """hair_analysis_log 전체를 집계해 스타일별 추천/비추천 카운트를 반환한다."""
    with _get_db() as conn:
        cur = conn.cursor()

        # 얼굴형·성별명이 style_name에 잘못 들어간 오류 row도 제외
        _placeholders = ",".join("?" * len(_INVALID_STYLE_NAMES))
        cur.execute(
            f"""
            SELECT
                gender,
                style_name,
                SUM(CASE WHEN style_type = 'recommended' THEN 1 ELSE 0 END) AS recommended_count,
                SUM(CASE WHEN style_type = 'worst'       THEN 1 ELSE 0 END) AS worst_count,
                COUNT(*) AS total_count
            FROM hair_analysis_log
            WHERE face_shape != gender
              AND style_name NOT IN ({_placeholders})
            GROUP BY gender, style_name
            ORDER BY recommended_count DESC, gender, style_name
            """,
            tuple(_INVALID_STYLE_NAMES),
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM hair_analysis_log WHERE face_shape != gender")
        total_rows = cur.fetchone()[0]

    items = []
    for row in rows:
        gender = row["gender"]
        name = row["style_name"]
        code = _lookup_style_code(gender, name)
        items.append({
            "gender": gender,
            "style_name": name,
            "style_code": code,
            "recommended_count": row["recommended_count"],
            "worst_count": row["worst_count"],
            "total_count": row["total_count"],
        })

    return {
        "items": items,
        "summary": {
            "total_rows": total_rows,
            "total_styles": len(items),
        },
    }


class _RAGTestHandler(BaseHTTPRequestHandler):
    """GET(정적 파일 + stats API) + POST(/api/*) 요청을 처리하는 핸들러."""

    server_version = "RAGTestServer/1.0"

    # ── GET ──────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self.path.split("?")[0]  # 쿼리스트링 제거

        if path in ("/", "/index.html"):
            self._serve_static("index.html")
        elif path == "/stats.html":
            self._serve_static("stats.html")
        elif path == "/api/hair-style-stats":
            self._handle_hair_stats()
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
        else:
            self._send_not_found()

    # ── POST ─────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        data = self._read_body_json()
        if data is None:
            return

        if self.path == "/api/analysis":
            self._handle_analysis(data)
        elif self.path == "/api/chatbot":
            self._handle_chatbot(data)
        elif self.path == "/api/hair-options":
            self._handle_hair_options(data)
        else:
            self._send_not_found()

    # ── API 핸들러 ────────────────────────────────────────────────────────────

    def _handle_analysis(self, data: dict) -> None:
        try:
            result = generate_analysis_result(
                gender=data["gender"],
                face_shape=data["face_shape"],
                face_proportion=data["face_proportion"],
                recommended_hair_styles=data["recommended_hair_styles"],
            )
            self._send_json(result)
        except KeyError as exc:
            self._send_json({"error": f"필수 필드 누락: {exc}"}, status=400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _handle_chatbot(self, data: dict) -> None:
        try:
            result = run_chatbot(
                user_message=data["user_message"],
                gender=data["gender"],
                face_shape=data["face_shape"],
                face_proportion=data["face_proportion"],
                previous_analysis=data.get("previous_analysis"),
                previous_recommendations=data.get("previous_recommendations"),
                user_profile=data.get("user_profile"),
                chat_history=data.get("chat_history"),
            )
            self._send_json(result)
        except KeyError as exc:
            self._send_json({"error": f"필수 필드 누락: {exc}"}, status=400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _handle_hair_options(self, data: dict) -> None:
        try:
            result = _query_hair_options(
                gender=data["gender"],
                face_shape=data["face_shape"],
                face_proportion=data["face_proportion"],
            )
            self._send_json(result)
        except KeyError as exc:
            self._send_json({"error": f"필수 필드 누락: {exc}"}, status=400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _handle_hair_stats(self) -> None:
        try:
            result = _query_hair_stats()
            self._send_json(result)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    # ── 정적 파일 서빙 ────────────────────────────────────────────────────────

    def _serve_static(self, filename: str) -> None:
        filepath = (_STATIC_DIR / filename).resolve()
        if not str(filepath).startswith(str(_STATIC_DIR.resolve())):
            self._send_not_found()
            return

        ext = Path(filename).suffix.lower()
        content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")

        try:
            content = filepath.read_bytes()
        except FileNotFoundError:
            self._send_not_found()
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ── 응답 헬퍼 ─────────────────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_not_found(self) -> None:
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not Found")

    def _read_body_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"error": f"요청 JSON 파싱 오류: {exc}"}, status=400)
            return None


def main() -> None:
    server = HTTPServer(("localhost", _PORT), _RAGTestHandler)
    print("=" * 50)
    print("Beauty RAG 로컬 테스트 서버")
    print(f"메인:  http://localhost:{_PORT}")
    print(f"통계:  http://localhost:{_PORT}/stats.html")
    print("종료:  Ctrl+C")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료.")
        server.server_close()


if __name__ == "__main__":
    main()
