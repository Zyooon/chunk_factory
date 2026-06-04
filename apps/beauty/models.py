from django.db import models


class AiRawDataJson(models.Model):
    raw_json = models.JSONField(help_text="AI가 생성한 정제 JSON 원본 통째로 저장")
    uuid = models.CharField(max_length=36, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_raw_data_json"


class HairAnalysisLog(models.Model):
    STYLE_TYPE_CHOICES = [
        ("recommended", "추천"),
        ("worst", "비추천"),
    ]

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
