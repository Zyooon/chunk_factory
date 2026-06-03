from django.db import models


class AiRawDataJson(models.Model):
    raw_json = models.JSONField(help_text="AI가 생성한 정제 JSON 원본 통째로 저장")
    uuid = models.CharField(max_length=36, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_raw_data_json"


class HairAnalysisLog(models.Model):
    gender = models.CharField(max_length=10)
    face_shape = models.CharField(max_length=50, db_index=True)
    style_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hair_analysis_log"
