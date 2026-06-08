"""로컬 테스트용 HTTP 서버 (Python 표준 라이브러리 기반)

실행:
    uv run python -m apps.rag_test_front.server

접속:
    http://localhost:8000
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (uv run 환경에서도 apps.* 임포트 보장)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# .env 로드 (.env 파일 자체는 덮어쓰지 않음)
from dotenv import load_dotenv  # noqa: E402
load_dotenv(_PROJECT_ROOT / ".env")

# Django 설정 (apps.beauty 모델 등 임포트 체인에서 필요할 수 있음)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    import django
    django.setup()
except Exception as _django_err:
    print(f"[경고] Django setup 실패 (계속 진행): {_django_err}")

# RAG 서비스 임포트
from apps.analysis_rag.service import generate_analysis_result  # noqa: E402
from apps.chatbot_rag.graph import run_chatbot  # noqa: E402

_STATIC_DIR = Path(__file__).parent / "static"
_PORT = 8000

_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


class _RAGTestHandler(BaseHTTPRequestHandler):
    """GET(정적 파일) + POST(/api/*) 요청을 처리하는 핸들러."""

    server_version = "RAGTestServer/1.0"

    # ── GET ──────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._serve_static("index.html")
        elif self.path.startswith("/static/"):
            filename = self.path[len("/static/"):]
            self._serve_static(filename)
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

    # ── 정적 파일 서빙 ────────────────────────────────────────────────────────

    def _serve_static(self, filename: str) -> None:
        # 경로 탈출 방지
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

    # ── 요청 바디 파싱 ────────────────────────────────────────────────────────

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
    print(f"접속 주소: http://localhost:{_PORT}")
    print("종료: Ctrl+C")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료.")
        server.server_close()


if __name__ == "__main__":
    main()
