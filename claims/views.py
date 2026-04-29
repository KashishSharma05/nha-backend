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