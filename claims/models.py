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
        ('SG039A', 'Cholecystectomy — Open (No CBD)'),
        ('SG039B', 'Cholecystectomy — Open (With CBD)'),
        ('SG039C', 'Cholecystectomy — Laparoscopic (No CBD)'),
        ('SG039D', 'Cholecystectomy — Laparoscopic (With CBD)'),
        ('MG006A', 'Enteric Fever'),
        ('MG001A', 'Acute Febrile Illness'),
        ('MG026A', 'Pyrexia of Unknown Origin'),
        ('MG064A', 'Severe Anemia'),
        ('SB039A', 'Total Knee Replacement (Primary)'),
        ('SB039B', 'Total Knee Replacement (Revision)'),
    ]

    WARD_CHOICES = [
        ('general_ward',   'General Ward'),
        ('hdu',            'HDU'),
        ('icu',            'ICU without Ventilator'),
        ('icu_ventilator', 'ICU with Ventilator'),
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
    ward_type        = models.CharField(max_length=20, choices=WARD_CHOICES, blank=True, default='general_ward')
    patient_age      = models.PositiveIntegerField(null=True, blank=True)
    alos             = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text="Actual Length of Stay (days)")
    hb_level         = models.FloatField(null=True, blank=True,
                                         help_text="Hemoglobin level in g/dL (for Severe Anemia)")
    claimed_amount   = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text="Amount claimed by hospital (₹)")

    # ── Mandatory document flags ─────────────────────────────────────────────
    has_diagnostic_report     = models.BooleanField(default=False,
        help_text="USG / CBC+ESR+LFT / X-ray / Hb report")
    has_clinical_notes        = models.BooleanField(default=False)
    has_indoor_case_papers    = models.BooleanField(default=False)
    has_operative_note        = models.BooleanField(default=False)
    has_discharge_summary     = models.BooleanField(default=False)
    has_treatment_records     = models.BooleanField(default=False,
        help_text="Antibiotic records / Blood transfusion / Iron injection")
    has_post_treatment_report = models.BooleanField(default=False,
        help_text="Post-op X-ray / Post-treatment Hb / Intra-op photo")
    has_histopathology_report = models.BooleanField(default=False,
        help_text="Required for Cholecystectomy")
    has_cbc_report            = models.BooleanField(default=False,
        help_text="Required for Enteric Fever")
    has_implant_invoice       = models.BooleanField(default=False,
        help_text="Required for TKR — implant barcode/invoice")
    has_preop_xray            = models.BooleanField(default=False,
        help_text="Required for Revision TKR only")
    # New fields from full PDF extraction
    has_lft_report            = models.BooleanField(default=False,
        help_text="Liver Function Test — required for Cholecystectomy")
    has_pre_anesthesia_report = models.BooleanField(default=False,
        help_text="Pre-anesthesia check-up — required for Cholecystectomy")
    has_postop_photo          = models.BooleanField(default=False,
        help_text="Post-op clinical photograph — required for TKR")
    has_previous_cholecystectomy = models.BooleanField(default=False,
        help_text="FRAUD FLAG: Has patient had cholecystectomy before?")
    fever_duration_days       = models.PositiveIntegerField(null=True, blank=True,
        help_text="Duration of fever in days (for Enteric Fever)")

    def __str__(self):
        return self.title or f"Claim #{self.id}"