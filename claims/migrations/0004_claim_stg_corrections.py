"""Migration: Add missing STG fields from full PDF extraction."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0003_claim_stg_medical_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='claim', name='ward_type',
            field=models.CharField(max_length=20, blank=True, default='general_ward',
                choices=[('general_ward','General Ward'),('hdu','HDU'),
                         ('icu','ICU without Ventilator'),('icu_ventilator','ICU with Ventilator')]),
        ),
        migrations.AddField(
            model_name='claim', name='has_lft_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim', name='has_pre_anesthesia_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim', name='has_postop_photo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim', name='has_previous_cholecystectomy',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim', name='fever_duration_days',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        # Expand diagnosis_code choices
        migrations.AlterField(
            model_name='claim', name='diagnosis_code',
            field=models.CharField(max_length=10, blank=True, default='',
                choices=[
                    ('SG039A','Cholecystectomy — Open (No CBD)'),
                    ('SG039B','Cholecystectomy — Open (With CBD)'),
                    ('SG039C','Cholecystectomy — Laparoscopic (No CBD)'),
                    ('SG039D','Cholecystectomy — Laparoscopic (With CBD)'),
                    ('MG006A','Enteric Fever'),
                    ('MG001A','Acute Febrile Illness'),
                    ('MG026A','Pyrexia of Unknown Origin'),
                    ('MG064A','Severe Anemia'),
                    ('SB039A','Total Knee Replacement (Primary)'),
                    ('SB039B','Total Knee Replacement (Revision)'),
                ]),
        ),
    ]
