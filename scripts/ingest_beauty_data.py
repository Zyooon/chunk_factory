"""
독립형 데이터 적재 스크립트 — Beauty Hair Data Ingestion
=========================================================
실행 방법:
    uv run python scripts/ingest_beauty_data.py

사전 조건:
    1. uv run python scripts/ingest_beauty_data.py 실행 전, Django 마이그레이션이
       완료되어 있어야 합니다.
       (또는 이 스크립트가 자동으로 migrate 를 수행합니다 — AUTO_MIGRATE 참조)

    2. 외부 Django 프로젝트가 있다면 DJANGO_SETTINGS_MODULE 환경변수를 설정하세요.
       없으면 아래 INLINE_DJANGO_SETTINGS 를 사용하는 SQLite 기반 독립 모드로 동작합니다.

필요한 Django 모델 (models.py 참고용):
─────────────────────────────────────
    class AiRawDataJson(models.Model):
        \"\"\"AI 정제 원본 JSON 보관 테이블\"\"\"
        raw_json   = models.JSONField()
        uuid       = models.CharField(max_length=36, unique=True)
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            db_table = "ai_raw_data_json"

    class HairAnalysisLog(models.Model):
        \"\"\"헤어 스타일 통계/분석용 비정규화 테이블 (FK 없음)\"\"\"
        face_shape  = models.CharField(max_length=50)
        style_name  = models.CharField(max_length=100)
        gender      = models.CharField(max_length=10)
        style_type  = models.CharField(max_length=20, default='recommended', db_index=True)
        created_at  = models.DateTimeField(auto_now_add=True)

        class Meta:
            db_table = "hair_analysis_log"
─────────────────────────────────────
"""

import hashlib
import json
import os
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 1. 프로젝트 루트를 sys.path 에 추가 (어느 디렉터리에서 실행해도 동작)
# ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ──────────────────────────────────────────────────────────────
# 2. Django 설정 모듈 자동 탐색 → 없으면 인라인 설정으로 폴백
# ──────────────────────────────────────────────────────────────
_CANDIDATE_SETTINGS = [
    "config.settings",
    "config.settings.base",
    "core.settings",
    "settings",
]

_DB_PATH = PROJECT_ROOT / "db_beauty.sqlite3"

INLINE_DJANGO_SETTINGS = {
    "DATABASES": {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(_DB_PATH),
        }
    },
    "INSTALLED_APPS": [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "beauty",          # 인라인 모드에서 모델을 담을 앱 레이블
    ],
    "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
    "USE_TZ": True,
    "TIME_ZONE": "Asia/Seoul",
}


def _setup_django() -> bool:
    """
    Django 환경을 초기화한다.
    외부 settings 발견 → 해당 모듈 사용
    없으면 → 인라인 설정으로 SQLite 독립 모드 실행

    Returns:
        True  — 인라인 설정 모드 (migrate 자동 수행 필요)
        False — 외부 settings 모듈 모드
    """
    import django
    from django.conf import settings as django_settings

    # 2-a. 환경변수에 명시된 설정이 있으면 최우선 사용
    env_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if env_module:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", env_module)
        django.setup()
        print(f"[Django] 환경변수 설정 모듈 사용: {env_module}")
        return False

    # 2-b. 후보 경로를 순회하며 import 가능한 모듈 탐색
    for candidate in _CANDIDATE_SETTINGS:
        try:
            __import__(candidate)
            os.environ["DJANGO_SETTINGS_MODULE"] = candidate
            django.setup()
            print(f"[Django] 설정 모듈 자동 탐지: {candidate}")
            return False
        except ModuleNotFoundError:
            continue

    # 2-c. 탐색 실패 → 인라인 설정으로 독립 실행
    if not django_settings.configured:
        django_settings.configure(**INLINE_DJANGO_SETTINGS)
    django.setup()
    print(f"[Django] 인라인 SQLite 독립 모드: {_DB_PATH}")
    return True


# ──────────────────────────────────────────────────────────────
# 3. 인라인 모드 전용 모델 정의 (외부 앱 모델이 있으면 사용 안 함)
# ──────────────────────────────────────────────────────────────
def _get_models(inline_mode: bool):
    """
    실행 모드에 따라 적절한 모델 클래스를 반환한다.

    인라인 모드: 이 파일에서 동적으로 정의한 모델 사용
    외부 모드  : 실제 Django 앱의 models.py 에서 import
    """
    if inline_mode:
        from django.db import models

        class AiRawDataJson(models.Model):
            raw_json   = models.JSONField()
            uuid       = models.CharField(max_length=36, unique=True)
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "beauty"
                db_table  = "ai_raw_data_json"

        class HairAnalysisLog(models.Model):
            STYLE_TYPE_CHOICES = [
                ("recommended", "추천"),
                ("worst", "비추천"),
            ]
            face_shape  = models.CharField(max_length=50)
            style_name  = models.CharField(max_length=100)
            gender      = models.CharField(max_length=10)
            style_type  = models.CharField(
                max_length=20,
                choices=STYLE_TYPE_CHOICES,
                default="recommended",
                db_index=True,
            )
            created_at  = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "beauty"
                db_table  = "hair_analysis_log"

        return AiRawDataJson, HairAnalysisLog

    # 외부 Django 프로젝트가 있다면 실제 앱의 모델을 import
    # ↓ 실제 앱 경로에 맞게 수정하세요
    try:
        from apps.beauty.models import AiRawDataJson, HairAnalysisLog  # type: ignore[import]
        return AiRawDataJson, HairAnalysisLog
    except ImportError:
        # 앱 경로가 다를 경우 아래 주석을 참고해 경로를 조정하세요
        # from myapp.models import AiRawDataJson, HairAnalysisLog
        raise ImportError(
            "외부 settings 모드이지만 'apps.beauty.models' 를 import 할 수 없습니다.\n"
            "스크립트 내 _get_models() 함수의 import 경로를 실제 앱 경로로 수정해 주세요."
        )


