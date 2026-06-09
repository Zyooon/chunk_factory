"""로컬 테스트용 HTTP 서버 (Python 표준 라이브러리 기반)

실행:
    uv run python -m apps.rag_test_front.server

접속:
    http://localhost:8000

DB 구조 (정규화 모델 — ingest_beauty_data.py 적재 기준):
    face_conditions         : id, gender, face_shape, face_proportion,
                              expert_reasoning_positive, expert_reasoning_negative
    hair_styles             : style_code (PK), style_name
    condition_style_mapping : id, condition_id(FK), style_id(FK), is_recommended(0/1)
    style_features          : id, mapping_id(FK), feature_description
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

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _query_hair_options(gender: str, face_shape: str, face_proportion: str) -> dict:
    """정규화 테이블(face_conditions + condition_style_mapping + hair_styles)에서
    조건에 맞는 추천/비추천 스타일 목록을 반환한다."""
    with _get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                hs.style_name,
                hs.style_code,
                csm.is_recommended
            FROM condition_style_mapping csm
            JOIN face_conditions fc  ON csm.condition_id = fc.id
            JOIN hair_styles     hs  ON csm.style_id     = hs.style_code
            WHERE fc.gender          = ?
              AND fc.face_shape      = ?
              AND fc.face_proportion = ?
            ORDER BY csm.is_recommended DESC, hs.style_name
            """,
            (gender, face_shape, face_proportion),
        )
        rows = cur.fetchall()

    if not rows:
        return {
            "recommended_styles": [],
            "worst_styles": [],
            "source": {
                "table": "condition_style_mapping",
                "matched_count": 0,
            },
        }

    recommended: list[dict] = []
    worst: list[dict] = []

    for row in rows:
        entry = {"style_name": row["style_name"], "style_code": row["style_code"]}
        if row["is_recommended"]:
            recommended.append(entry)
        else:
            worst.append(entry)

    return {
        "recommended_styles": recommended,
        "worst_styles": worst,
        "source": {
            "table": "condition_style_mapping",
            "matched_count": len(rows),
        },
    }


def _query_hair_stats() -> dict:
    """정규화 테이블 전체를 집계해 스타일별 추천/비추천 카운트를 반환한다."""
    with _get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                fc.gender,
                hs.style_name,
                hs.style_code,
                SUM(CASE WHEN csm.is_recommended = 1 THEN 1 ELSE 0 END) AS recommended_count,
                SUM(CASE WHEN csm.is_recommended = 0 THEN 1 ELSE 0 END) AS worst_count,
                COUNT(*) AS total_count
            FROM condition_style_mapping csm
            JOIN face_conditions fc  ON csm.condition_id = fc.id
            JOIN hair_styles     hs  ON csm.style_id     = hs.style_code
            GROUP BY fc.gender, hs.style_code
            ORDER BY recommended_count DESC, fc.gender, hs.style_name
            """
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM condition_style_mapping")
        total_rows = cur.fetchone()[0]

    items = [
        {
            "gender":             row["gender"],
            "style_name":         row["style_name"],
            "style_code":         row["style_code"],
            "recommended_count":  row["recommended_count"],
            "worst_count":        row["worst_count"],
            "total_count":        row["total_count"],
        }
        for row in rows
    ]

    return {
        "items": items,
        "summary": {
            "total_rows":   total_rows,
            "total_styles": len(items),
        },
    }


def _query_hair_stats_raw() -> dict:
    """조건별 원시 매핑 데이터를 반환 — 프론트에서 다양한 집계에 사용."""
    with _get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                fc.gender,
                fc.face_shape,
                fc.face_proportion,
                hs.style_name,
                hs.style_code,
                csm.is_recommended
            FROM condition_style_mapping csm
            JOIN face_conditions fc ON csm.condition_id = fc.id
            JOIN hair_styles     hs ON csm.style_id     = hs.style_code
            ORDER BY fc.gender, fc.face_shape, fc.face_proportion, hs.style_name
            """
        )
        raw_rows = cur.fetchall()

        cur.execute(
            """
            SELECT gender, face_shape, face_proportion, COUNT(*) AS doc_count
            FROM face_conditions
            GROUP BY gender, face_shape, face_proportion
            ORDER BY gender, face_shape, face_proportion
            """
        )
        cond_rows = cur.fetchall()

        cur.execute(
            "SELECT DISTINCT face_shape FROM face_conditions ORDER BY face_shape"
        )
        face_shapes = [r[0] for r in cur.fetchall()]

        cur.execute(
            "SELECT DISTINCT face_proportion FROM face_conditions ORDER BY face_proportion"
        )
        face_proportions = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) FROM condition_style_mapping")
        total_rows = cur.fetchone()[0]

        cur.execute("SELECT style_code, style_name FROM hair_styles ORDER BY style_code")
        all_style_rows = cur.fetchall()

    items = [
        {
            "gender":          r["gender"],
            "face_shape":      r["face_shape"],
            "face_proportion": r["face_proportion"],
            "style_name":      r["style_name"],
            "style_code":      r["style_code"],
            "is_recommended":  bool(r["is_recommended"]),
        }
        for r in raw_rows
    ]

    condition_counts = [
        {
            "gender":          r["gender"],
            "face_shape":      r["face_shape"],
            "face_proportion": r["face_proportion"],
            "doc_count":       r["doc_count"],
        }
        for r in cond_rows
    ]

    all_hair_styles = [
        {"style_code": r["style_code"], "style_name": r["style_name"]}
        for r in all_style_rows
    ]

    return {
        "items":            items,
        "condition_counts": condition_counts,
        "face_shapes":      face_shapes,
        "face_proportions": face_proportions,
        "all_hair_styles":  all_hair_styles,
        "summary": {
            "total_rows":   total_rows,
            "total_styles": len(all_hair_styles),
        },
    }


def _query_hair_style_map() -> dict:
    """hair_styles 테이블의 style_name → style_code 매핑을 반환한다."""
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT style_code, style_name FROM hair_styles")
        rows = cur.fetchall()
    return {row["style_name"]: row["style_code"] for row in rows}


def _query_rag_coverage() -> dict:
    """ChromaDB의 style_groups 메타데이터에 등장하는 style_code 목록을 반환한다."""
    from apps.rag_core.retriever import get_covered_style_codes
    covered = get_covered_style_codes()
    return {"covered_codes": sorted(covered)}


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
        elif path == "/api/hair-stats-raw":
            self._handle_hair_stats_raw()
        elif path == "/api/hair-style-map":
            self._handle_hair_style_map()
        elif path == "/api/hair-rag-coverage":
            self._handle_rag_coverage()
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

    def _handle_hair_stats_raw(self) -> None:
        try:
            result = _query_hair_stats_raw()
            self._send_json(result)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _handle_hair_style_map(self) -> None:
        try:
            result = _query_hair_style_map()
            self._send_json(result)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _handle_rag_coverage(self) -> None:
        try:
            result = _query_rag_coverage()
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
