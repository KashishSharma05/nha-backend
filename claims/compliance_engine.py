"""
NHA STG Compliance Engine — Strictly based on NHA PDF rules only.

Rule weights (from PDF structure):
  Part III TMS rules   → weight=3, critical (any fail = REJECTED)
  Part II Mandatory doc → weight=2, high
  Part I ALOS / price  → weight=1, medium

Scoring: weighted_passed / weighted_total * 100
Verdict:
  - Any Part III (TMS) rule fails → REJECTED immediately
  - Score >= 85 and no high failures → APPROVED
  - Score >= 50 → CONDITIONAL
  - Else → REJECTED
"""

# ── Registry ─────────────────────────────────────────────────────────────────
STG_REGISTRY = {
    "SG039A": "Cholecystectomy — Open (Without CBD Exploration)",
    "SG039B": "Cholecystectomy — Open (With CBD Exploration)",
    "SG039C": "Cholecystectomy — Laparoscopic (Without CBD Exploration)",
    "SG039D": "Cholecystectomy — Laparoscopic (With CBD Exploration)",
    "MG006A": "Enteric Fever (Typhoid)",
    "MG001A": "Acute Febrile Illness",
    "MG026A": "Pyrexia of Unknown Origin",
    "MG064A": "Severe Anemia",
    "SB039A": "Total Knee Replacement (Primary)",
    "SB039B": "Total Knee Replacement (Revision)",
}

STG_SPECIALTY = {
    "SG039A": "General Surgery", "SG039B": "General Surgery",
    "SG039C": "General Surgery", "SG039D": "General Surgery",
    "MG006A": "General Medicine", "MG001A": "General Medicine",
    "MG026A": "General Medicine", "MG064A": "General Medicine",
    "SB039A": "Orthopedics",     "SB039B": "Orthopedics",
}

# ALOS (min, max) from PDFs
STG_ALOS = {
    "SG039A": (4, 6),  # Open: 6 days
    "SG039B": (4, 6),
    "SG039C": (1, 3),  # Laparoscopic: 3 days
    "SG039D": (1, 3),
    "MG006A": (3, 5),  # 3–5 days
    "MG001A": (3, 5),
    "MG026A": (3, 5),
    "MG064A": (2, 4),  # ~3 days
    "SB039A": (5, 7),  # 5–7 days
    "SB039B": (5, 7),
}

# Package prices (INR). Tiered for medical packages = max (ICU+vent).
STG_PRICES = {
    "SG039A": 22800, "SG039B": 22800,
    "SG039C": 22800, "SG039D": 22800,
    "MG006A": 4500,  "MG001A": 4500,
    "MG026A": 4500,  "MG064A": 4500,
    "SB039A": 80000, "SB039B": 130000,
}

WARD_PRICES = {
    "general_ward": 1800, "hdu": 2700,
    "icu": 3600, "icu_ventilator": 4500,
}

TIERED_CODES = {"MG006A", "MG001A", "MG026A", "MG064A"}

# Rule parts
PART_III = "TMS"      # weight 3, critical
PART_II  = "DOCS"     # weight 2, high
PART_I   = "CLINICAL" # weight 1, medium


