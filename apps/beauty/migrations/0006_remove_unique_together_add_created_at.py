"""
0006 — unique_together 제거 + FaceCondition.created_at 추가

변경 내용:
  - FaceCondition: unique_together 제거, created_at(DateTimeField) 추가
  - ConditionStyleMapping: unique_together 제거
"""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beauty', '0005_hairstyle_facecondition_conditionstylemapping_and_more'),
    ]

    operations = [
        # ── FaceCondition: unique_together 제거 ───────────────────────────────
        migrations.AlterUniqueTogether(
            name='facecondition',
            unique_together=set(),
        ),

        # ── FaceCondition: created_at 추가 ────────────────────────────────────
        # 기존 row는 마이그레이션 시점의 now()로 채워짐 (이후 재적재로 리셋)
        migrations.AddField(
            model_name='facecondition',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),

        # ── ConditionStyleMapping: unique_together 제거 ───────────────────────
        migrations.AlterUniqueTogether(
            name='conditionstylemapping',
            unique_together=set(),
        ),

        # ── FaceCondition help_text 제거 (minor) ─────────────────────────────
        migrations.AlterField(
            model_name='facecondition',
            name='expert_reasoning_positive',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='facecondition',
            name='expert_reasoning_negative',
            field=models.TextField(blank=True, default=''),
        ),

        # ── ConditionStyleMapping help_text 제거 (minor) ─────────────────────
        migrations.AlterField(
            model_name='conditionstylemapping',
            name='is_recommended',
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
