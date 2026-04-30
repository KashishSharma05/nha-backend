"""
NHA Standard Treatment Guidelines — Compliance Rule Engine
Based on: ps1.zip STG PDFs (Cholecystectomy, Enteric Fever, Severe Anemia, TKR)

Corrected against full PDF extraction:
- Cholecystectomy has 4 variants (SG039A-D), all ₹22,800
- Enteric Fever ALOS is 3-5 days (not 5-7), tiered pricing 1800-4500
- Severe Anemia ALOS is 3 days, tiered pricing 1800-4500
- TKR unchanged
"""

STG_REGISTRY = {
    "SG039A": "Cholecystectomy Without CBD Exploration — Open",
    "SG039B": "Cholecystectomy With CBD Exploration — Open",
    "SG039C": "Cholecystectomy Without CBD Exploration — Laparoscopic",
    "SG039D": "Cholecystectomy With CBD Exploration — Laparoscopic",
    "MG006A": "Enteric Fever (Typhoid)",
    "MG001A": "Acute Febrile Illness",
    "MG026A": "Pyrexia of Unknown Origin",
    "MG064A": "Severe Anemia",
    "SB039A": "Total Knee Replacement (Primary)",
    "SB039B": "Total Knee Replacement (Revision)",
}

# Base prices (General Ward rate for medical; fixed for surgical)
STG_PRICES = {
    "SG039A": 22800,
    "SG039B": 22800,
    "SG039C": 22800,
    "SG039D": 22800,
    "MG006A": 4500,   # ICU with ventilator (max tier)
    "MG001A": 4500,
    "MG026A": 4500,
    "MG064A": 4500,   # ICU with ventilator (max tier)
    "SB039A": 80000,
    "SB039B": 130000,
}

# Tiered pricing for medical packages
WARD_PRICES = {
    "MG006A": {"general_ward": 1800, "hdu": 2700, "icu": 3600, "icu_ventilator": 4500},
    "MG001A": {"general_ward": 1800, "hdu": 2700, "icu": 3600, "icu_ventilator": 4500},
    "MG026A": {"general_ward": 1800, "hdu": 2700, "icu": 3600, "icu_ventilator": 4500},
    "MG064A": {"general_ward": 1800, "hdu": 2700, "icu": 3600, "icu_ventilator": 4500},
}

# ALOS ranges (min, max days) — corrected from PDFs
STG_ALOS = {
    "SG039A": (3, 6),   # Open: 6 days
    "SG039B": (3, 6),
    "SG039C": (1, 3),   # Laparoscopic: 3 days
    "SG039D": (1, 3),
    "MG006A": (3, 5),   # CORRECTED: PDF says 3-5 days
    "MG001A": (3, 5),
    "MG026A": (3, 5),
    "MG064A": (2, 4),   # CORRECTED: PDF says ALOS 3 days, allow 2-4
    "SB039A": (5, 7),
    "SB039B": (5, 7),
}

# Doctor qualifications
STG_DOCTOR_QUAL = {
    "SG039A": "MS / DNB General Surgery (Essential)",
    "SG039B": "MS / DNB General Surgery (Essential)",
    "SG039C": "MS / DNB General Surgery (Essential)",
    "SG039D": "MS / DNB General Surgery (Essential)",
    "MG006A": "MD / DNB General Medicine (Essential); MBBS (Desirable)",
    "MG001A": "MD / DNB General Medicine (Essential); MBBS (Desirable)",
    "MG026A": "MD / DNB General Medicine (Essential); MBBS (Desirable)",
    "MG064A": "MBBS (Essential); MD / DNB General Medicine (Desirable)",
    "SB039A": "Diploma Ortho + 10yr exp (Essential); MS/DNB Ortho (Desirable)",
    "SB039B": "Diploma Ortho + 10yr exp (Essential); MS/DNB Ortho (Desirable)",
}


