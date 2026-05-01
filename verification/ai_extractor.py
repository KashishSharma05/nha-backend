import os
import json
from google import genai
from google.genai import types

# Setup Gemini API client
_api_key = os.getenv("GEMINI_API_KEY")
_client  = genai.Client(api_key=_api_key) if _api_key else None


def extract_clinical_data_from_pdf(pdf_file_path):
    """
    Sends the PDF to Gemini 2.0 Flash to automatically extract clinical parameters
    and detect the presence of mandatory documents based on the NHA STG rules.
    """
    if not _client:
        return {
            "error": "Gemini API key is missing. Add GEMINI_API_KEY to your .env file.",
            "success": False
        }

    gemini_file = None
    try:
        # Upload the file to Gemini's File API
        print(f"Uploading {pdf_file_path} to Gemini...")
        gemini_file = _client.files.upload(file=pdf_file_path)

        # Define the strong, architected JSON prompt
        prompt = """
        <ROLE>
        You are an expert NHA (National Health Authority) Medical Auditor for PMJAY. 
        Your task is to perform an exhaustive, highly accurate review of the attached hospital IPD dossier.
        </ROLE>

        <OBJECTIVE>
        Analyze the document to extract exact clinical parameters and verify the presence of mandatory compliance documents.
        You must output ONLY a valid JSON object matching the schema below.
        </OBJECTIVE>

        <DOCUMENT_DEFINITIONS>
        - "diagnostic_report": Pathology (CBC/Hb) or Radiology (USG/X-Ray) reports from a lab.
        - "clinical_notes": Doctor's handwritten or typed evaluation notes detailing patient history and examination.
        - "indoor_case_papers": Daily nursing charts, TPR (Temp/Pulse/Resp) charts, or daily ward progress notes.
        - "operative_note": A surgical procedure note detailing the anesthesia, incision, and surgical steps.
        - "discharge_summary": The final summary given to the patient upon leaving, containing admission/discharge dates and treatment summary.
        - "treatment_records": Medication charts showing antibiotics or blood transfusion logs.
        </DOCUMENT_DEFINITIONS>

        <CONSTRAINTS_AND_RULES>
        1. NO HALLUCINATIONS: If a value or document is not explicitly present, you MUST return null (for data) or false (for documents).
        2. DO NOT GUESS ALOS: Actual Length of Stay (alos) must be calculated exactly as (Discharge Date - Admission Date). If either is missing, return null.
        3. FRAUD DETECTION: Check the history carefully. If the patient is undergoing a cholecystectomy, do they mention having their gallbladder removed previously?
        </CONSTRAINTS_AND_RULES>

        <OUTPUT_SCHEMA>
        Return exactly this JSON structure:
        {
            "reasoning_chain": "Briefly explain your step-by-step search for the clinical data and the mandatory documents. This improves your accuracy.",
            
            "clinical_data": {
                "patient_age": <integer or null>,
                "hb_level": <float or null> (Hemoglobin level in g/dL),
                "alos": <integer or null>,
                "fever_duration_days": <integer or null>
            },
            
            "mandatory_documents_found": {
                "has_diagnostic_report": <boolean>,
                "has_clinical_notes": <boolean>,
                "has_lft_report": <boolean>,
                "has_indoor_case_papers": <boolean>,
                "has_operative_note": <boolean>,
                "has_pre_anesthesia_report": <boolean>,
                "has_discharge_summary": <boolean>,
                "has_treatment_records": <boolean>
            },
            
            "fraud_flags": {
                "has_previous_cholecystectomy": <boolean>
            }
        }
        </OUTPUT_SCHEMA>
        """

        print("Requesting extraction from Gemini 2.0 Flash...")
        response = _client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[gemini_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        extracted_json = json.loads(response.text)
        
        # Flatten the nested JSON structure for the frontend
        extracted_data = {
            "patient_age": extracted_json["clinical_data"].get("patient_age"),
            "hb_level": extracted_json["clinical_data"].get("hb_level"),
            "alos": extracted_json["clinical_data"].get("alos"),
            "fever_duration_days": extracted_json["clinical_data"].get("fever_duration_days"),
            "has_previous_cholecystectomy": extracted_json["fraud_flags"].get("has_previous_cholecystectomy", False),
            "success": True,
            "reasoning": extracted_json.get("reasoning_chain", "")
        }
        
        # Merge document checkboxes
        extracted_data.update(extracted_json["mandatory_documents_found"])
        
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
        # Clean up the uploaded file from Google's servers
        if gemini_file:
            try:
                _client.files.delete(name=gemini_file.name)
                print(f"Deleted temporary file {gemini_file.name} from Gemini Cloud.")
            except Exception as cleanup_error:
                print(f"Failed to delete file from Gemini Cloud: {cleanup_error}")
