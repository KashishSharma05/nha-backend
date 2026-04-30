from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim


class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        return Response({
            "total_claims": claims.count(),
            "verified_claims": claims.filter(status='verified').count(),
            "pending_claims": claims.filter(status='pending').count(),
            "rejected_claims": claims.filter(status='rejected').count()
        })


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        notifications = []

        for claim in claims:
            notifications.append({
                "claim_id": claim.id,
                "message": f"Your claim is currently {claim.status}"
            })

        return Response({
            "notifications": notifications
        })


class ExportReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        export_data = []

        for claim in claims:
            export_data.append({
                "claim_id": claim.id,
                "title": claim.title,
                "status": claim.status
            })

        return Response({
            "export_data": export_data
        })


class AdminReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.all()

        all_claims = []

        for claim in claims:
            all_claims.append({
                "claim_id": claim.id,
                "title": claim.title,
                "status": claim.status,
                "user": claim.user.email
            })

        return Response({
            "claims": all_claims
        })


class ClaimHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user).order_by('-created_at')

        history = []

        for claim in claims:
            history.append({
                "claim_id": claim.id,
                "title": claim.title,
                "status": claim.status,
                "created_at": claim.created_at
            })

        return Response({
            "history": history
        })


class ClaimInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        insights = {
            "total_claims": claims.count(),
            "verified_percentage": (
                (claims.filter(status='verified').count() / claims.count()) * 100
                if claims.count() > 0 else 0
            ),
            "pending_percentage": (
                (claims.filter(status='pending').count() / claims.count()) * 100
                if claims.count() > 0 else 0
            ),
            "rejected_percentage": (
                (claims.filter(status='rejected').count() / claims.count()) * 100
                if claims.count() > 0 else 0
            )
        }

        return Response(insights)


class ClaimReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            report = {
                "claim_id": claim.id,
                "title": claim.title,
                "description": claim.description,
                "status": claim.status,
                "document": str(claim.document) if claim.document else None
            }

            return Response(report)

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