def check_compliance(claim_data: dict) -> dict:
    """
    Run STG compliance checks against a claim's medical data.
    Returns detailed compliance result with scores, rules, verdict, payable amount.
    """
    diagnosis_code = (claim_data.get("diagnosis_code") or "").strip().upper()
    matched_rules = []
    failed_rules  = []

    def check(rule_id, description, passed, impact="medium"):
        entry = {"id": rule_id, "description": description, "impact": impact}
        if passed:
            matched_rules.append(entry)
        else:
            failed_rules.append(entry)
        return passed

    # ── Common rules (all STGs) ─────────────────────────────────────────────
    alos = claim_data.get("alos")
    alos_range = STG_ALOS.get(diagnosis_code)
    if alos is not None and alos_range:
        alos_min, alos_max = alos_range
        check("CMN01",
              f"ALOS within expected range ({alos_min}–{alos_max} days). Actual: {alos} days",
              alos_min <= alos <= alos_max, "high")
    elif alos is not None and not alos_range:
        failed_rules.append({"id": "CMN01",
                             "description": "Cannot verify ALOS — unknown STG code",
                             "impact": "medium"})

    check("CMN02", "Discharge summary submitted",
          bool(claim_data.get("has_discharge_summary")), "high")
    check("CMN03", "Indoor case papers submitted",
          bool(claim_data.get("has_indoor_case_papers")), "high")

    # ── SG039A-D — Cholecystectomy ──────────────────────────────────────────
    if diagnosis_code in ("SG039A", "SG039B", "SG039C", "SG039D"):
        check("CHO01", "USG upper abdomen confirming cholelithiasis / cholecystitis submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("CHO02", "LFT (Liver Function Test) report submitted",
              bool(claim_data.get("has_lft_report")), "medium")
        check("CHO03", "Histopathology report of gallbladder specimen submitted",
              bool(claim_data.get("has_histopathology_report")), "high")
        check("CHO04", "Operative note submitted",
              bool(claim_data.get("has_operative_note")), "high")
        check("CHO05", "Clinical notes with indication for surgery submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")
        check("CHO06", "Pre-anesthesia check-up report submitted",
              bool(claim_data.get("has_pre_anesthesia_report")), "medium")
        check("CHO07", "Intraoperative photograph / gross specimen photo submitted",
              bool(claim_data.get("has_post_treatment_report")), "medium")
        # Fraud check: previous cholecystectomy must be NO
        if claim_data.get("has_previous_cholecystectomy"):
            failed_rules.append({
                "id": "CHO08",
                "description": "FRAUD FLAG: Patient has had cholecystectomy in the past — cannot be done twice",
                "impact": "high"
            })
        else:
            matched_rules.append({
                "id": "CHO08",
                "description": "No previous cholecystectomy on record",
                "impact": "high"
            })

    # ── MG006A / MG001A / MG026A — Enteric Fever / AFI / PUO ───────────────
    elif diagnosis_code in ("MG006A", "MG001A", "MG026A"):
        check("ENT01", "CBC, ESR, Peripheral smear, LFT reports submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("ENT02", "Post-treatment CBC, ESR, Peripheral smear, LFT reports submitted",
              bool(claim_data.get("has_post_treatment_report")), "high")
        check("ENT03", "Clinical notes with detailed fever history submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")
        check("ENT04", "Treatment details documented in indoor case papers",
              bool(claim_data.get("has_treatment_records")), "medium")
        # TMS rule: fever >= 38.3°C for > 2 days
        fever_duration = claim_data.get("fever_duration_days")
        if fever_duration is not None:
            check("ENT05",
                  f"Fever ≥ 38.3°C for more than 2 days. Actual: {fever_duration} days",
                  fever_duration >= 2, "high")

    # ── MG064A — Severe Anemia ──────────────────────────────────────────────
    elif diagnosis_code == "MG064A":
        hb = claim_data.get("hb_level")
        if hb is not None:
            check("ANE01",
                  f"Hemoglobin level < 7 g/dL confirmed. Actual: {hb} g/dL",
                  hb < 7.0, "high")
        else:
            failed_rules.append({
                "id": "ANE01",
                "description": "Hemoglobin level not submitted — required < 7 g/dL for Severe Anemia",
                "impact": "high"
            })
        check("ANE02", "CBC / Hb report submitted at admission",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("ANE03", "Blood transfusion AND/OR ferrous sulphate injection documented",
              bool(claim_data.get("has_treatment_records")), "high")
        check("ANE04", "Post-treatment Hb report submitted (confirms improvement)",
              bool(claim_data.get("has_post_treatment_report")), "high")
        check("ANE05", "Clinical notes with evaluation findings submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")

    # ── SB039A / SB039B — Total Knee Replacement ────────────────────────────
    elif diagnosis_code in ("SB039A", "SB039B"):
        patient_age = claim_data.get("patient_age")
        # Age check only for primary OA (no trauma, no systemic disease)
        if diagnosis_code == "SB039A":
            if patient_age is not None:
                check("TKR01",
                      f"Patient age > 55 years for primary OA. Actual: {patient_age} years",
                      patient_age > 55, "high")
            else:
                failed_rules.append({
                    "id": "TKR01",
                    "description": "Patient age not submitted — required > 55 for primary OA",
                    "impact": "high"
                })

        check("TKR02", "X-ray / CT of knee (labelled with patient ID, date, side) submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("TKR03", "Post-op X-ray showing implant (labelled) submitted",
              bool(claim_data.get("has_post_treatment_report")), "high")
        check("TKR04", "Implant invoice / barcode submitted",
              bool(claim_data.get("has_implant_invoice")), "high")
        check("TKR05", "Detailed operative / procedure note submitted",
              bool(claim_data.get("has_operative_note")), "medium")
        check("TKR06", "Post-op clinical photograph submitted",
              bool(claim_data.get("has_postop_photo")), "medium")
        check("TKR07", "Clinical notes with indication for surgery submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")

        if diagnosis_code == "SB039B":
            check("TKR08",
                  "Pre-op X-ray showing existing implant submitted (required for Revision TKR)",
                  bool(claim_data.get("has_preop_xray")), "high")

    else:
        failed_rules.append({
            "id": "STG00",
            "description": f"Unknown or missing diagnosis code: '{diagnosis_code}'. Cannot apply STG rules.",
            "impact": "high"
        })

    # ── Score calculation ────────────────────────────────────────────────────
    total  = len(matched_rules) + len(failed_rules)
    score  = round((len(matched_rules) / total) * 100) if total > 0 else 0

    high_failures = [r for r in failed_rules if r["impact"] == "high"]

    if score >= 90 and not high_failures:
        risk_level     = "Low"
        verdict        = "APPROVED"
        recommendation = (
            "Claim meets all NHA STG compliance requirements. "
            "Approved for processing and reimbursement."
        )
    elif score >= 50 or not high_failures:
        risk_level     = "Medium"
        verdict        = "CONDITIONAL"
        recommendation = (
            "Claim partially meets STG compliance. "
            f"{len(failed_rules)} rule(s) failed — {len(high_failures)} critical. "
            "Manual review recommended before approval."
        )
    else:
        risk_level     = "High"
        verdict        = "REJECTED"
        recommendation = (
            "Claim does not meet NHA STG compliance requirements. "
            f"{len(high_failures)} critical rule(s) failed. "
            "Claim should be rejected or returned to hospital for resubmission."
        )

    # ── Payable amount ───────────────────────────────────────────────────────
    ward_type  = claim_data.get("ward_type", "general_ward")
    ward_table = WARD_PRICES.get(diagnosis_code)
    if ward_table:
        base_price = ward_table.get(ward_type, ward_table["general_ward"])
    else:
        base_price = STG_PRICES.get(diagnosis_code, 0)

    if verdict == "APPROVED":
        payable = base_price
    elif verdict == "CONDITIONAL":
        payable = base_price * score // 100
    else:
        payable = 0

    return {
        "diagnosis_code":    diagnosis_code,
        "procedure_name":    STG_REGISTRY.get(diagnosis_code, "Unknown Procedure"),
        "specialty":         _get_specialty(diagnosis_code),
        "doctor_qualification": STG_DOCTOR_QUAL.get(diagnosis_code, ""),
        "compliance_score":  score,
        "risk_level":        risk_level,
        "verdict":           verdict,
        "matched_rules":     matched_rules,
        "failed_rules":      failed_rules,
        "total_rules":       total,
        "passed_rules":      len(matched_rules),
        "recommendation":    recommendation,
        "base_price":        base_price,
        "payable_amount":    payable,
        "total_claimed":     claim_data.get("claimed_amount", base_price),
        "alos_range":        list(STG_ALOS.get(diagnosis_code, [0, 0])),
    }


def _get_specialty(code):
    if code.startswith("SG039"):
        return "General Surgery"
    elif code in ("MG006A", "MG001A", "MG026A", "MG064A"):
        return "General Medicine"
    elif code.startswith("SB039"):
        return "Orthopedics"
    return "Unknown"
