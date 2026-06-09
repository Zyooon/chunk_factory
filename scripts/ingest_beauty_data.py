"""
Beauty Hair RAG 데이터 import/export 스크립트
=========================================

새 done.json flat 스키마를 SQLite DB에 저장하고,
DB 데이터를 다시 done.json 형태로 복원한다.

실행 예시:
    # JSON -> DB
    uv run python scripts/ingest_beauty_data.py --mode import

    # DB -> JSON
    uv run python scripts/ingest_beauty_data.py --mode export

    # JSON -> DB -> JSON
    uv run python scripts/ingest_beauty_data.py --mode roundtrip

    # 기존 beauty_hair_rag_records를 비우고 다시 import
    uv run python scripts/ingest_beauty_data.py --mode import --replace
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_DB_PATH = PROJECT_ROOT / "db_beauty.sqlite3"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "cleaned" / "done.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "cleaned" / "done_from_db.json"

TABLE_NAME = "beauty_hair_rag_records"

# 이전 정규화 구조에서 사용하던 테이블이다.
# 새 flat RAG 스키마에서는 단일 row가 곧 하나의 RAG record이므로 사용하지 않는다.
UNUSED_TABLES = [
    "style_features",
    "condition_style_mapping",
    "face_conditions",
    "hair_styles",
    "ai_raw_data_json",
]

SCALAR_FIELDS = [
    "category",
    "gender",
    "face_shape",
    "face_proportion",
    "style_code",
    "style_name",
    "relation",
    "source_type",
    "confidence_level",
    "reason_summary",
    "reason_detail",
    "reason_source",
]

ARRAY_FIELDS = [
    "style_features",
    "styling_tips",
    "cautions",
    "good_variants",
    "avoid_variants",
]

BOOLEAN_FIELDS = [
    "needs_reason_fill",
    "needs_review",
]

DEFAULT_VALUES: dict[str, Any] = {
    "category": "hair",
    "gender": "",
    "face_shape": "",
    "face_proportion": "",
    "style_code": "",
    "style_name": "",
    "relation": "recommended",
    "source_type": "",
    "confidence_level": "",
    "reason_summary": "",
    "reason_detail": "",
    "reason_source": "",
    "style_features": [],
    "styling_tips": [],
    "cautions": [],
    "good_variants": [],
    "avoid_variants": [],
    "needs_reason_fill": False,
    "needs_review": False,
}


# ---------------------------------------------------------------------
# JSON 파싱 / 직렬화 유틸
# ---------------------------------------------------------------------
def parse_json_file(path: Path) -> list[dict[str, Any]]:
    """JSON 배열 또는 JSONL 형식 파일을 list[dict]로 읽는다."""
    if not path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {path}")

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    if raw.startswith("["):
        data = json.loads(raw)
    else:
        data = []
        for line_no, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path.name} {line_no}번째 줄 JSON 파싱 실패: {exc}"
                ) from exc

    if not isinstance(data, list):
        raise ValueError(f"최상위 JSON은 list여야 합니다. 현재 타입: {type(data).__name__}")

    invalid_indexes = [idx for idx, item in enumerate(data) if not isinstance(item, dict)]
    if invalid_indexes:
        raise ValueError(f"dict가 아닌 항목이 있습니다. 문제 인덱스: {invalid_indexes[:10]}")

    return data


def write_json_file(path: Path, records: list[dict[str, Any]]) -> None:
    """list[dict]를 보기 좋은 done.json 형식으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n", ""}:
            return False
    return bool(value)


def _array_to_db_text(value: Any) -> str:
    """
    배열 필드를 DB Text 컬럼에 저장할 문자열로 변환한다.

    DB에는 문자열 그대로 저장하지만, export 시 다시 배열로 복원할 수 있도록
    JSON 문자열 형태를 사용한다.
    """
    if value is None:
        items: list[Any] = []
    elif isinstance(value, list):
        items = value
    else:
        items = [value]

    return json.dumps(items, ensure_ascii=False)


def _db_text_to_array(value: Any) -> list[Any]:
    """
    DB Text 컬럼의 문자열을 다시 배열로 복원한다.

    기본은 JSON 문자열을 역직렬화한다. 과거에 일반 문자열이 들어간 경우도
    데이터 손실을 피하기 위해 단일 원소 배열로 복원한다.
    """
    if value is None:
        return []

    text = str(value).strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]

    if isinstance(parsed, list):
        return parsed

    if parsed is None:
        return []

    return [parsed]


