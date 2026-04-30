import os
import json
import tempfile
import google.generativeai as genai

# Setup Gemini API (The user must provide GEMINI_API_KEY in .env)
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def extract_clinical_data_from_pdf(pdf_file_path):
    """
    Sends the PDF to Gemini 1.5 Flash to automatically extract clinical parameters
    and detect the presence of mandatory documents based on the NHA STG rules.
    """
    if not api_key:
        return {
            "error": "Gemini API key is missing. Add GEMINI_API_KEY to your .env file.",
            "success": False
        }

    try:
        # Upload the file to Gemini's File API
        print(f"Uploading {pdf_file_path} to Gemini...")
        gemini_file = genai.upload_file(pdf_file_path)

        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Define the strong JSON prompt
        prompt = """
        You are a highly advanced medical auditor working for the National Health Authority (NHA) PMJAY.
        Your task is to analyze the attached uploaded medical dossier (which may contain clinical notes, blood reports, X-rays, discharge summaries, etc.).

        Extract the following data and return it EXACTLY as a strict JSON object. Do not return any markdown wrappers, just the raw JSON string.

        {
            "patient_age": <integer or null>,
            "hb_level": <float or null> (look for Hemoglobin, Hb, HGB in blood reports),
            "alos": <integer or null> (calculate the Actual Length of Stay in days based on admission and discharge dates),
            "fever_duration_days": <integer or null> (look for history of fever),
            
            // Document Checkboxes: Set to true ONLY if you explicitly see the document inside the file
            "has_diagnostic_report": <boolean> (Is there a USG, X-ray, or Blood report?),
            "has_clinical_notes": <boolean> (Are there detailed doctor's evaluation notes?),
            "has_lft_report": <boolean> (Is there a Liver Function Test / Bilirubin report?),
            "has_indoor_case_papers": <boolean> (Are there daily ward observation / nursing sheets?),
            "has_operative_note": <boolean> (Is there an OT/Procedure note?),
            "has_pre_anesthesia_report": <boolean> (Is there a PAC / Anesthesia checkup?),
            "has_discharge_summary": <boolean> (Is there a final discharge summary?),
            "has_treatment_records": <boolean> (Are there records of antibiotics or blood transfusion?),
            
            // Fraud Flags
            "has_previous_cholecystectomy": <boolean> (Does the medical history mention they ALREADY had their gallbladder removed in the past?)
        }
        """

        print("Requesting extraction from Gemini 1.5 Flash...")
        response = model.generate_content([gemini_file, prompt])

        # Parse the JSON response
        raw_text = response.text.strip()
        
        # Clean up markdown if Gemini accidentally included it
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "", 1)
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
            
        extracted_data = json.loads(raw_text.strip())
        extracted_data["success"] = True
        return extracted_data

    except Exception as e:
        print(f"Gemini Extraction Error: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }
