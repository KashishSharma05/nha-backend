from django.db import models
from django.conf import settings
import json


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


# ─────────────────────────────────────────────────────────────────────────────
# PS-1 Per-Page Output Model
# ─────────────────────────────────────────────────────────────────────────────

# Document-type → default chronological rank (per PS-1 spec)
DOC_RANK_MAP = {
    "MG064A": {
        "clinical_notes":    1,
        "cbc_hb_report":     2,
        "indoor_case":       3,
        "treatment_details": 4,
        "post_hb_report":    5,
        "discharge_summary": 6,
    },
    "SG039C": {
        "clinical_notes":    1,
        "usg_report":        2,
        "lft_report":        3,
        "pre_anesthesia":    4,
        "indoor_case":       5,
        "operative_notes":   6,
        "photo_evidence":    7,
        "histopathology":    8,
        "discharge_summary": 9,
    },
    "MG006A": {
        "clinical_notes":      1,
        "investigation_pre":   2,
        "vitals_treatment":    3,
        "investigation_post":  4,
        "discharge_summary":   5,
    },
    "SB039A": {
        "clinical_notes":    1,
        "xray_ct_knee":      2,
        "indoor_case":       3,
        "operative_notes":   4,
        "implant_invoice":   5,
        "post_op_photo":     6,
        "post_op_xray":      7,
        "discharge_summary": 8,
    },
}