# ---------------------------------------------------------------------
# 레코드 정규화
# ---------------------------------------------------------------------
def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """새 flat JSON 스키마를 DB 저장용 dict로 정규화한다."""
    normalized: dict[str, Any] = {}

    for field in SCALAR_FIELDS:
        normalized[field] = _safe_text(record.get(field), DEFAULT_VALUES[field])

    for field in ARRAY_FIELDS:
        normalized[field] = _array_to_db_text(record.get(field, DEFAULT_VALUES[field]))

    for field in BOOLEAN_FIELDS:
        normalized[field] = _safe_bool(record.get(field), DEFAULT_VALUES[field])

    return normalized


def record_to_json(row: sqlite3.Row) -> dict[str, Any]:
    """DB row를 다시 새 done.json 객체로 복원한다."""
    record: dict[str, Any] = {}

    for field in SCALAR_FIELDS:
        record[field] = row[field] or DEFAULT_VALUES[field]

    for field in ARRAY_FIELDS:
        record[field] = _db_text_to_array(row[field])

    for field in BOOLEAN_FIELDS:
        record[field] = bool(row[field])

    return record


def make_record_key(record: dict[str, Any]) -> str:
    """중복 방지를 위한 stable key를 생성한다."""
    fingerprint = {
        "category": record.get("category", ""),
        "gender": record.get("gender", ""),
        "face_shape": record.get("face_shape", ""),
        "face_proportion": record.get("face_proportion", ""),
        "style_code": record.get("style_code", ""),
        "relation": record.get("relation", "recommended"),
    }
    fingerprint_str = json.dumps(fingerprint, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# DB 스키마
# ---------------------------------------------------------------------
def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def drop_unused_tables(conn: sqlite3.Connection) -> None:
    """이전 정규화 구조에서 쓰던 테이블을 제거한다."""
    for table_name in UNUSED_TABLES:
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.commit()


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row["name"] for row in rows}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _drop_legacy_record_table_if_needed(conn: sqlite3.Connection) -> None:
    """
    이전 버전의 beauty_hair_rag_records는 uuid TEXT PRIMARY KEY 구조였다.
    새 구조는 id INTEGER PK + record_key UNIQUE 구조이므로, 로컬 테스트 DB에
    구버전 테이블이 있으면 안전하게 새 테이블로 다시 만들 수 있게 제거한다.
    """
    if not _table_exists(conn, TABLE_NAME):
        return

    columns = _table_columns(conn, TABLE_NAME)
    if "id" in columns and "record_key" in columns:
        return

    conn.execute(f'DROP TABLE IF EXISTS "{TABLE_NAME}"')
    conn.commit()
    print(f"  [DB] 구버전 {TABLE_NAME} 테이블 제거 완료")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """새 flat RAG record 저장용 단일 테이블을 생성한다."""
    _drop_legacy_record_table_if_needed(conn)

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_key TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'hair',
            gender TEXT NOT NULL DEFAULT '',
            face_shape TEXT NOT NULL DEFAULT '',
            face_proportion TEXT NOT NULL DEFAULT '',
            style_code TEXT NOT NULL DEFAULT '',
            style_name TEXT NOT NULL DEFAULT '',
            relation TEXT NOT NULL DEFAULT 'recommended',
            source_type TEXT NOT NULL DEFAULT '',
            confidence_level TEXT NOT NULL DEFAULT '',
            style_features TEXT NOT NULL DEFAULT '[]',
            reason_summary TEXT NOT NULL DEFAULT '',
            reason_detail TEXT NOT NULL DEFAULT '',
            styling_tips TEXT NOT NULL DEFAULT '[]',
            cautions TEXT NOT NULL DEFAULT '[]',
            good_variants TEXT NOT NULL DEFAULT '[]',
            avoid_variants TEXT NOT NULL DEFAULT '[]',
            reason_source TEXT NOT NULL DEFAULT '',
            needs_reason_fill INTEGER NOT NULL DEFAULT 0,
            needs_review INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_lookup
        ON {TABLE_NAME} (
            category,
            gender,
            face_shape,
            face_proportion,
            style_code,
            relation
        )
        """
    )
    conn.commit()


def reset_record_table(conn: sqlite3.Connection) -> None:
    conn.execute(f"DELETE FROM {TABLE_NAME}")
    conn.execute(f"DELETE FROM sqlite_sequence WHERE name = ?", (TABLE_NAME,))
    conn.commit()


# ---------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------
def import_records(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
) -> dict[str, int]:
    stats = {
        "total": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    now = datetime.now().isoformat(timespec="seconds")

    for record in records:
        stats["total"] += 1
        try:
            normalized = normalize_record(record)
            record_key = make_record_key(normalized)

            existing = conn.execute(
                f"SELECT id FROM {TABLE_NAME} WHERE record_key = ?",
                (record_key,),
            ).fetchone()

            values = {
                **normalized,
                "record_key": record_key,
                "created_at": now,
                "updated_at": now,
                "needs_reason_fill": int(normalized["needs_reason_fill"]),
                "needs_review": int(normalized["needs_review"]),
            }

            if existing:
                conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET
                        category = :category,
                        gender = :gender,
                        face_shape = :face_shape,
                        face_proportion = :face_proportion,
                        style_code = :style_code,
                        style_name = :style_name,
                        relation = :relation,
                        source_type = :source_type,
                        confidence_level = :confidence_level,
                        style_features = :style_features,
                        reason_summary = :reason_summary,
                        reason_detail = :reason_detail,
                        styling_tips = :styling_tips,
                        cautions = :cautions,
                        good_variants = :good_variants,
                        avoid_variants = :avoid_variants,
                        reason_source = :reason_source,
                        needs_reason_fill = :needs_reason_fill,
                        needs_review = :needs_review,
                        updated_at = :updated_at
                    WHERE record_key = :record_key
                    """,
                    values,
                )
                stats["updated"] += 1
            else:
                conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        record_key,
                        category,
                        gender,
                        face_shape,
                        face_proportion,
                        style_code,
                        style_name,
                        relation,
                        source_type,
                        confidence_level,
                        style_features,
                        reason_summary,
                        reason_detail,
                        styling_tips,
                        cautions,
                        good_variants,
                        avoid_variants,
                        reason_source,
                        needs_reason_fill,
                        needs_review,
                        created_at,
                        updated_at
                    ) VALUES (
                        :record_key,
                        :category,
                        :gender,
                        :face_shape,
                        :face_proportion,
                        :style_code,
                        :style_name,
                        :relation,
                        :source_type,
                        :confidence_level,
                        :style_features,
                        :reason_summary,
                        :reason_detail,
                        :styling_tips,
                        :cautions,
                        :good_variants,
                        :avoid_variants,
                        :reason_source,
                        :needs_reason_fill,
                        :needs_review,
                        :created_at,
                        :updated_at
                    )
                    """,
                    values,
                )
                stats["inserted"] += 1

        except Exception as exc:
            stats["errors"] += 1
            print(f"  [오류] record import 실패: {exc}")

    conn.commit()
    return stats


def export_records(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT *
        FROM {TABLE_NAME}
        ORDER BY id
        """
    ).fetchall()

    return [record_to_json(row) for row in rows]


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Beauty Hair RAG flat JSON 데이터를 SQLite DB와 상호 변환합니다."
    )
    parser.add_argument(
        "--mode",
        choices=["import", "export", "roundtrip"],
        default="import",
        help="import: JSON -> DB, export: DB -> JSON, roundtrip: JSON -> DB -> JSON",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"입력 JSON 경로. 기본값: {DEFAULT_INPUT_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"export JSON 경로. 기본값: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite DB 경로. 기본값: {DEFAULT_DB_PATH}",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="import 전 beauty_hair_rag_records 테이블을 비웁니다.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    print("=" * 60)
    print("  Beauty Hair RAG Data Import/Export")
    print("=" * 60)
    print(f"  mode  : {args.mode}")
    print(f"  db    : {args.db}")

    with connect_db(args.db) as conn:
        drop_unused_tables(conn)
        ensure_schema(conn)

        if args.mode in {"import", "roundtrip"}:
            print(f"  input : {args.input}")
            if args.replace:
                reset_record_table(conn)
                print("  기존 beauty_hair_rag_records 데이터 삭제 완료")

            records = parse_json_file(args.input)
            stats = import_records(conn, records)
            print("-" * 60)
            print("  Import 완료")
            print(f"  전체    : {stats['total']:>6}건")
            print(f"  신규    : {stats['inserted']:>6}건")
            print(f"  업데이트: {stats['updated']:>6}건")
            print(f"  오류    : {stats['errors']:>6}건")

        if args.mode in {"export", "roundtrip"}:
            print(f"  output: {args.output}")
            exported = export_records(conn)
            write_json_file(args.output, exported)
            print("-" * 60)
            print("  Export 완료")
            print(f"  출력 레코드: {len(exported):>6}건")

    print("=" * 60)
    print("  완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
