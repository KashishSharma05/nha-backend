"""
PS-1 Output Engine — NHA PMJAY Hackathon

Produces a PS-1 compliant per-page JSON array for any of the 4 packages:
  MG064A — Severe Anemia
  SG039C — Cholecystectomy (Laparoscopic)
  MG006A — Enteric Fever
  SB039A — Total Knee Replacement

Flow:
  1. PDF is uploaded to Gemini's File API
  2. A package-specific structured prompt drives per-page extraction
  3. Gemini returns a JSON array (one object per page)
  4. document_rank is normalised / validated server-side
  5. Results are persisted in ClaimPageResult and returned as PS-1 JSON
"""

import os
import json
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ── Gemini setup ──────────────────────────────────────────────────────────────
_api_key = os.getenv("GEMINI_API_KEY")
_client  = genai.Client(api_key=_api_key) if _api_key else None



# ── Package-specific Gemini prompts ───────────────────────────────────────────

_PROMPTS = {

    # ── MG064A — Severe Anemia ────────────────────────────────────────────────
    "MG064A": """
<ROLE>
You are an expert NHA (National Health Authority) Medical Auditor for PMJAY.
You are reviewing an IPD dossier for Package MG064A — Severe Anemia.
</ROLE>

<TASK>
Analyse EVERY PAGE of this document individually.
Return a JSON array where each element covers exactly ONE page.
</TASK>

<FIELD_DEFINITIONS>
clinical_notes      : Doctor's evaluation notes with patient history and examination findings (1=present, 0=absent)
cbc_hb_report       : CBC / Hemoglobin pathology report (1=present, 0=absent)
indoor_case         : Indoor case papers / nursing charts / daily ward progress notes (1=present, 0=absent)
treatment_details   : Blood transfusion records or Iron/Ferrous-sulphate injection records (1=present, 0=absent)
post_hb_report      : Post-treatment Hemoglobin report confirming improvement (1=present, 0=absent)
discharge_summary   : Final discharge summary with admission/discharge dates (1=present, 0=absent)
severe_anemia       : This page contains evidence that Hb < 7 g/dL (STG Section 3.2) (1=yes, 0=no)
common_signs        : Page documents pallor, fatigue, or weakness (STG Sec 1.2) (1=present, 0=absent)
significant_signs   : Page documents tachycardia or breathlessness (STG Sec 1.2) (1=present, 0=absent)
life_threatening_signs : Page documents cardiac failure, severe hypoxia, or shock (STG Sec 1.2) (1=present, 0=absent)
extra_document      : This page is NOT one of the STG-required documents above (e.g. consent form, unrelated report) (1=yes, 0=no)
document_rank       : Chronological position of this document. Use: clinical_notes=1, cbc_hb_report=2, indoor_case=3, treatment_details=4, post_hb_report=5, discharge_summary=6. Multi-page docs sharing the same type share the same rank. Extra documents = 99.
document_type       : One of: "clinical_notes","cbc_hb_report","indoor_case","treatment_details","post_hb_report","discharge_summary","extra_document"
</FIELD_DEFINITIONS>

<RULES>
1. Analyse each page INDEPENDENTLY — a field is 1 only if that specific page contains the evidence.
2. If a document spans multiple pages (e.g. a 3-page CBC report), all pages share the same document_rank.
3. extra_document = 1 AND document_rank = 99 for any page that is not in the STG list.
4. NO HALLUCINATIONS: mark 0 / null if the information is not explicitly present.
5. severe_anemia = 1 only if the page explicitly shows Hb < 7 g/dL.
</RULES>

<OUTPUT_FORMAT>
Return ONLY a valid JSON array. No markdown, no explanation. Example for 2 pages:
[
  {
    "page_number": 1,
    "document_type": "cbc_hb_report",
    "clinical_notes": 0,
    "cbc_hb_report": 1,
    "indoor_case": 0,
    "treatment_details": 0,
    "post_hb_report": 0,
    "discharge_summary": 0,
    "severe_anemia": 1,
    "common_signs": 0,
    "significant_signs": 0,
    "life_threatening_signs": 0,
    "extra_document": 0,
    "document_rank": 2
  },
  {
    "page_number": 2,
    "document_type": "extra_document",
    "clinical_notes": 0,
    "cbc_hb_report": 0,
    "indoor_case": 0,
    "treatment_details": 0,
    "post_hb_report": 0,
    "discharge_summary": 0,
    "severe_anemia": 0,
    "common_signs": 0,
    "significant_signs": 0,
    "life_threatening_signs": 0,
    "extra_document": 1,
    "document_rank": 99
  }
]
</OUTPUT_FORMAT>
""",

    # ── SG039C — Cholecystectomy ──────────────────────────────────────────────
    "SG039C": """
<ROLE>
You are an expert NHA Medical Auditor for PMJAY.
You are reviewing an IPD dossier for Package SG039C — Laparoscopic Cholecystectomy (No CBD Exploration).
</ROLE>

<TASK>
Analyse EVERY PAGE of this document individually.
Return a JSON array where each element covers exactly ONE page.
</TASK>

<FIELD_DEFINITIONS>
clinical_notes      : Doctor's evaluation/consultation notes (1=present, 0=absent)
usg_report          : USG Upper Abdomen report (1=present, 0=absent)
lft_report          : Liver Function Test (LFT) / bilirubin / transaminase / alkaline phosphatase report (1=present, 0=absent)
operative_notes     : Surgical operative note (1=present, 0=absent)
pre_anesthesia      : Pre-anesthesia check-up report (1=present, 0=absent)
discharge_summary   : Final discharge summary (1=present, 0=absent)
photo_evidence      : Intra-operative photographs or gross specimen photographs (1=present, 0=absent)
histopathology      : Histopathology report of the gallbladder specimen (1=present, 0=absent)
clinical_condition  : This page documents at least one of: (a) jaundice, (b) acute cholecystitis, (c) chronic cholecystitis, (d) mucocele of GB, (e) empyema of GB — as per STG Sec 1.2 (1=yes, 0=no)
usg_calculi         : USG explicitly confirms calculi / stones in the gallbladder — STG Sec 3.2 (1=yes, 0=no)
pain_present        : Page documents pain in right hypochondrium or epigastrium (1=yes, 0=no)
previous_surgery    : Page mentions patient has had a previous cholecystectomy — FRAUD FLAG (1=yes, 0=no)
extra_document      : This page is NOT in the STG-required list above (1=yes, 0=no)
document_rank       : Chronological rank. Use: clinical_notes=1, usg_report=2, lft_report=3, pre_anesthesia=4, indoor_case=5, operative_notes=6, photo_evidence=7, histopathology=8, discharge_summary=9. Extra=99.
document_type       : One of: "clinical_notes","usg_report","lft_report","pre_anesthesia","indoor_case","operative_notes","photo_evidence","histopathology","discharge_summary","extra_document"
</FIELD_DEFINITIONS>

<RULES>
1. Analyse each page INDEPENDENTLY.
2. clinical_condition = 1 if ANY ONE of the 5 listed conditions is documented on this page.
3. Multi-page documents sharing the same type share the same document_rank.
4. extra_document = 1 AND document_rank = 99 for non-STG pages.
5. NO HALLUCINATIONS.
</RULES>

<OUTPUT_FORMAT>
Return ONLY a valid JSON array. No markdown, no explanation.
Each element must have all the keys listed above plus "page_number".
</OUTPUT_FORMAT>
""",

    # ── MG006A — Enteric Fever ────────────────────────────────────────────────
    "MG006A": """
<ROLE>
You are an expert NHA Medical Auditor for PMJAY.
You are reviewing an IPD dossier for Package MG006A — Enteric Fever (Typhoid).
</ROLE>

<TASK>
Analyse EVERY PAGE of this document individually.
Return a JSON array where each element covers exactly ONE page.
</TASK>

<FIELD_DEFINITIONS>
clinical_notes      : Doctor's evaluation notes with fever history (1=present, 0=absent)
investigation_pre   : Pre-treatment investigation report (CBC, Widal, Blood Culture, etc.) (1=present, 0=absent)
pre_date            : Date printed on the pre-treatment investigation report. Extract exactly as shown (format DD/MM/YY or DD-MM-YYYY). Return null if not present on this page.
vitals_treatment    : Vitals chart or antibiotic/treatment chart (1=present, 0=absent)
investigation_post  : Post-treatment investigation report (1=present, 0=absent)
post_date           : Date printed on the post-treatment investigation report. Extract exactly as shown. Return null if not present on this page.
discharge_summary   : Final discharge summary (1=present, 0=absent)
poor_quality        : This page is a scan/photo of poor quality — difficult to read (1=yes, 0=no)
fever               : This page explicitly documents fever >= 38.3°C / 101°F for >= 2 days — STG Sec 3.2.1 (1=yes, 0=no)
symptoms            : This page documents at least one of: (a) headache, (b) abdominal pain, (c) relative bradycardia — STG Sec 1.2 (1=yes, 0=no)
extra_document      : This page is NOT in the STG-required list (1=yes, 0=no)
document_rank       : Chronological rank. Use: clinical_notes=1, investigation_pre=2, vitals_treatment=3, investigation_post=4, discharge_summary=5. Extra=99.
document_type       : One of: "clinical_notes","investigation_pre","vitals_treatment","investigation_post","discharge_summary","extra_document"
</FIELD_DEFINITIONS>

<RULES>
1. Analyse each page INDEPENDENTLY.
2. pre_date: extract from pre-investigation pages only. post_date: extract from post-investigation pages only.
3. symptoms = 1 if ANY ONE of the 3 listed symptoms is documented on this page.
4. fever = 1 only if temperature value or explicit mention of high-grade fever for >= 2 days appears on this page.
5. Multi-page documents sharing the same type share the same document_rank.
6. NO HALLUCINATIONS — if date is not on this page, return null.
</RULES>

<OUTPUT_FORMAT>
Return ONLY a valid JSON array. No markdown, no explanation.
Each element must have all the keys listed above plus "page_number".
</OUTPUT_FORMAT>
""",

    # ── SB039A — Total Knee Replacement ──────────────────────────────────────
    "SB039A": """
<ROLE>
You are an expert NHA Medical Auditor for PMJAY.
You are reviewing an IPD dossier for Package SB039A — Total Knee Replacement (Primary).
</ROLE>

<TASK>
Analyse EVERY PAGE of this document individually.
Return a JSON array where each element covers exactly ONE page.
</TASK>

<FIELD_DEFINITIONS>
clinical_notes      : Doctor's evaluation notes with surgical indication (1=present, 0=absent)
xray_ct_knee        : X-ray or CT of the knee (labelled with patient ID, date, and side L/R) (1=present, 0=absent)
indoor_case         : Indoor case papers / nursing charts (1=present, 0=absent)
operative_notes     : Surgical operative / procedure note (1=present, 0=absent)
implant_invoice     : Implant invoice or barcode sticker (1=present, 0=absent)
post_op_photo       : Post-operative clinical photograph (1=present, 0=absent)
post_op_xray        : Post-operative X-ray showing the implant (1=present, 0=absent)
discharge_summary   : Final discharge summary (1=present, 0=absent)
doa                 : Date of Admission — extract from the discharge summary in DD-MM-YYYY format. Return null if not on this page.
dod                 : Date of Discharge — extract from the discharge summary in DD-MM-YYYY format. Return null if not on this page.
arthritis_type      : This page documents the type of arthritis (osteoarthritis, rheumatoid, post-traumatic, avascular necrosis, or other) — STG Sec 1.2 (1=yes, 0=no)
post_op_implant_present : Post-op X-ray on this page shows the knee implant in situ — STG Sec 3.2.2 (1=yes, 0=no)
age_valid           : This page explicitly records patient age >= 55 years — STG Sec 3.2.3 (1=yes, 0=no)
extra_document      : This page is NOT in the STG-required list (1=yes, 0=no)
document_rank       : Chronological rank. Use: clinical_notes=1, xray_ct_knee=2, indoor_case=3, operative_notes=4, implant_invoice=5, post_op_photo=6, post_op_xray=7, discharge_summary=8. Extra=99.
document_type       : One of: "clinical_notes","xray_ct_knee","indoor_case","operative_notes","implant_invoice","post_op_photo","post_op_xray","discharge_summary","extra_document"
</FIELD_DEFINITIONS>

<RULES>
1. Analyse each page INDEPENDENTLY.
2. doa and dod must be extracted from discharge summary pages only, in DD-MM-YYYY format.
3. post_op_implant_present = 1 only if the X-ray image on this page visually shows the knee implant.
4. age_valid = 1 only if patient age is explicitly documented as >= 55 on this page.
5. Multi-page documents sharing the same type share the same document_rank.
6. NO HALLUCINATIONS.
</RULES>

<OUTPUT_FORMAT>
Return ONLY a valid JSON array. No markdown, no explanation.
Each element must have all the keys listed above plus "page_number".
</OUTPUT_FORMAT>
""",
}