class ClaimPageResult(models.Model):
    """Stores the PS-1 compliant per-page output for a single page of a claim document."""

    claim          = models.ForeignKey(Claim, on_delete=models.CASCADE,
                                       related_name='page_results')

    # ── Identification ───────────────────────────────────────────────────────
    case_id        = models.CharField(max_length=200)
    s3_link        = models.CharField(max_length=1000, blank=True, default='')
    procedure_code = models.CharField(max_length=10)
    page_number    = models.PositiveIntegerField(default=1)
    document_type  = models.CharField(max_length=50, blank=True, default='',
                                      help_text="Gemini-classified doc type for rank assignment")

    # ── Common fields (all packages) ─────────────────────────────────────────
    clinical_notes    = models.BooleanField(default=False)
    discharge_summary = models.BooleanField(default=False)
    extra_document    = models.BooleanField(default=False)
    document_rank     = models.PositiveIntegerField(default=99)

    # ── MG064A — Severe Anemia ───────────────────────────────────────────────
    cbc_hb_report         = models.BooleanField(default=False)
    indoor_case           = models.BooleanField(default=False)
    treatment_details     = models.BooleanField(default=False)
    post_hb_report        = models.BooleanField(default=False)
    severe_anemia         = models.BooleanField(default=False,
        help_text="Hb < 7 g/dL — STG Section 3.2")
    common_signs          = models.BooleanField(default=False,
        help_text="Pallor, fatigue, weakness — STG Sec 1.2")
    significant_signs     = models.BooleanField(default=False,
        help_text="Tachycardia, breathlessness — STG Sec 1.2")
    life_threatening_signs = models.BooleanField(default=False,
        help_text="Cardiac failure, shock, severe hypoxia — STG Sec 1.2")

    # ── SG039C — Cholecystectomy ─────────────────────────────────────────────
    usg_report        = models.BooleanField(default=False)
    lft_report        = models.BooleanField(default=False)
    operative_notes   = models.BooleanField(default=False)
    pre_anesthesia    = models.BooleanField(default=False)
    photo_evidence    = models.BooleanField(default=False,
        help_text="Intra-op + gross specimen photos")
    histopathology    = models.BooleanField(default=False)
    clinical_condition = models.BooleanField(default=False,
        help_text="Any of 5 clinical conditions present — STG Sec 1.2")
    usg_calculi       = models.BooleanField(default=False,
        help_text="USG confirms calculi — STG Sec 3.2")
    pain_present      = models.BooleanField(default=False,
        help_text="Pain in right hypochondrium / epigastrium")
    previous_surgery  = models.BooleanField(default=False,
        help_text="Prior cholecystectomy — fraud flag")

    # ── MG006A — Enteric Fever ───────────────────────────────────────────────
    investigation_pre  = models.BooleanField(default=False)
    pre_date           = models.CharField(max_length=20, null=True, blank=True,
        help_text="Date on pre-investigation report (DD/MM/YY)")
    vitals_treatment   = models.BooleanField(default=False,
        help_text="Vitals + treatment chart")
    investigation_post = models.BooleanField(default=False)
    post_date          = models.CharField(max_length=20, null=True, blank=True,
        help_text="Date on post-investigation report (DD/MM/YY)")
    poor_quality       = models.BooleanField(default=False,
        help_text="Document/image quality is poor or unreadable")
    fever              = models.BooleanField(default=False,
        help_text="Fever criterion met — STG Sec 3.2.1")
    symptoms           = models.BooleanField(default=False,
        help_text="Any of 3 symptoms present — STG Sec 1.2")

    # ── SB039A — Total Knee Replacement ─────────────────────────────────────
    xray_ct_knee          = models.BooleanField(default=False)
    implant_invoice       = models.BooleanField(default=False)
    post_op_photo         = models.BooleanField(default=False)
    post_op_xray          = models.BooleanField(default=False)
    doa                   = models.CharField(max_length=20, null=True, blank=True,
        help_text="Date of Admission from discharge summary (DD-MM-YYYY)")
    dod                   = models.CharField(max_length=20, null=True, blank=True,
        help_text="Date of Discharge from discharge summary (DD-MM-YYYY)")
    arthritis_type        = models.BooleanField(default=False,
        help_text="Arthritis type classification — STG Sec 1.2")
    post_op_implant_present = models.BooleanField(default=False,
        help_text="Post-op X-ray shows implant — STG Sec 3.2.2")
    age_valid             = models.BooleanField(default=False,
        help_text="Age >= 55 for primary OA — STG Sec 3.2.3")

    # ── Metadata ─────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    raw_json   = models.JSONField(null=True, blank=True,
        help_text="Raw Gemini extraction response for this page")

    class Meta:
        ordering = ['page_number']

    def __str__(self):
        return f"Claim #{self.claim_id} — {self.procedure_code} Page {self.page_number}"

    def to_ps1_dict(self):
        """Serialize this page to the exact PS-1 output JSON structure."""
        code = (self.procedure_code or '').upper()

        # Base fields common to all packages
        base = {
            "case_id":        self.case_id,
            "procedure_code": self.procedure_code,
            "page_number":    self.page_number,
            "clinical_notes": int(self.clinical_notes),
            "discharge_summary": int(self.discharge_summary),
            "extra_document": int(self.extra_document),
            "document_rank":  self.document_rank,
        }

        if code == "MG064A":
            base["link"] = self.s3_link
            base.update({
                "cbc_hb_report":         int(self.cbc_hb_report),
                "indoor_case":           int(self.indoor_case),
                "treatment_details":     int(self.treatment_details),
                "post_hb_report":        int(self.post_hb_report),
                "severe_anemia":         int(self.severe_anemia),
                "common_signs":          int(self.common_signs),
                "significant_signs":     int(self.significant_signs),
                "life_threatening_signs": int(self.life_threatening_signs),
            })

        elif code == "SG039C":
            base["S3_link/DocumentName"] = self.s3_link
            base.update({
                "usg_report":        int(self.usg_report),
                "lft_report":        int(self.lft_report),
                "operative_notes":   int(self.operative_notes),
                "pre_anesthesia":    int(self.pre_anesthesia),
                "photo_evidence":    int(self.photo_evidence),
                "histopathology":    int(self.histopathology),
                "clinical_condition": int(self.clinical_condition),
                "usg_calculi":       int(self.usg_calculi),
                "pain_present":      int(self.pain_present),
                "previous_surgery":  int(self.previous_surgery),
            })

        elif code == "MG006A":
            base["S3_link"] = self.s3_link
            base.update({
                "investigation_pre":  int(self.investigation_pre),
                "pre_date":           self.pre_date,
                "vitals_treatment":   int(self.vitals_treatment),
                "investigation_post": int(self.investigation_post),
                "post_date":          self.post_date,
                "poor_quality":       int(self.poor_quality),
                "fever":              int(self.fever),
                "symptoms":           int(self.symptoms),
            })

        elif code == "SB039A":
            base["s3_link"] = self.s3_link
            base.update({
                "xray_ct_knee":           int(self.xray_ct_knee),
                "indoor_case":            int(self.indoor_case),
                "operative_notes":        int(self.operative_notes),
                "implant_invoice":        int(self.implant_invoice),
                "post_op_photo":          int(self.post_op_photo),
                "post_op_xray":           int(self.post_op_xray),
                "doa":                    self.doa,
                "dod":                    self.dod,
                "arthritis_type":         int(self.arthritis_type),
                "post_op_implant_present": int(self.post_op_implant_present),
                "age_valid":              int(self.age_valid),
            })

        return base

    @classmethod
    def from_gemini_dict(cls, claim, page_data: dict, case_id: str,
                         s3_link: str, procedure_code: str):
        """Construct a ClaimPageResult from Gemini's per-page extraction dict."""
        obj = cls(claim=claim, case_id=case_id, s3_link=s3_link,
                  procedure_code=procedure_code)
        for field in [
            'page_number', 'document_type',
            'clinical_notes', 'discharge_summary', 'extra_document', 'document_rank',
            # MG064A
            'cbc_hb_report', 'indoor_case', 'treatment_details', 'post_hb_report',
            'severe_anemia', 'common_signs', 'significant_signs', 'life_threatening_signs',
            # SG039C
            'usg_report', 'lft_report', 'operative_notes', 'pre_anesthesia',
            'photo_evidence', 'histopathology', 'clinical_condition',
            'usg_calculi', 'pain_present', 'previous_surgery',
            # MG006A
            'investigation_pre', 'pre_date', 'vitals_treatment',
            'investigation_post', 'post_date', 'poor_quality', 'fever', 'symptoms',
            # SB039A
            'xray_ct_knee', 'implant_invoice', 'post_op_photo', 'post_op_xray',
            'doa', 'dod', 'arthritis_type', 'post_op_implant_present', 'age_valid',
        ]:
            if field in page_data:
                val = page_data[field]
                # Convert integer 0/1 to bool for BooleanFields
                model_field = cls._meta.get_field(field)
                if hasattr(model_field, 'get_internal_type') and \
                        model_field.get_internal_type() == 'BooleanField':
                    val = bool(val)
                setattr(obj, field, val)
        obj.raw_json = page_data
        return obj