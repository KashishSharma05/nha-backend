from django.db import models
from django.conf import settings


class Claim(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('verified',   'Verified'),
        ('rejected',   'Rejected'),
    ]

    DIAGNOSIS_CHOICES = [
        ('SG039C', 'Cholecystectomy'),
        ('MG006A', 'Enteric Fever'),
        ('MG064A', 'Severe Anemia'),
        ('SB039A', 'Total Knee Replacement (Primary)'),
        ('SB039B', 'Total Knee Replacement (Revision)'),
    ]

    # ── Core fields ─────────────────────────────────────────────────────────
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title       = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    document    = models.FileField(upload_to='claims/', blank=True, null=True)
    source      = models.CharField(max_length=50, blank=True, default='')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at  = models.DateTimeField(auto_now_add=True)

    # ── STG / Diagnosis ──────────────────────────────────────────────────────
    diagnosis_code   = models.CharField(max_length=10, choices=DIAGNOSIS_CHOICES, blank=True, default='')
    patient_age      = models.PositiveIntegerField(null=True, blank=True)
    alos             = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text="Actual Length of Stay (days)")
    hb_level         = models.FloatField(null=True, blank=True,
                                         help_text="Hemoglobin level in g/dL (for Severe Anemia)")
    claimed_amount   = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text="Amount claimed by hospital (₹)")

    # ── Mandatory document flags ─────────────────────────────────────────────
    has_diagnostic_report    = models.BooleanField(default=False,
        help_text="Ultrasound / Widal / Blood culture / X-ray / Hb lab report")
    has_clinical_notes       = models.BooleanField(default=False)
    has_indoor_case_papers   = models.BooleanField(default=False)
    has_operative_note       = models.BooleanField(default=False)
    has_discharge_summary    = models.BooleanField(default=False)
    has_treatment_records    = models.BooleanField(default=False,
        help_text="Antibiotic records / Blood transfusion / Iron injection")
    has_post_treatment_report = models.BooleanField(default=False,
        help_text="Post-op X-ray / Post-treatment Hb report")
    has_histopathology_report = models.BooleanField(default=False,
        help_text="Required for Cholecystectomy")
    has_cbc_report            = models.BooleanField(default=False,
        help_text="Required for Enteric Fever")
    has_implant_invoice       = models.BooleanField(default=False,
        help_text="Required for TKR — implant barcode/invoice")
    has_preop_xray            = models.BooleanField(default=False,
        help_text="Required for Revision TKR only")

    def __str__(self):
        return self.title or f"Claim #{self.id}"