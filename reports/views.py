from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim


class ClaimReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            report_data = {
                "claim_id": claim.id,
                "title": claim.title,
                "description": claim.description,
                "status": claim.status,
                "created_at": claim.created_at
            }

            return Response(report_data)

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)


class ComplianceCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            compliance_status = "compliant" if claim.status == "verified" else "non-compliant"

            return Response({
                "claim_id": claim.id,
                "compliance_status": compliance_status
            })

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)