# Fallback prompt for supported codes with alternate IDs (e.g. SG039A/B/D → use SG039C prompt)
_PROMPT_FALLBACKS = {
    "SG039A": "SG039C", "SG039B": "SG039C", "SG039D": "SG039C",
    "MG001A": "MG006A", "MG026A": "MG006A",
    "SB039B": "SB039A",
}


def _get_prompt(procedure_code: str) -> str | None:
    code = procedure_code.upper()
    if code in _PROMPTS:
        return _PROMPTS[code]
    fallback = _PROMPT_FALLBACKS.get(code)
    if fallback:
        return _PROMPTS[fallback]
    return None


# ── Core extraction function ──────────────────────────────────────────────────

def extract_ps1_output_from_pdf(pdf_path: str, procedure_code: str,
                                 case_id: str, s3_link: str) -> dict:
    """
    Upload the PDF to Gemini and extract PS-1 per-page JSON array.

    Returns:
        {
            "success": True,
            "pages": [ <per-page dicts> ],
            "page_count": N
        }
        or
        {
            "success": False,
            "error": "..."
        }
    """
    if not _client:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not configured. Set it in the .env file."
        }

    prompt_text = _get_prompt(procedure_code)
    if not prompt_text:
        return {
            "success": False,
            "error": f"No PS-1 prompt available for procedure code '{procedure_code}'."
        }

    gemini_file = None
    try:
        logger.info("PS-1 Engine: Uploading %s to Gemini for %s…", pdf_path, procedure_code)
        gemini_file = _client.files.upload(file=pdf_path)

        response = _client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[gemini_file, prompt_text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        raw_text = response.text.strip()
        # Strip markdown code fences if the model wraps with ```json … ```
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```", 2)[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.rsplit("```", 1)[0].strip()

        pages: list = json.loads(raw_text)
        if not isinstance(pages, list):
            return {"success": False, "error": "Gemini returned non-array response."}

        # Stamp case_id + s3_link + procedure_code into every page
        for i, page in enumerate(pages):
            page.setdefault("page_number", i + 1)
            page["case_id"]        = case_id
            page["s3_link"]        = s3_link
            page["procedure_code"] = procedure_code

        # Server-side rank normalisation
        pages = _normalise_ranks(pages, procedure_code)

        return {
            "success":    True,
            "pages":      pages,
            "page_count": len(pages),
        }

    except json.JSONDecodeError as exc:
        logger.error("PS-1 Engine: JSON decode error: %s", exc)
        return {"success": False, "error": "Gemini returned invalid JSON. Please retry."}

    except Exception as exc:
        err = str(exc)
        if "429" in err or "quota" in err.lower():
            err = "Gemini API rate limit reached. Please wait 60 seconds and retry."
        logger.error("PS-1 Engine: Gemini error: %s", err)
        return {"success": False, "error": err}

    finally:
        if gemini_file:
            try:
                _client.files.delete(name=gemini_file.name)
                logger.info("PS-1 Engine: Cleaned up Gemini file %s", gemini_file.name)
            except Exception as cleanup_err:
                logger.warning("PS-1 Engine: Could not delete Gemini file: %s", cleanup_err)


# ── Rank normalisation ────────────────────────────────────────────────────────

# Canonical document-type → base rank mapping (per PS-1 spec)
_BASE_RANKS = {
    "MG064A": {
        "clinical_notes": 1, "cbc_hb_report": 2, "indoor_case": 3,
        "treatment_details": 4, "post_hb_report": 5, "discharge_summary": 6,
        "extra_document": 99,
    },
    "SG039C": {
        "clinical_notes": 1, "usg_report": 2, "lft_report": 3,
        "pre_anesthesia": 4, "indoor_case": 5, "operative_notes": 6,
        "photo_evidence": 7, "histopathology": 8, "discharge_summary": 9,
        "extra_document": 99,
    },
    "MG006A": {
        "clinical_notes": 1, "investigation_pre": 2, "vitals_treatment": 3,
        "investigation_post": 4, "discharge_summary": 5,
        "extra_document": 99,
    },
    "SB039A": {
        "clinical_notes": 1, "xray_ct_knee": 2, "indoor_case": 3,
        "operative_notes": 4, "implant_invoice": 5, "post_op_photo": 6,
        "post_op_xray": 7, "discharge_summary": 8,
        "extra_document": 99,
    },
}
# Fill in fallbacks
for _alias, _canon in {
    "SG039A": "SG039C", "SG039B": "SG039C", "SG039D": "SG039C",
    "MG001A": "MG006A", "MG026A": "MG006A",
    "SB039B": "SB039A",
}.items():
    _BASE_RANKS[_alias] = _BASE_RANKS[_canon]


def _normalise_ranks(pages: list, procedure_code: str) -> list:
    """
    Ensure every page has a valid document_rank:
    - extra_document pages → 99
    - other pages → use document_type to look up base rank
    - multi-page docs of the same type share the same rank (already handled by the AI,
      but we enforce it here to avoid inconsistencies)
    """
    code   = procedure_code.upper()
    ranks  = _BASE_RANKS.get(code, {})

    # First pass: assign ranks from document_type
    type_rank_cache: dict[str, int] = {}  # document_type → rank (for multi-page consistency)

    for page in pages:
        extra     = bool(page.get("extra_document", 0))
        doc_type  = (page.get("document_type") or "").strip().lower()

        if extra:
            page["extra_document"] = 1
            page["document_rank"]  = 99
            continue

        # Use Gemini's rank if it gave one and it's sensible
        ai_rank = page.get("document_rank")
        if doc_type in ranks:
            expected_rank = ranks[doc_type]
        elif ai_rank and isinstance(ai_rank, int) and ai_rank != 99:
            expected_rank = ai_rank
        else:
            expected_rank = 99

        # Maintain multi-page consistency
        if doc_type and doc_type not in type_rank_cache:
            type_rank_cache[doc_type] = expected_rank
        final_rank = type_rank_cache.get(doc_type, expected_rank)

        page["document_rank"]  = final_rank
        page["extra_document"] = 0

    return pages
