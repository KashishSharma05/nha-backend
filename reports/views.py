from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim


class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        return Response({
            "total_claims":    claims.count(),
            "verified_claims": claims.filter(status='verified').count(),
            "pending_claims":  claims.filter(status='pending').count(),
            "rejected_claims": claims.filter(status='rejected').count(),
        })


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user).order_by('-created_at')[:20]

        notifications = [
            {
                "claim_id": claim.id,
                "title":    claim.title or f"Claim #{claim.id}",
                "message":  f"Your claim is currently {claim.status}",
                "status":   claim.status,
            }
            for claim in claims
        ]

        return Response({"notifications": notifications})


class ExportReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        export_data = [
            {
                "claim_id":   claim.id,
                "title":      claim.title or f"Claim #{claim.id}",
                "status":     claim.status,
                "created_at": claim.created_at,
            }
            for claim in claims
        ]

        return Response({"export_data": export_data})


class AdminReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only staff/admin users can see all claims
        if not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to access this resource."},
                status=403
            )

        claims = Claim.objects.select_related('user').all()

        all_claims = [
            {
                "claim_id": claim.id,
                "title":    claim.title or f"Claim #{claim.id}",
                "status":   claim.status,
                "user":     getattr(claim.user, 'email', str(claim.user)),
            }
            for claim in claims
        ]

        return Response({"claims": all_claims})


class ClaimHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user).order_by('-created_at')

        history = [
            {
                "claim_id":   claim.id,
                "title":      claim.title or f"Claim #{claim.id}",
                "status":     claim.status,
                "created_at": claim.created_at,
            }
            for claim in claims
        ]

        return Response({"history": history})


class ClaimInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)
        total = claims.count()

        insights = {
            "total_claims": total,
            "verified_percentage": (
                round((claims.filter(status='verified').count() / total) * 100, 1)
                if total > 0 else 0
            ),
            "pending_percentage": (
                round((claims.filter(status='pending').count() / total) * 100, 1)
                if total > 0 else 0
            ),
            "rejected_percentage": (
                round((claims.filter(status='rejected').count() / total) * 100, 1)
                if total > 0 else 0
            ),
        }

        return Response(insights)


class ClaimReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            return Response({
                "claim_id":    claim.id,
                "title":       claim.title or f"Claim #{claim.id}",
                "description": claim.description or "",
                "status":      claim.status,
                "document":    str(claim.document) if claim.document else None,
                "created_at":  claim.created_at,
            })

        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)


class ComplianceCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            is_compliant = claim.status == "verified"

            return Response({
                "claim_id":          claim.id,
                "compliance_status": "compliant" if is_compliant else "non-compliant",
                "compliance_score":  100 if is_compliant else 0,
                "risk_level":        "Low Risk" if is_compliant else "High Risk",
                "recommendation": (
                    "Claim follows treatment guidelines. Approved for processing."
                    if is_compliant else
                    "Claim has compliance issues. Manual review recommended."
                ),
            })

        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)