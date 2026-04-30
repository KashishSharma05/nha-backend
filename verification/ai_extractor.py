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

    gemini_file = None
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

        Extract the following data and return it as a JSON object. 
        CRITICAL EDGE CASES:
        1. If a value is not found or unreadable, return null. DO NOT hallucinate or guess.
        2. For checkboxes (has_*), return true ONLY if you explicitly see the document inside the file. If absent, return false.
        3. ALOS: Calculate the Actual Length of Stay in days based on admission and discharge dates. If dates are missing, return null.

        {
            "patient_age": <integer or null>,
            "hb_level": <float or null> (look for Hemoglobin, Hb, HGB in blood reports),
            "alos": <integer or null>,
            "fever_duration_days": <integer or null>,
            
            "has_diagnostic_report": <boolean>,
            "has_clinical_notes": <boolean>,
            "has_lft_report": <boolean>,
            "has_indoor_case_papers": <boolean>,
            "has_operative_note": <boolean>,
            "has_pre_anesthesia_report": <boolean>,
            "has_discharge_summary": <boolean>,
            "has_treatment_records": <boolean>,
            
            "has_previous_cholecystectomy": <boolean>
        }
        """

        print("Requesting extraction from Gemini 1.5 Flash...")
        response = model.generate_content(
            [gemini_file, prompt],
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )

        extracted_data = json.loads(response.text)
        extracted_data["success"] = True
        return extracted_data

    except json.JSONDecodeError:
        return {"error": "AI returned invalid data format.", "success": False}
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            error_msg = "Gemini API rate limit exceeded. Please try again in a minute."
        print(f"Gemini Extraction Error: {error_msg}")
        return {"error": error_msg, "success": False}
    finally:
        # Edge Case: Clean up the uploaded file from Google's servers to avoid storage quota issues
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
                print(f"Deleted temporary file {gemini_file.name} from Gemini Cloud.")
            except Exception as cleanup_error:
                print(f"Failed to delete file from Gemini Cloud: {cleanup_error}")
