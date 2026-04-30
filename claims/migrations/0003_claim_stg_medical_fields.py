"""Migration: Add STG medical data fields to Claim model"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0002_alter_claim_fields'),
    ]

    operations = [
        # STG diagnosis code
        migrations.AddField(
            model_name='claim',
            name='diagnosis_code',
            field=models.CharField(
                blank=True, default='', max_length=10,
                choices=[
                    ('SG039C', 'Cholecystectomy'),
                    ('MG006A', 'Enteric Fever'),
                    ('MG064A', 'Severe Anemia'),
                    ('SB039A', 'Total Knee Replacement (Primary)'),
                    ('SB039B', 'Total Knee Replacement (Revision)'),
                ]
            ),
        ),
        migrations.AddField(
            model_name='claim',
            name='patient_age',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='claim',
            name='alos',
            field=models.PositiveIntegerField(blank=True, null=True,
                help_text='Actual Length of Stay (days)'),
        ),
        migrations.AddField(
            model_name='claim',
            name='hb_level',
            field=models.FloatField(blank=True, null=True,
                help_text='Hemoglobin level in g/dL (for Severe Anemia)'),
        ),
        migrations.AddField(
            model_name='claim',
            name='claimed_amount',
            field=models.PositiveIntegerField(blank=True, null=True,
                help_text='Amount claimed by hospital (₹)'),
        ),
        # Mandatory document flags
        migrations.AddField(
            model_name='claim',
            name='has_diagnostic_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_clinical_notes',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_indoor_case_papers',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_operative_note',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_discharge_summary',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_treatment_records',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_post_treatment_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_histopathology_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_cbc_report',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_implant_invoice',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='claim',
            name='has_preop_xray',
            field=models.BooleanField(default=False),
        ),
    ]