def check_compliance(claim_data: dict) -> dict:
    code = (claim_data.get("diagnosis_code") or "").strip().upper()

    rules = []  # list of rule dicts

    def rule(rid, part, desc, passed, fix=""):
        """Register a rule result."""
        rules.append({
            "id":          rid,
            "part":        part,
            "description": desc,
            "passed":      passed,
            "fix":         fix if not passed else "",
            "weight":      3 if part == PART_III else (2 if part == PART_II else 1),
        })
        return passed

    # ── ALOS check (Part I — PDF specifies explicit ALOS) ───────────────────
    alos = claim_data.get("alos")
    alos_range = STG_ALOS.get(code)
    if alos is not None and alos_range:
        lo, hi = alos_range
        if alos < lo:
            rule("ALOS01", PART_I,
                 f"ALOS {alos}d is BELOW minimum {lo}d — possible premature discharge or fraudulent billing",
                 False,
                 f"Verify actual discharge date. Minimum expected stay is {lo} days per NHA STG.")
        elif alos > hi:
            rule("ALOS01", PART_I,
                 f"ALOS {alos}d EXCEEDS expected maximum {hi}d",
                 False,
                 f"Justify extended stay with clinical notes. Expected ALOS: {lo}–{hi} days.")
        else:
            rule("ALOS01", PART_I,
                 f"ALOS {alos}d is within expected range ({lo}–{hi} days) per NHA STG",
                 True)

    # ── Financial check (Part I — claimed vs package price) ─────────────────
    claimed = claim_data.get("claimed_amount")
    ward    = claim_data.get("ward_type", "general_ward")
    if code in TIERED_CODES:
        base_price = WARD_PRICES.get(ward, 1800)
    else:
        base_price = STG_PRICES.get(code, 0)

    if claimed and base_price:
        if claimed > base_price:
            rule("FIN01", PART_I,
                 f"Claimed amount ₹{claimed:,} EXCEEDS NHA package price ₹{base_price:,}",
                 False,
                 f"Package rate is fixed at ₹{base_price:,}. Over-claiming is not permitted.")
        else:
            rule("FIN01", PART_I,
                 f"Claimed amount ₹{claimed:,} is within NHA package price ₹{base_price:,}",
                 True)

    # ────────────────────────────────────────────────────────────────────────
    # CHOLECYSTECTOMY (SG039A/B/C/D)
    # ────────────────────────────────────────────────────────────────────────
    if code in ("SG039A", "SG039B", "SG039C", "SG039D"):

        # Part III — TMS auto-check rules (critical)
        rule("CHO-TMS01", PART_III,
             "USG upper abdomen confirms presence of calculi in gall bladder",
             bool(claim_data.get("has_diagnostic_report")),
             "Submit USG upper abdomen report showing cholelithiasis — required per NHA TMS rule I.")

        rule("CHO-TMS02", PART_III,
             "Patient has complaint of pain in right hypochondrium or epigastrium",
             bool(claim_data.get("has_clinical_notes")),
             "Clinical notes must document right hypochondrium/epigastric pain — NHA TMS rule II.")

        prev = claim_data.get("has_previous_cholecystectomy", False)
        rule("CHO-TMS03", PART_III,
             "No previous cholecystectomy on record (procedure cannot be repeated)",
             not prev,
             "FRAUD FLAG: Previous cholecystectomy detected — NHA TMS rule III explicitly rejects this.")

        # Part II — Mandatory documents
        rule("CHO-DOC01", PART_II,
             "LFT (Liver Function Test) report submitted at pre-authorization",
             bool(claim_data.get("has_lft_report")),
             "LFT report is mandatory at pre-auth stage. Submit elevated bilirubin/transaminase/alkaline phosphate results.")

        rule("CHO-DOC02", PART_II,
             "Operative notes with indications and outcomes submitted",
             bool(claim_data.get("has_operative_note")),
             "Detailed operative notes are mandatory at claim submission.")

        rule("CHO-DOC03", PART_II,
             "Pre-anesthesia check-up report submitted",
             bool(claim_data.get("has_pre_anesthesia_report")),
             "Pre-anesthesia check-up report is mandatory per NHA Part II CPD checklist.")

        rule("CHO-DOC04", PART_II,
             "Discharge summary with follow-up advice submitted",
             bool(claim_data.get("has_discharge_summary")),
             "Detailed discharge summary is mandatory at claim submission.")

        rule("CHO-DOC05", PART_II,
             "Intraoperative photograph and gross specimen pictures submitted",
             bool(claim_data.get("has_post_treatment_report")),
             "Intra-operative and gross specimen photos are mandatory. For CBD stones: video of extraction required.")

        rule("CHO-DOC06", PART_II,
             "Histopathology report of gallbladder specimen submitted",
             bool(claim_data.get("has_histopathology_report")),
             "Histopathology report is mandatory (may be submitted within 7 days of discharge).")

        rule("CHO-DOC07", PART_II,
             "Indoor case papers submitted",
             bool(claim_data.get("has_indoor_case_papers")),
             "Detailed indoor case papers are mandatory at claim submission.")

    # ────────────────────────────────────────────────────────────────────────
    # ENTERIC FEVER / AFI / PUO (MG006A / MG001A / MG026A)
    # ────────────────────────────────────────────────────────────────────────
    elif code in ("MG006A", "MG001A", "MG026A"):

        # Part III — TMS auto-check rule
        fever_days = claim_data.get("fever_duration_days")
        if fever_days is not None:
            rule("ENT-TMS01", PART_III,
                 f"Patient had fever ≥ 38.3°C / ≥ 101°F for more than 2 days (actual: {fever_days}d)",
                 fever_days >= 2,
                 "NHA TMS rule: Fever must be documented for > 2 days at ≥ 38.3°C. Submit temperature chart.")
        else:
            rule("ENT-TMS01", PART_III,
                 "Fever duration not recorded — required by NHA TMS rule",
                 False,
                 "Document fever duration in days (must be > 2 days at ≥ 38.3°C / ≥ 101°F).")

        # Part II — Mandatory documents
        rule("ENT-DOC01", PART_II,
             "CBC, ESR, Peripheral smear, LFT reports submitted at pre-authorization",
             bool(claim_data.get("has_diagnostic_report")),
             "CBC, ESR, Peripheral smear and LFT are all mandatory at pre-auth stage.")

        rule("ENT-DOC02", PART_II,
             "Detailed clinical notes with fever history submitted at pre-authorization",
             bool(claim_data.get("has_clinical_notes")),
             "Detailed clinical notes documenting fever history are mandatory at pre-auth.")

        rule("ENT-DOC03", PART_II,
             "Detailed indoor case papers with all vitals and treatment details submitted",
             bool(claim_data.get("has_indoor_case_papers")),
             "Indoor case papers with vitals and treatment details are mandatory at claim submission.")

        rule("ENT-DOC04", PART_II,
             "Post-treatment CBC, ESR, Peripheral smear, LFT reports submitted",
             bool(claim_data.get("has_post_treatment_report")),
             "Post-treatment investigation reports are mandatory — show patient improvement.")

        rule("ENT-DOC05", PART_II,
             "Detailed discharge summary with follow-up date submitted",
             bool(claim_data.get("has_discharge_summary")),
             "Discharge summary must include date of follow-up visit.")

    # ────────────────────────────────────────────────────────────────────────
    # SEVERE ANEMIA (MG064A)
    # ────────────────────────────────────────────────────────────────────────
    elif code == "MG064A":

        # Part III — TMS auto-check rules
        hb = claim_data.get("hb_level")
        if hb is not None:
            rule("ANE-TMS01", PART_III,
                 f"Patient Hb level < 7 g/dL confirmed (actual: {hb} g/dL)",
                 hb < 7.0,
                 f"NHA TMS rule: Hb must be < 7 g/dL for Severe Anemia. Reported Hb is {hb} g/dL — does not qualify.")
        else:
            rule("ANE-TMS01", PART_III,
                 "Hemoglobin level not submitted — required by NHA TMS rule",
                 False,
                 "Submit CBC/Hb report showing Hb < 7 g/dL at admission. This is a mandatory TMS check.")

        rule("ANE-TMS02", PART_III,
             "Blood transfusion treatment documented",
             bool(claim_data.get("has_treatment_records")),
             "NHA TMS rule: Blood transfusion must be documented. Submit transfusion records.")

        # Part II — Mandatory documents
        rule("ANE-DOC01", PART_II,
             "Clinical notes with evaluation findings, indications, and planned treatment submitted",
             bool(claim_data.get("has_clinical_notes")),
             "Clinical notes including evaluation findings and treatment plan are mandatory at pre-auth.")

        rule("ANE-DOC02", PART_II,
             "CBC / Hb report submitted at pre-authorization",
             bool(claim_data.get("has_diagnostic_report")),
             "CBC and Hb report are mandatory at pre-authorization stage.")

        rule("ANE-DOC03", PART_II,
             "Detailed indoor case papers with treatment details (blood transfusion + ferrous sulphate injection)",
             bool(claim_data.get("has_indoor_case_papers")),
             "Indoor case papers must specifically mention blood transfusion and ferrous sulphate injection.")

        rule("ANE-DOC04", PART_II,
             "Post-treatment Hb report confirming improvement submitted",
             bool(claim_data.get("has_post_treatment_report")),
             "Post-treatment Hb report is mandatory — must confirm improvement in Hb level.")

        rule("ANE-DOC05", PART_II,
             "Detailed discharge summary submitted",
             bool(claim_data.get("has_discharge_summary")),
             "Detailed discharge summary is mandatory at claim submission.")

    # ────────────────────────────────────────────────────────────────────────
    # TOTAL KNEE REPLACEMENT (SB039A / SB039B)
    # ────────────────────────────────────────────────────────────────────────
    elif code in ("SB039A", "SB039B"):

        # Part III — TMS auto-check rules
        rule("TKR-TMS01", PART_III,
             "Post-op X-ray of knee shows presence of implant",
             bool(claim_data.get("has_post_treatment_report")),
             "NHA TMS rule I: Post-op X-ray must show implant, labelled with patient ID, date and side (L/R).")

        if code == "SB039B":
            rule("TKR-TMS02", PART_III,
                 "Pre-op X-ray of knee shows presence of existing implant (Revision TKR)",
                 bool(claim_data.get("has_preop_xray")),
                 "NHA TMS rule II: For Revision TKR, pre-op X-ray must show existing implant.")

        age = claim_data.get("patient_age")
        if code == "SB039A":
            if age is not None:
                rule("TKR-TMS03", PART_III,
                     f"Patient age > 55 years for primary osteoarthritis (actual: {age}y)",
                     age > 55,
                     f"NHA TMS rule III: For primary OA with no trauma/systemic disease, patient must be > 55y. Age {age}y does not qualify.")
            else:
                rule("TKR-TMS03", PART_III,
                     "Patient age not submitted — required for primary OA validation",
                     False,
                     "NHA TMS rule III: Submit patient age. For primary osteoarthritis, age must be > 55 years.")

        # Part II — Mandatory documents
        rule("TKR-DOC01", PART_II,
             "X-ray / CT of knee (labelled with patient ID, date, side) submitted",
             bool(claim_data.get("has_diagnostic_report")),
             "Labelled X-ray or CT of the affected knee is mandatory at pre-authorization.")

        rule("TKR-DOC02", PART_II,
             "Clinical notes with surgical indication submitted",
             bool(claim_data.get("has_clinical_notes")),
             "Clinical notes with clear indication for surgery are mandatory at pre-authorization.")

        rule("TKR-DOC03", PART_II,
             "Indoor case papers submitted",
             bool(claim_data.get("has_indoor_case_papers")),
             "Indoor case papers are mandatory at claim submission.")

        rule("TKR-DOC04", PART_II,
             "Detailed operative / procedure note submitted",
             bool(claim_data.get("has_operative_note")),
             "Detailed operative note is mandatory at claim submission.")

        rule("TKR-DOC05", PART_II,
             "Post-op clinical photograph submitted",
             bool(claim_data.get("has_postop_photo")),
             "Post-op clinical photograph is mandatory at claim submission per NHA Part II.")

        rule("TKR-DOC06", PART_II,
             "Implant invoice / barcode submitted",
             bool(claim_data.get("has_implant_invoice")),
             "Implant invoice or barcode is mandatory at claim submission.")

        rule("TKR-DOC07", PART_II,
             "Discharge summary submitted",
             bool(claim_data.get("has_discharge_summary")),
             "Discharge summary is mandatory at claim submission.")

    else:
        rules.append({
            "id": "STG00", "part": PART_III,
            "description": f"Unknown/missing diagnosis code: '{code}'",
            "passed": False,
            "fix": "Select a valid NHA STG procedure code.",
            "weight": 3,
        })

    # ── Verdict calculation ──────────────────────────────────────────────────
    passed_rules = [r for r in rules if r["passed"]]
    failed_rules = [r for r in rules if not r["passed"]]
    tms_failures = [r for r in failed_rules if r["part"] == PART_III]
    doc_failures = [r for r in failed_rules if r["part"] == PART_II]

    w_total  = sum(r["weight"] for r in rules)
    w_passed = sum(r["weight"] for r in passed_rules)
    score    = round((w_passed / w_total) * 100) if w_total > 0 else 0

    # Determine verdict
    if tms_failures:
        # Any TMS (Part III) failure = immediate REJECTED
        verdict    = "REJECTED"
        risk_level = "High"
        recommendation = (
            f"REJECTED — {len(tms_failures)} critical NHA TMS rule(s) failed: "
            + "; ".join(r['description'] for r in tms_failures)
            + ". These are hard fraud-prevention checks defined in Part III of the NHA STG."
        )
    elif score >= 85 and not doc_failures:
        verdict    = "APPROVED"
        risk_level = "Low"
        recommendation = (
            "Claim fully complies with all NHA STG requirements. "
            "All mandatory documents and clinical criteria are satisfied. "
            "Approved for reimbursement."
        )
    elif score >= 50:
        verdict    = "CONDITIONAL"
        risk_level = "Medium"
        recommendation = (
            f"Claim partially complies — {len(doc_failures)} mandatory document(s) missing. "
            "Claim is held pending submission of the missing documents. "
            "Hospital must resubmit with complete documentation."
        )
    else:
        verdict    = "REJECTED"
        risk_level = "High"
        recommendation = (
            f"Claim rejected — compliance score {score}% is below acceptable threshold. "
            f"{len(failed_rules)} rule(s) failed including {len(doc_failures)} mandatory document(s). "
            "Hospital must correct all deficiencies and resubmit."
        )

    # ── Payable amount ───────────────────────────────────────────────────────
    if verdict == "APPROVED":
        payable = base_price
    elif verdict == "CONDITIONAL":
        payable = 0   # held — not paid until complete
    else:
        payable = 0

    # Clean up output — separate TMS from doc rules for frontend display
    return {
        "diagnosis_code":      code,
        "procedure_name":      STG_REGISTRY.get(code, "Unknown"),
        "specialty":           STG_SPECIALTY.get(code, ""),
        "alos_range":          list(STG_ALOS.get(code, [0, 0])),
        "compliance_score":    score,
        "risk_level":          risk_level,
        "verdict":             verdict,
        "recommendation":      recommendation,
        # Rules split by part for detailed frontend display
        "matched_rules":       [_fmt(r) for r in passed_rules],
        "failed_rules":        [_fmt(r) for r in failed_rules],
        "tms_failures":        [_fmt(r) for r in tms_failures],
        "doc_failures":        [_fmt(r) for r in doc_failures],
        "total_rules":         len(rules),
        "passed_rules":        len(passed_rules),
        "total_tms_rules":     len([r for r in rules if r["part"] == PART_III]),
        "passed_tms_rules":    len([r for r in passed_rules if r["part"] == PART_III]),
        # Financial
        "base_price":          base_price,
        "payable_amount":      payable,
        "total_claimed":       claim_data.get("claimed_amount", base_price),
    }


def _fmt(r):
    return {
        "id":          r["id"],
        "part":        r["part"],
        "description": r["description"],
        "fix":         r.get("fix", ""),
        "impact":      "critical" if r["part"] == PART_III else "high",
    }
