"""
독립형 데이터 적재 스크립트 — Beauty Hair Data Ingestion (정규화 모델 버전)
========================================================================
실행 방법:
    uv run python scripts/ingest_beauty_data.py
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 1. 프로젝트 루트를 sys.path 에 추가
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
        "beauty",  
    ],
    "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
    "USE_TZ": True,
    "TIME_ZONE": "Asia/Seoul",
}


def _setup_django() -> bool:
    import django
    from django.conf import settings as django_settings

    env_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if env_module:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", env_module)
        django.setup()
        print(f"[Django] 환경변수 설정 모듈 사용: {env_module}")
        return False

    for candidate in _CANDIDATE_SETTINGS:
        try:
            __import__(candidate)
            os.environ["DJANGO_SETTINGS_MODULE"] = candidate
            django.setup()
            print(f"[Django] 설정 모듈 자동 탐지: {candidate}")
            return False
        except ModuleNotFoundError:
            continue

    if not django_settings.configured:
        django_settings.configure(**INLINE_DJANGO_SETTINGS)
    django.setup()
    print(f"[Django] 인라인 SQLite 독립 모드: {_DB_PATH}")
    return True


# ──────────────────────────────────────────────────────────────
# 3. 모델 정의 (인라인 모드 동적 생성 및 외부 임포트 대응)
# ──────────────────────────────────────────────────────────────
def _get_models(inline_mode: bool):
    if inline_mode:
        from django.db import models

        class AiRawDataJson(models.Model):
            raw_json   = models.JSONField()
            uuid       = models.CharField(max_length=36, unique=True)
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "beauty"
                db_table  = "ai_raw_data_json"

        class FaceCondition(models.Model):
            gender                    = models.CharField(max_length=10)
            face_shape                = models.CharField(max_length=50)
            face_proportion           = models.CharField(max_length=50)
            expert_reasoning_positive = models.TextField(blank=True, default="")
            expert_reasoning_negative = models.TextField(blank=True, default="")
            created_at                = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "beauty"
                db_table  = "face_conditions"
                # unique_together 제거 — 분석 요청마다 독립 Row 누적

        class HairStyle(models.Model):
            style_code = models.CharField(max_length=20, primary_key=True)
            style_name = models.CharField(max_length=100)

            class Meta:
                app_label = "beauty"
                db_table  = "hair_styles"

        class ConditionStyleMapping(models.Model):
            condition      = models.ForeignKey(FaceCondition, on_delete=models.CASCADE)
            style          = models.ForeignKey(HairStyle, on_delete=models.CASCADE)
            is_recommended = models.BooleanField(default=True)

            class Meta:
                app_label = "beauty"
                db_table  = "condition_style_mapping"
                # unique_together 제거 — 분석 요청마다 독립 Row 누적

        class StyleFeature(models.Model):
            mapping             = models.ForeignKey(ConditionStyleMapping, on_delete=models.CASCADE, related_name="features")
            feature_description = models.CharField(max_length=255)

            class Meta:
                app_label = "beauty"
                db_table  = "style_features"

        return AiRawDataJson, FaceCondition, HairStyle, ConditionStyleMapping, StyleFeature

    try:
        from apps.beauty.models import (
            AiRawDataJson, FaceCondition, HairStyle, ConditionStyleMapping, StyleFeature
        )
        return AiRawDataJson, FaceCondition, HairStyle, ConditionStyleMapping, StyleFeature
    except ImportError:
        raise ImportError("외부 settings 모드이지만 모델을 import 할 수 없습니다. 경로를 수정해 주세요.")


# ──────────────────────────────────────────────────────────────
# 4. 데이터 파일 탐색 및 파싱
# ──────────────────────────────────────────────────────────────
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "cleaned"
HAIRSTYLE_GROUP_PATH = PROJECT_ROOT / "data" / "hairstyle_group.md"


def parse_hairstyle_group() -> list[tuple[str, str]]:
    """hairstyle_group.md 테이블 행에서 (style_code, style_name) 목록을 파싱한다."""
    if not HAIRSTYLE_GROUP_PATH.exists():
        print(f"  [경고] hairstyle_group.md 파일을 찾을 수 없습니다: {HAIRSTYLE_GROUP_PATH}")
        return []
    pattern = re.compile(r"^\|\s*((?:f|m)-\d+)\s*\|\s*(\S+)\s*\|")
    styles: list[tuple[str, str]] = []
    for line in HAIRSTYLE_GROUP_PATH.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line.strip())
        if m:
            styles.append((m.group(1), m.group(2)))
    return styles


def _ensure_all_hair_styles(HairStyle) -> None:
    """hairstyle_group.md의 모든 스타일이 hair_styles 테이블에 있도록 보장한다.

    done.json 유무에 관계없이 항상 호출된다.
    """
    styles = parse_hairstyle_group()
    if not styles:
        return
    added = 0
    for code, name in styles:
        _, created = HairStyle.objects.get_or_create(
            style_code=code,
            defaults={"style_name": name},
        )
        if created:
            added += 1
    print(f"  [보장] hair_styles 전체 {len(styles)}개 확인 / 신규 추가 {added}개")


def find_json_files() -> list[Path]:
    if not CLEANED_DATA_DIR.exists():
        print(f"[오류] 데이터 디렉터리가 없습니다: {CLEANED_DATA_DIR}")
        sys.exit(1)
    return sorted(CLEANED_DATA_DIR.glob("done.json"))


def parse_json_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw.startswith("["):
        return json.loads(raw)
    
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


def make_record_uuid(record: dict) -> str:
    conditions       = record.get("conditions", {})
    recommended      = record.get("recommended_styles", [])
    fingerprint_str  = json.dumps(
        {"conditions": conditions, "recommended_styles": recommended},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()
    h = digest[:32]
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ──────────────────────────────────────────────────────────────
# 5. 관계형 데이터 적재 로직
# ──────────────────────────────────────────────────────────────
def ingest_record(record: dict, models_tuple: tuple, stats: dict) -> None:
    from django.db import transaction
    AiRawDataJson, FaceCondition, HairStyle, ConditionStyleMapping, StyleFeature = models_tuple

    record_uuid = make_record_uuid(record)

    if AiRawDataJson.objects.filter(uuid=record_uuid).exists():
        stats["skipped"] += 1
        return

    try:
        with transaction.atomic():
            # 트랙 1: 원본 로그 저장
            AiRawDataJson.objects.create(raw_json=record, uuid=record_uuid)
            stats["raw_inserted"] += 1

            # 트랙 2: 관계형 구조 분해 적재
            gender = record.get("gender", "")
            conditions = record.get("conditions", {})
            face_shape = conditions.get("face_shape", "")
            face_proportion = conditions.get("face_proportion", "")
            pos_reasoning = record.get("expert_reasoning_positive", "")
            neg_reasoning = record.get("expert_reasoning_negative", "")

            # ① 얼굴 조건 — 분석 요청마다 독립 Row 생성 (누적 집계 목적)
            condition_obj = FaceCondition.objects.create(
                gender=gender,
                face_shape=face_shape,
                face_proportion=face_proportion,
                expert_reasoning_positive=pos_reasoning,
                expert_reasoning_negative=neg_reasoning,
            )

            def _process_styles(styles_list, is_rec):
                for s in styles_list:
                    code = s.get("style_code")
                    name = s.get("style_name")
                    features = s.get("style_features", [])

                    if not code or not name:
                        continue

                    # ② 스타일 마스터 — 종류별 단일 Row 유지 (get_or_create 유지)
                    style_obj, _ = HairStyle.objects.get_or_create(
                        style_code=code,
                        defaults={"style_name": name},
                    )

                    # ③ 조건-스타일 매핑 — 분석 요청마다 독립 Row 생성 (누적 집계 목적)
                    mapping_obj = ConditionStyleMapping.objects.create(
                        condition=condition_obj,
                        style=style_obj,
                        is_recommended=is_rec,
                    )

                    # ④ 스타일 특징 등록
                    feature_objs = [
                        StyleFeature(mapping=mapping_obj, feature_description=f)
                        for f in features
                    ]
                    if feature_objs:
                        StyleFeature.objects.bulk_create(feature_objs)

                    if is_rec:
                        stats["recommended_inserted"] += 1
                    else:
                        stats["worst_inserted"] += 1

            _process_styles(record.get("recommended_styles", []), is_rec=True)
            _process_styles(record.get("worst_styles", []), is_rec=False)

    except Exception as e:
        print(f"  [오류] 데이터 적재 실패 (uuid={record_uuid}): {e}")
        stats["errors"] += 1


# ──────────────────────────────────────────────────────────────
# 6. 인라인 모드 전용 — 테이블 자동 생성
# ──────────────────────────────────────────────────────────────
def _ensure_tables(models_tuple: tuple) -> None:
    from django.db import connection
    existing = connection.introspection.table_names()
    
    for model in models_tuple:
        table = model._meta.db_table
        if table not in existing:
            with connection.schema_editor() as editor:
                editor.create_model(model)
            print(f"  [DB] 테이블 생성 완료: {table}")


# ──────────────────────────────────────────────────────────────
# 7. 메인 실행부
# ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("  Beauty Hair Data Ingestion - 정규화 DB 구조 적재")
    print("=" * 60)

    inline_mode = _setup_django()
    models_tuple = _get_models(inline_mode)

    if inline_mode:
        _ensure_tables(models_tuple)

    # done.json 유무와 무관하게 hairstyle_group.md 전체 스타일을 항상 보장
    _, _, HairStyle, _, _ = models_tuple
    _ensure_all_hair_styles(HairStyle)

    json_files = find_json_files()
    if not json_files:
        print(f"[정보] 데이터 디렉터리에 .json 파일이 없습니다.")
        return

    stats = {
        "raw_inserted": 0,
        "recommended_inserted": 0,
        "worst_inserted": 0,
        "skipped": 0,
        "errors": 0,
        "total_records": 0,
    }

    for file_path in json_files:
        print(f"[처리] {file_path.name}")
        try:
            records = parse_json_file(file_path)
        except Exception as e:
            print(f"  [오류] 파일 파싱 실패: {e}")
            stats["errors"] += 1
            continue

        if not records:
            continue

        stats["total_records"] += len(records)

        for idx, record in enumerate(records):
            ingest_record(record, models_tuple, stats)

    # 대입문 오타(=)가 있던 부분을 올바르게 수정했어요
    divider = "=" * 60
    print(divider)
    print("  적재 완료 요약")
    print(divider)
    print(f"  처리 대상 레코드    : {stats['total_records']:>6}건")
    print(f"  원본 로그 테이블 적재 : {stats['raw_inserted']:>6}건  (AiRawDataJson)")
    print(f"  매핑된 추천 스타일 수 : {stats['recommended_inserted']:>6}건")
    print(f"  매핑된 비추천 스타일 수: {stats['worst_inserted']:>6}건")
    print(f"  중복 스킵           : {stats['skipped']:>6}건")
    print(f"  오류 발생           : {stats['errors']:>6}건")
    print(divider)


if __name__ == "__main__":
    main()