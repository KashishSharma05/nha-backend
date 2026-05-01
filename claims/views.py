from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Claim, ClaimPageResult
from .serializers import ClaimSerializer
from .ps1_engine import extract_ps1_output_from_pdf
import os


class ClaimCreateView(generics.CreateAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ClaimListView(generics.ListAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(user=self.request.user)


class ClaimDetailView(generics.RetrieveAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(user=self.request.user)


class ClaimUpdateView(generics.UpdateAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(user=self.request.user)


class ClaimDeleteView(generics.DestroyAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(user=self.request.user)
    
class ClaimSearchView(generics.ListAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        return Claim.objects.filter(
            user=self.request.user,
            title__icontains=query
        )
class ClaimFilterView(generics.ListAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status = self.request.GET.get('status', '')
        return Claim.objects.filter(
            user=self.request.user,
            status=status
        )
class ClaimStatusSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(user=request.user)

        return Response({
            "total": claims.count(),
            "pending": claims.filter(status='pending').count(),
            "verified": claims.filter(status='verified').count(),
            "rejected": claims.filter(status='rejected').count()
        })
class BulkClaimCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        claims_data = request.data.get("claims", [])
        created_claims = []

        for claim_data in claims_data:
            claim = Claim.objects.create(
                user=request.user,
                title=claim_data.get("title"),
                description=claim_data.get("description"),
                status="pending"
            )

            created_claims.append({
                "claim_id": claim.id,
                "title": claim.title
            })

        return Response({
            "created_claims": created_claims
        })


class ClaimTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)

            timeline = [
                {
                    "step": "Claim Created",
                    "status": "completed"
                },
                {
                    "step": "Document Uploaded",
                    "status": "completed"
                },
                {
                    "step": "Verification",
                    "status": claim.status
                }
            ]

            return Response({
                "claim_id": claim.id,
                "timeline": timeline
            })

        except Claim.DoesNotExist:
            return Response({
                "error": "Claim not found"
            }, status=404)

class ClaimDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    ALLOWED_TYPES = {'application/pdf', 'image/jpeg', 'image/jpg', 'image/png'}
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def post(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)
            document = request.FILES.get('document')

            if not document:
                return Response({"error": "No document uploaded"}, status=400)

            # Validate file size
            if document.size > self.MAX_SIZE_BYTES:
                return Response(
                    {"error": "File too large. Maximum allowed size is 10 MB."},
                    status=400
                )

            # Validate file extension
            import os as _os
            ext = _os.path.splitext(document.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                return Response(
                    {"error": f"Invalid file type '{ext}'. Only PDF, JPG, and PNG are allowed."},
                    status=400
                )

            # Validate MIME type
            if document.content_type not in self.ALLOWED_TYPES:
                return Response(
                    {"error": "Invalid file content type. Only PDF, JPG, and PNG are allowed."},
                    status=400
                )

            claim.document = document
            claim.save()

            return Response({
                "message": "Document uploaded successfully",
                "claim_id": claim.id
            })

        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)


class PS1GenerateView(APIView):
    """
    POST /api/claims/ps1/generate/<claim_id>/

    Triggers Gemini-based per-page PS-1 extraction for the claim's uploaded document.
    Persists results in ClaimPageResult and returns the PS-1 compliant JSON array.

    Optional body / query params:
        case_id  (str) — override the case identifier (defaults to claim.id)
        s3_link  (str) — override the document link (defaults to relative media path)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)
        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)

        if not claim.document:
            return Response(
                {"error": "No document uploaded for this claim. Upload a PDF first."},
                status=400
            )

        if not claim.diagnosis_code:
            return Response(
                {"error": "Claim has no diagnosis_code. Set it before running PS-1 extraction."},
                status=400
            )

        # Resolve identifiers
        case_id = (
            request.data.get("case_id")
            or request.query_params.get("case_id")
            or str(claim.id)
        )
        s3_link = (
            request.data.get("s3_link")
            or request.query_params.get("s3_link")
            or claim.document.name
        )

        # Resolve absolute path to the uploaded PDF
        pdf_path = claim.document.path
        if not os.path.exists(pdf_path):
            return Response(
                {"error": f"Document file not found on disk: {pdf_path}"},
                status=400
            )

        # Run Gemini extraction
        result = extract_ps1_output_from_pdf(
            pdf_path=pdf_path,
            procedure_code=claim.diagnosis_code,
            case_id=case_id,
            s3_link=s3_link,
        )

        if not result.get("success"):
            return Response(
                {"error": result.get("error", "Extraction failed.")},
                status=502
            )

        pages = result["pages"]

        # Persist — delete stale results first
        ClaimPageResult.objects.filter(claim=claim).delete()
        saved_pages = []
        for page_data in pages:
            page_obj = ClaimPageResult.from_gemini_dict(
                claim=claim,
                page_data=page_data,
                case_id=case_id,
                s3_link=s3_link,
                procedure_code=claim.diagnosis_code,
            )
            page_obj.save()
            saved_pages.append(page_obj.to_ps1_dict())

        return Response({
            "claim_id":       claim.id,
            "case_id":        case_id,
            "procedure_code": claim.diagnosis_code,
            "page_count":     len(saved_pages),
            "ps1_output":     saved_pages,
        })


class PS1ResultView(APIView):
    """
    GET /api/claims/ps1/result/<claim_id>/

    Returns stored PS-1 per-page results without re-running Gemini.
    Returns 404 if extraction has not been run yet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        try:
            claim = Claim.objects.get(id=claim_id, user=request.user)
        except Claim.DoesNotExist:
            return Response({"error": "Claim not found"}, status=404)

        page_results = ClaimPageResult.objects.filter(claim=claim).order_by('page_number')
        if not page_results.exists():
            return Response(
                {"error": "No PS-1 output found. Run POST /ps1/generate/<id>/ first."},
                status=404
            )

        ps1_output = [p.to_ps1_dict() for p in page_results]

        return Response({
            "claim_id":       claim.id,
            "case_id":        page_results.first().case_id,
            "procedure_code": claim.diagnosis_code,
            "page_count":     len(ps1_output),
            "ps1_output":     ps1_output,
        })
