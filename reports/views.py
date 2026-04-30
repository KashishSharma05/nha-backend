from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from claims.models import Claim
from claims.compliance_engine import check_compliance, STG_REGISTRY, STG_PRICES


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


def _build_claim_data(claim):
    """Extract all compliance-relevant fields from a Claim instance."""
    return {
        "diagnosis_code":             claim.diagnosis_code,
        "ward_type":                  getattr(claim, 'ward_type', 'general_ward'),
        "patient_age":                claim.patient_age,
        "alos":                       claim.alos,
        "hb_level":                   claim.hb_level,
        "claimed_amount":             claim.claimed_amount,
        "fever_duration_days":        getattr(claim, 'fever_duration_days', None),
        "has_diagnostic_report":      claim.has_diagnostic_report,
        "has_clinical_notes":         claim.has_clinical_notes,
        "has_indoor_case_papers":     claim.has_indoor_case_papers,
        "has_operative_note":         claim.has_operative_note,
        "has_discharge_summary":      claim.has_discharge_summary,
        "has_treatment_records":      claim.has_treatment_records,
        "has_post_treatment_report":  claim.has_post_treatment_report,
        "has_histopathology_report":  claim.has_histopathology_report,
        "has_cbc_report":             claim.has_cbc_report,
        "has_implant_invoice":        claim.has_implant_invoice,
        "has_preop_xray":             claim.has_preop_xray,
        "has_lft_report":             getattr(claim, 'has_lft_report', False),
        "has_pre_anesthesia_report":  getattr(claim, 'has_pre_anesthesia_report', False),
        "has_postop_photo":           getattr(claim, 'has_postop_photo', False),
        "has_previous_cholecystectomy": getattr(claim, 'has_previous_cholecystectomy', False),
    }


class ClaimReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim  = Claim.objects.get(id=claim_id, user=request.user)
            result = check_compliance(_build_claim_data(claim))

            return Response({
                "claim_id":       claim.id,
                "title":          claim.title or f"Claim #{claim.id}",
                "description":    claim.description or "",
                "status":         claim.status,
                "created_at":     claim.created_at,
                "diagnosis_code": claim.diagnosis_code,
                "procedure_name": result["procedure_name"],
                "specialty":      result.get("specialty", ""),
                "alos_range":     result.get("alos_range", []),
                # Compliance
                "verdict":          result["verdict"],
                "compliance_score": result["compliance_score"],
                "risk_level":       result["risk_level"],
                "recommendation":   result["recommendation"],
                "matched_rules":    result["matched_rules"],
                "failed_rules":     result["failed_rules"],
                "tms_failures":     result.get("tms_failures", []),
                "doc_failures":     result.get("doc_failures", []),
                "total_rules":      result["total_rules"],
                "passed_rules":     result["passed_rules"],
                "total_tms_rules":  result.get("total_tms_rules", 0),
                "passed_tms_rules": result.get("passed_tms_rules", 0),
                # Financial
                "payable_amount":   result["payable_amount"],
                "total_claimed":    result["total_claimed"],
                "base_price":       result["base_price"],
            })

        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)


class ComplianceCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim  = Claim.objects.get(id=claim_id, user=request.user)
            result = check_compliance(_build_claim_data(claim))

            # Update claim status based on verdict
            if result["verdict"] == "APPROVED":
                claim.status = "verified"
            elif result["verdict"] == "REJECTED":
                claim.status = "rejected"
            claim.save()

            return Response({
                "claim_id":           claim.id,
                "diagnosis_code":     result["diagnosis_code"],
                "procedure_name":     result["procedure_name"],
                "specialty":          result.get("specialty", ""),
                "compliance_status":  "compliant" if result["verdict"] == "APPROVED" else "non-compliant",
                "compliance_score":   result["compliance_score"],
                "risk_level":         result["risk_level"],
                "verdict":            result["verdict"],
                "matched_rules":      result["matched_rules"],
                "failed_rules":       result["failed_rules"],
                "tms_failures":       result.get("tms_failures", []),
                "doc_failures":       result.get("doc_failures", []),
                "total_rules":        result["total_rules"],
                "passed_rules":       result["passed_rules"],
                "total_tms_rules":    result.get("total_tms_rules", 0),
                "passed_tms_rules":   result.get("passed_tms_rules", 0),
                "recommendation":     result["recommendation"],
                "payable_amount":     result["payable_amount"],
                "total_claimed":      result["total_claimed"],
                "alos_range":         result.get("alos_range", []),
            })

        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)