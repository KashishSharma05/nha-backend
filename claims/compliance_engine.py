"""
NHA Standard Treatment Guidelines — Compliance Rule Engine
Based on: ps1.zip STG PDFs (Cholecystectomy, Enteric Fever, Severe Anemia, TKR)
"""

STG_REGISTRY = {
    "SG039C": "Cholecystectomy",
    "MG006A": "Enteric Fever",
    "MG064A": "Severe Anemia",
    "SB039A": "Total Knee Replacement (Primary)",
    "SB039B": "Total Knee Replacement (Revision)",
}

STG_PRICES = {
    "SG039C": 22000,
    "MG006A": 4000,
    "MG064A": 4000,
    "SB039A": 80000,
    "SB039B": 130000,
}

STG_ALOS = {
    "SG039C": (3, 5),
    "MG006A": (5, 7),
    "MG064A": (3, 5),
    "SB039A": (5, 7),
    "SB039B": (5, 7),
}


def check_compliance(claim_data: dict) -> dict:
    """
    Run STG compliance checks against a claim's medical data.

    Args:
        claim_data: dict with fields from the Claim model

    Returns:
        dict with compliance_score, risk_level, matched_rules, failed_rules,
              recommendation, verdict, payable_amount
    """
    diagnosis_code = (claim_data.get("diagnosis_code") or "").strip().upper()
    matched_rules = []
    failed_rules  = []

    # ── Helper ──────────────────────────────────────────────────────────────
    def check(rule_id, description, passed, impact="medium"):
        if passed:
            matched_rules.append({"id": rule_id, "description": description, "impact": impact})
        else:
            failed_rules.append({"id": rule_id, "description": description, "impact": impact})
        return passed

    # ── Common rules (apply to all STGs) ────────────────────────────────────
    alos = claim_data.get("alos")
    alos_min, alos_max = STG_ALOS.get(diagnosis_code, (1, 30))
    if alos is not None:
        check("CMN01", f"ALOS within expected range ({alos_min}–{alos_max} days) — actual: {alos} days",
              alos_min <= alos <= alos_max, "high")
    check("CMN02", "Discharge summary submitted",
          bool(claim_data.get("has_discharge_summary")), "high")
    check("CMN03", "Indoor case papers submitted",
          bool(claim_data.get("has_indoor_case_papers")), "high")

    # ── SG039C — Cholecystectomy ─────────────────────────────────────────────
    if diagnosis_code == "SG039C":
        check("CHO01", "Ultrasound report confirming cholelithiasis / cholecystitis submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("CHO02", "Histopathology report of gallbladder specimen submitted",
              bool(claim_data.get("has_histopathology_report")), "high")
        check("CHO03", "Operative note mentioning Laparoscopic or Open approach submitted",
              bool(claim_data.get("has_operative_note")), "medium")
        check("CHO04", "Clinical notes with indication for surgery submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")

    # ── MG006A — Enteric Fever ───────────────────────────────────────────────
    elif diagnosis_code == "MG006A":
        check("ENT01", "Widal test OR Blood culture confirming Salmonella Typhi submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("ENT02", "Antibiotic therapy (Ceftriaxone / Azithromycin / Ciprofloxacin) documented",
              bool(claim_data.get("has_treatment_records")), "high")
        check("ENT03", "CBC (Complete Blood Count) report submitted",
              bool(claim_data.get("has_cbc_report")), "medium")
        check("ENT04", "Clinical notes including fever history (≥7 days) submitted",
              bool(claim_data.get("has_clinical_notes")), "medium")

    # ── MG064A — Severe Anemia ───────────────────────────────────────────────
    elif diagnosis_code == "MG064A":
        hb = claim_data.get("hb_level")
        if hb is not None:
            check("ANE01", f"Hemoglobin level < 7 g/dL confirmed by lab report — actual: {hb} g/dL",
                  hb < 7.0, "high")
        else:
            failed_rules.append({"id": "ANE01",
                                  "description": "Hemoglobin level not submitted — required < 7 g/dL",
                                  "impact": "high"})
        check("ANE02", "Blood transfusion AND/OR ferrous sulphate injection documented",
              bool(claim_data.get("has_treatment_records")), "high")
        check("ANE03", "Post-treatment Hb report submitted to confirm improvement",
              bool(claim_data.get("has_post_treatment_report")), "high")
        check("ANE04", "CBC / Hb level report submitted at admission",
              bool(claim_data.get("has_diagnostic_report")), "medium")

    # ── SB039A / SB039B — Total Knee Replacement ────────────────────────────
    elif diagnosis_code in ("SB039A", "SB039B"):
        patient_age = claim_data.get("patient_age")
        if patient_age is not None:
            check("TKR01", f"Patient age > 55 years for primary OA — actual: {patient_age}",
                  patient_age > 55, "high")
        else:
            failed_rules.append({"id": "TKR01",
                                  "description": "Patient age not submitted — required > 55 for primary OA",
                                  "impact": "high"})
        check("TKR02", "X-ray / CT of knee confirming joint space narrowing submitted",
              bool(claim_data.get("has_diagnostic_report")), "high")
        check("TKR03", "Post-op X-ray showing implant submitted",
              bool(claim_data.get("has_post_treatment_report")), "high")
        check("TKR04", "Implant invoice / barcode submitted",
              bool(claim_data.get("has_implant_invoice")), "high")
        check("TKR05", "Detailed operative note submitted",
              bool(claim_data.get("has_operative_note")), "medium")
        if diagnosis_code == "SB039B":
            check("TKR06", "Pre-op X-ray showing existing implant submitted (required for Revision)",
                  bool(claim_data.get("has_preop_xray")), "high")

    else:
        # Unknown STG code
        failed_rules.append({
            "id": "STG00",
            "description": f"Unknown or missing diagnosis code: '{diagnosis_code}'. Cannot apply STG rules.",
            "impact": "high"
        })

    # ── Score calculation ────────────────────────────────────────────────────
    total   = len(matched_rules) + len(failed_rules)
    score   = round((len(matched_rules) / total) * 100) if total > 0 else 0

    high_failures = [r for r in failed_rules if r["impact"] == "high"]

    if score >= 90 and not high_failures:
        risk_level      = "Low Risk"
        verdict         = "APPROVED"
        recommendation  = (
            "Claim meets all NHA STG compliance requirements. "
            "Approved for processing and reimbursement."
        )
    elif score >= 60 or not high_failures:
        risk_level      = "Medium Risk"
        verdict         = "CONDITIONAL"
        recommendation  = (
            "Claim partially meets STG compliance. "
            "Missing some mandatory documents. "
            "Manual review recommended before approval."
        )
    else:
        risk_level      = "High Risk"
        verdict         = "REJECTED"
        recommendation  = (
            "Claim does not meet NHA STG compliance requirements. "
            f"{len(high_failures)} critical rule(s) failed. "
            "Claim should be rejected or returned to hospital for resubmission."
        )

    # ── Payable amount ───────────────────────────────────────────────────────
    base_price = STG_PRICES.get(diagnosis_code, 0)
    payable    = base_price if verdict == "APPROVED" else (base_price * score // 100 if verdict == "CONDITIONAL" else 0)

    return {
        "diagnosis_code":    diagnosis_code,
        "procedure_name":    STG_REGISTRY.get(diagnosis_code, "Unknown Procedure"),
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
    }
