from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import RegisterSerializer
from .models import User


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email
        })


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)

            return Response({
                "message": "Password reset link sent successfully",
                "email": user.email
            })

        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=404)