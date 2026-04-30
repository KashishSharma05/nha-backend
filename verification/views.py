from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim
import tempfile
import os
from .ai_extractor import extract_clinical_data_from_pdf


class VerifyClaimView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            if claim.document:
                claim.status = 'verified'
            else:
                claim.status = 'rejected'

            claim.save()

            return Response({
                "message": "Claim verification completed",
                "claim_id": claim.id,
                "status": claim.status
            })

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)


class OCRProcessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Takes an uploaded PDF file directly, runs it through Gemini 1.5,
        and returns the extracted JSON without saving a Claim to the database yet.
        """
        document = request.FILES.get('document')
        
        if not document:
            return Response({"error": "No document provided"}, status=400)

        # Save to temp file so Gemini SDK can read it
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in document.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # Run the Gemini Pipeline
            extracted_data = extract_clinical_data_from_pdf(temp_file_path)
            
            # Clean up temp file
            os.remove(temp_file_path)

            if not extracted_data.get("success"):
                return Response(extracted_data, status=500)

            return Response({
                "message": "AI Extraction completed",
                "extracted_data": extracted_data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class OCRStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            status = "completed" if claim.document else "pending"

            return Response({
                "claim_id": claim.id,
                "ocr_status": status
            })

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)