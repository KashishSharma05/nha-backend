from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Claim
from .serializers import ClaimSerializer


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