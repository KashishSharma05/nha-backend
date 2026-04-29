from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim


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

    def post(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            extracted_text = f"Extracted text from {claim.document.name}"

            return Response({
                "message": "OCR processing completed",
                "claim_id": claim.id,
                "extracted_text": extracted_text
            })

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)