# ──────────────────────────────────────────────────────────────
# 4. 데이터 파일 탐색
# ──────────────────────────────────────────────────────────────
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "cleaned"


def find_json_files() -> list[Path]:
    if not CLEANED_DATA_DIR.exists():
        print(f"[오류] 데이터 디렉터리가 없습니다: {CLEANED_DATA_DIR}")
        sys.exit(1)

    files = sorted(CLEANED_DATA_DIR.glob("*.json"))
    return files


# ──────────────────────────────────────────────────────────────
# 5. JSON 파싱 (배열형 / NDJSON 양쪽 모두 지원)
# ──────────────────────────────────────────────────────────────
def parse_json_file(path: Path) -> list[dict]:
    """
    파일 하나에서 모든 JSON 객체를 추출한다.
    - 대괄호로 묶인 배열(JSON Array) 형식
    - 줄바꿈으로 구분된 NDJSON 형식
    둘 다 처리한다.
    """
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    # 배열 형식 우선 시도
    if raw.startswith("["):
        return json.loads(raw)

    # NDJSON: 줄 단위로 파싱
    items = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"  [경고] {path.name} 라인 {line_no} JSON 파싱 실패: {e}")
    return items


# ──────────────────────────────────────────────────────────────
# 6. UUID 생성 (conditions + recommended_styles 기반 결정론적 해시)
# ──────────────────────────────────────────────────────────────
def make_record_uuid(record: dict) -> str:
    """
    동일한 원본 데이터에 대해 항상 동일한 UUID 를 반환하는 결정론적 함수.
    conditions + recommended_styles 의 직렬화 문자열을 SHA-256 으로 해시한 뒤
    UUID 형식(8-4-4-4-12)으로 포맷팅한다.
    """
    conditions       = record.get("conditions", {})
    recommended      = record.get("recommended_styles", [])
    fingerprint_str  = json.dumps(
        {"conditions": conditions, "recommended_styles": recommended},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()
    # SHA-256(64자) → UUID 포맷 32자 부분만 사용
    h = digest[:32]
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ──────────────────────────────────────────────────────────────
# 7. 단일 레코드 적재 (투 트랙)
# ──────────────────────────────────────────────────────────────
def ingest_record(
    record: dict,
    AiRawDataJson,
    HairAnalysisLog,
    stats: dict,
) -> None:
    """
    하나의 JSON 객체를 두 트랙으로 분리 적재한다.

    트랙 1 — AiRawDataJson : 원본 JSON 통째로 1행 인서트 (중복 UUID 시 스킵)
    트랙 2 — HairAnalysisLog : recommended_styles 개수만큼 행 분리 인서트
    """
    record_uuid = make_record_uuid(record)

    # ── 트랙 1: 중복 체크 후 원본 저장 ──────────────────────────
    if AiRawDataJson.objects.filter(uuid=record_uuid).exists():
        stats["skipped"] += 1
        return

    try:
        AiRawDataJson.objects.create(raw_json=record, uuid=record_uuid)
        stats["raw_inserted"] += 1
    except Exception as e:
        print(f"  [오류] AiRawDataJson 인서트 실패 (uuid={record_uuid}): {e}")
        stats["errors"] += 1
        return  # 원본 저장 실패 시 통계 적재도 건너뜀

    # ── 트랙 2: 스타일별 통계 행 분리 적재 (FK 없음) ─────────────
    face_shape      = record.get("conditions", {}).get("face_shape", "")
    gender          = record.get("gender", "")
    recommended     = record.get("recommended_styles", [])
    worst           = record.get("worst_styles", [])

    log_rows = []

    if not recommended and not worst:
        # 스타일이 전혀 없어도 face_shape / gender 정보는 빈 style_name 으로 1행 저장
        log_rows.append(HairAnalysisLog(
            face_shape=face_shape,
            style_name="",
            gender=gender,
            style_type="recommended",
        ))
    else:
        for style in recommended:
            log_rows.append(HairAnalysisLog(
                face_shape=face_shape,
                style_name=style.get("style_name", ""),
                gender=gender,
                style_type="recommended",
            ))
        for style in worst:
            log_rows.append(HairAnalysisLog(
                face_shape=face_shape,
                style_name=style.get("style_name", ""),
                gender=gender,
                style_type="worst",
            ))

    try:
        HairAnalysisLog.objects.bulk_create(log_rows)
        rec_count  = sum(1 for r in log_rows if r.style_type == "recommended")
        worst_count = sum(1 for r in log_rows if r.style_type == "worst")
        stats["recommended_inserted"] += rec_count
        stats["worst_inserted"]       += worst_count
    except Exception as e:
        print(f"  [오류] HairAnalysisLog 적재 실패 (uuid={record_uuid}): {e}")
        stats["errors"] += 1


# ──────────────────────────────────────────────────────────────
# 8. 인라인 모드 전용 — 테이블 자동 생성
# ──────────────────────────────────────────────────────────────
def _ensure_tables(AiRawDataJson, HairAnalysisLog) -> None:
    """인라인 SQLite 모드에서만 호출. migrate 없이 테이블을 직접 CREATE/ALTER."""
    from django.db import connection

    existing = connection.introspection.table_names()
    for model in (AiRawDataJson, HairAnalysisLog):
        table = model._meta.db_table
        if table not in existing:
            with connection.schema_editor() as editor:
                editor.create_model(model)
            print(f"  [DB] 테이블 생성: {table}")
        else:
            print(f"  [DB] 테이블 이미 존재: {table}")
            # style_type 컬럼이 없으면 추가 (스키마 업그레이드)
            if table == HairAnalysisLog._meta.db_table:
                col_names = [
                    col.name
                    for col in connection.introspection.get_table_description(
                        connection.cursor(), table
                    )
                ]
                if "style_type" not in col_names:
                    field = HairAnalysisLog._meta.get_field("style_type")
                    with connection.schema_editor() as editor:
                        editor.add_field(HairAnalysisLog, field)
                    print(f"  [DB] style_type 컬럼 추가: {table}")


# ──────────────────────────────────────────────────────────────
# 9. 메인 실행부
# ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("  Beauty Hair Data Ingestion — 투트랙 DB 적재 스크립트")
    print("=" * 60)

    # Django 초기화
    inline_mode = _setup_django()

    # 모델 클래스 획득
    AiRawDataJson, HairAnalysisLog = _get_models(inline_mode)

    # 인라인 모드: 테이블이 없으면 생성
    if inline_mode:
        _ensure_tables(AiRawDataJson, HairAnalysisLog)

    # 파일 탐색
    json_files = find_json_files()
    if not json_files:
        print(f"[정보] {CLEANED_DATA_DIR} 에 .json 파일이 없습니다. 종료합니다.")
        return

    print(f"\n[탐색] 총 {len(json_files)}개 파일 발견")
    for f in json_files:
        print(f"  - {f.name}")

    # 통계 카운터
    stats = {
        "raw_inserted":          0,
        "recommended_inserted":  0,
        "worst_inserted":        0,
        "skipped":               0,
        "errors":                0,
        "total_records":         0,
    }

    # 파일 순회
    print()
    for file_path in json_files:
        print(f"[처리] {file_path.name}")
        try:
            records = parse_json_file(file_path)
        except Exception as e:
            print(f"  [오류] 파일 읽기/파싱 실패: {e}")
            stats["errors"] += 1
            continue

        if not records:
            print("  [정보] 유효한 레코드 없음. 건너뜁니다.")
            continue

        print(f"  → {len(records)}개 레코드 파싱 완료")
        stats["total_records"] += len(records)

        for idx, record in enumerate(records):
            try:
                ingest_record(record, AiRawDataJson, HairAnalysisLog, stats)
            except Exception as e:
                print(f"  [오류] 레코드 #{idx + 1} 처리 중 예외 발생: {e}")
                stats["errors"] += 1

    # 최종 결과 출력
    total_log = stats["recommended_inserted"] + stats["worst_inserted"]
    print()
    print("=" * 60)
    print("  적재 완료 요약")
    print("=" * 60)
    print(f"  처리 대상 레코드  : {stats['total_records']:>6}건")
    print(f"  원본 테이블 적재  : {stats['raw_inserted']:>6}건  (AiRawDataJson)")
    print(f"  추천 스타일 적재  : {stats['recommended_inserted']:>6}건  (HairAnalysisLog / recommended)")
    print(f"  비추천 스타일 적재: {stats['worst_inserted']:>6}건  (HairAnalysisLog / worst)")
    print(f"  통계 테이블 합계  : {total_log:>6}건  (HairAnalysisLog)")
    print(f"  중복 스킵         : {stats['skipped']:>6}건")
    print(f"  오류              : {stats['errors']:>6}건")
    print("=" * 60)
    print(
        f"\n[적재 완료] 이번 배치에서 추천 스타일 {stats['recommended_inserted']}개, "
        f"비추천 스타일 {stats['worst_inserted']}개가 성공적으로 적재되었습니다."
    )

    if stats["errors"] > 0:
        print(f"[주의] {stats['errors']}건의 오류가 발생했습니다. 위 로그를 확인하세요.")


if __name__ == "__main__":
    main()
