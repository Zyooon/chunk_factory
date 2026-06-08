from django.db import models


# ──────────────────────────────────────────────────────────────
# [기존 모델] 서비스 하위 호환성 및 통계용 로그 테이블
# ──────────────────────────────────────────────────────────────

class AiRawDataJson(models.Model):
    raw_json = models.JSONField(help_text="AI가 생성한 정제 JSON 원본 통째로 저장")
    uuid = models.CharField(max_length=36, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_raw_data_json"


class HairAnalysisLog(models.Model):
    STYLE_TYPE_CHOICES = [("recommended", "추천"), ("worst", "비추천")]
    gender = models.CharField(max_length=10)
    face_shape = models.CharField(max_length=50, db_index=True)
    face_proportion = models.CharField(max_length=50, blank=True, default="")
    style_name = models.CharField(max_length=100)
    style_type = models.CharField(
        max_length=20,
        choices=STYLE_TYPE_CHOICES,
        default="recommended",
        db_index=True,
    )

    class Meta:
        db_table = "hair_analysis_log"


# ──────────────────────────────────────────────────────────────
# [신규 모델] 누적 집계용 정규화 테이블 (unique_together 없음)
# ──────────────────────────────────────────────────────────────

class FaceCondition(models.Model):
    """얼굴 조건 테이블 — 분석 요청마다 독립 Row로 누적"""
    gender = models.CharField(max_length=10)
    face_shape = models.CharField(max_length=50, db_index=True)
    face_proportion = models.CharField(max_length=50, blank=True, default="")
    expert_reasoning_positive = models.TextField(blank=True, default="")
    expert_reasoning_negative = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "face_conditions"


class HairStyle(models.Model):
    """헤어스타일 마스터 테이블 — 종류별 단일 Row (get_or_create 유지)"""
    style_code = models.CharField(max_length=20, primary_key=True)
    style_name = models.CharField(max_length=100)

    class Meta:
        db_table = "hair_styles"


class ConditionStyleMapping(models.Model):
    """얼굴 조건과 헤어스타일 간의 매핑 — 분석 요청마다 독립 Row로 누적"""
    condition = models.ForeignKey(
        FaceCondition,
        on_delete=models.CASCADE,
        related_name="style_mappings",
    )
    style = models.ForeignKey(
        HairStyle,
        on_delete=models.CASCADE,
        related_name="condition_mappings",
    )
    is_recommended = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "condition_style_mapping"


class StyleFeature(models.Model):
    """각 매핑 조건별 세부 스타일 특징 리스트"""
    mapping = models.ForeignKey(
        ConditionStyleMapping,
        on_delete=models.CASCADE,
        related_name="features",
    )
    feature_description = models.CharField(max_length=255)

    class Meta:
        db_table = "style_features"
